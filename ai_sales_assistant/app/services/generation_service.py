import logging
from collections.abc import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.enums import ContentType
from app.core.exceptions import CommercialTermsMissingError, GuestQuotaExceededError, NotFoundError
from app.models.generation import Generation
from app.prompts.builder import build_prompt, build_retry_prompt, mandatory_terms
from app.repositories.generation_repository import GenerationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.generation import GenerationCreate, GenerationList, GenerationRead
from app.services.ai.base import AIProvider, AIResult
from app.services.commercial_terms import find_missing

logger = logging.getLogger(__name__)

AIProviderResolver = Callable[[], AIProvider]


class GenerationService:
    """Use cases for generating and consulting commercial content.

    The AI provider is resolved lazily, so read operations keep working even
    when the provider is not configured.
    """

    def __init__(
        self,
        session: Session,
        repository: GenerationRepository,
        resolve_ai_provider: AIProviderResolver,
        users: UserRepository | None = None,
        *,
        commercial_terms_max_retries: int = 1,
        commercial_terms_strict: bool = False,
    ) -> None:
        self._session = session
        self._repository = repository
        self._resolve_ai_provider = resolve_ai_provider
        self._users = users or UserRepository(session)
        self._max_retries = commercial_terms_max_retries
        self._strict = commercial_terms_strict

    def generate(
        self, data: GenerationCreate, *, user_id: int, max_ai_calls: int | None = None
    ) -> GenerationRead:
        """Generate and store content. `max_ai_calls` caps the AI calls of the account (guests)."""
        # Any provider failure (or a strict-mode rejection) raises before anything is written.
        result, ai_calls = self._generate_text(data, user_id=user_id, max_ai_calls=max_ai_calls)
        generation = Generation(user_id=user_id)
        self._apply(generation, data, result)

        def save() -> None:
            self._repository.add(generation)
            self._users.increment_ai_generation_count(user_id, by=ai_calls)

        self._commit(save)
        logger.info("Generation %s created (content_type=%s)", generation.id, generation.content_type)
        return GenerationRead.model_validate(generation)

    def regenerate(
        self, generation_id: int, data: GenerationCreate, *, user_id: int, max_ai_calls: int | None = None
    ) -> GenerationRead:
        """Regenerate an existing generation from new input, updating the same record.

        The content always comes from the AI provider; clients cannot set it directly.
        """
        # Checked first, so an unknown (or someone else's) id never triggers a slow, possibly paid AI call.
        generation = self._get_or_404(generation_id, user_id)
        result, ai_calls = self._generate_text(data, user_id=user_id, max_ai_calls=max_ai_calls)
        # Any provider failure has raised above, leaving the record untouched.
        self._apply(generation, data, result)

        def save() -> None:
            self._session.flush()
            self._users.increment_ai_generation_count(user_id, by=ai_calls)

        self._commit(save)
        logger.info("Generation %s regenerated (content_type=%s)", generation.id, generation.content_type)
        return GenerationRead.model_validate(generation)

    def delete(self, generation_id: int, *, user_id: int) -> None:
        generation = self._get_or_404(generation_id, user_id)
        self._commit(lambda: self._repository.delete(generation))
        logger.info("Generation %s deleted", generation_id)

    def get(self, generation_id: int, *, user_id: int) -> GenerationRead:
        return GenerationRead.model_validate(self._get_or_404(generation_id, user_id))

    def list_generations(
        self, *, user_id: int, limit: int, offset: int, content_type: ContentType | None = None
    ) -> GenerationList:
        items = self._repository.list_paginated(
            user_id=user_id, limit=limit, offset=offset, content_type=content_type
        )
        return GenerationList(
            items=[GenerationRead.model_validate(item) for item in items],
            total=self._repository.count(user_id=user_id, content_type=content_type),
            limit=limit,
            offset=offset,
        )

    def _generate_text(
        self, data: GenerationCreate, *, user_id: int, max_ai_calls: int | None
    ) -> tuple[AIResult, int]:
        """Call the AI and verify that every mandatory commercial term made it into the text.

        If something is missing, the model is asked once more (it rewrites the text itself; the
        application never edits it). Returns the best result and the number of AI calls made.
        """
        self._check_ai_quota(user_id, max_ai_calls)
        provider = self._resolve_ai_provider()
        terms = mandatory_terms(data)
        prompt = build_prompt(data)
        result = provider.generate(prompt)
        calls = 1
        missing = find_missing(terms, result.content)

        retries = 0
        while missing and retries < self._max_retries and self._has_ai_quota(user_id, max_ai_calls, calls):
            retries += 1
            logger.info("Mandatory commercial terms missing (%d); asking the model again", len(missing))
            retry = provider.generate(build_retry_prompt(prompt, result.content, missing, data.language))
            calls += 1
            retry_missing = find_missing(terms, retry.content)
            # Keep whichever attempt preserved more terms; token usage covers both calls.
            best, best_missing = (retry, retry_missing) if len(retry_missing) <= len(missing) else (result, missing)
            result = _with_usage(best, result, retry)
            missing = best_missing

        if missing:
            logger.warning("Generated text still misses %d mandatory commercial term(s)", len(missing))
            if self._strict:
                self._users.increment_ai_generation_count(user_id, by=calls)
                self._session.commit()  # the AI calls were made: they still count for guest limits
                raise CommercialTermsMissingError([term.text for term in missing])
        return result, calls

    def _has_ai_quota(self, user_id: int, max_ai_calls: int | None, pending_calls: int) -> bool:
        if max_ai_calls is None:
            return True
        return self._users.ai_generation_count(user_id) + pending_calls < max_ai_calls

    def _check_ai_quota(self, user_id: int, max_ai_calls: int | None) -> None:
        # Checked before calling the provider: an exhausted quota never costs an AI call.
        if not self._has_ai_quota(user_id, max_ai_calls, 0):
            raise GuestQuotaExceededError()

    def _get_or_404(self, generation_id: int, user_id: int) -> Generation:
        # Someone else's generation is reported exactly like a missing one, so ids reveal nothing.
        generation = self._repository.get_for_user(generation_id, user_id=user_id)
        if generation is None:
            raise NotFoundError(f"Generation {generation_id} was not found.")
        return generation

    @staticmethod
    def _apply(generation: Generation, data: GenerationCreate, result: AIResult) -> None:
        for field, value in data.model_dump().items():
            setattr(generation, field, value)
        generation.generated_content = result.content
        generation.ai_provider = result.provider
        generation.ai_model = result.model
        generation.prompt_tokens = result.prompt_tokens
        generation.completion_tokens = result.completion_tokens

    def _commit(self, operation: Callable[[], object]) -> None:
        try:
            operation()
            self._session.commit()
        except SQLAlchemyError:
            self._session.rollback()
            raise


def _with_usage(best: AIResult, *attempts: AIResult) -> AIResult:
    """`best`, with the token usage of every attempt added up."""

    def total(values: list[int | None]) -> int | None:
        known = [value for value in values if value is not None]
        return sum(known) if known else None

    return AIResult(
        content=best.content,
        provider=best.provider,
        model=best.model,
        prompt_tokens=total([attempt.prompt_tokens for attempt in attempts]),
        completion_tokens=total([attempt.completion_tokens for attempt in attempts]),
    )
