from datetime import UTC

import pytest
from sqlalchemy.orm import Session

from app.core.enums import ContentType
from app.core.exceptions import AIProviderError, AIProviderNotConfiguredError, NotFoundError
from app.repositories import GenerationRepository
from app.schemas.generation import GenerationCreate
from app.services.ai.base import AIProvider
from app.services.generation_service import GenerationService
from tests.factories import OWNER, generation_payload, make_user
from tests.fakes import FakeAIProvider


@pytest.fixture(autouse=True)
def owner(db_session: Session) -> None:
    """The account that owns the generations created in these tests."""
    db_session.add(make_user(id=OWNER))
    db_session.commit()


def make_service(session: Session, provider: FakeAIProvider) -> GenerationService:
    return GenerationService(
        session=session,
        repository=GenerationRepository(session),
        resolve_ai_provider=lambda: provider,
    )


def make_input(**overrides: object) -> GenerationCreate:
    return GenerationCreate.model_validate(generation_payload(**overrides))


def test_generate_returns_and_persists_the_result(db_session: Session) -> None:
    service = make_service(db_session, FakeAIProvider(content="Estimada María, ..."))

    result = service.generate(make_input(), user_id=OWNER)
    db_session.expunge_all()
    stored = GenerationRepository(db_session).get_by_id(result.id)

    assert result.generated_content == "Estimada María, ..."
    assert result.ai_provider == "fake"
    assert result.ai_model == "fake-model"
    assert stored is not None
    assert stored.generated_content == "Estimada María, ..."
    assert (stored.prompt_tokens, stored.completion_tokens) == (100, 50)


def test_generate_sends_the_prompt_for_the_requested_content_type(db_session: Session) -> None:
    provider = FakeAIProvider()

    make_service(db_session, provider).generate(make_input(content_type="whatsapp", customer="Ana Ruiz"), user_id=OWNER)

    assert len(provider.prompts) == 1
    assert "WhatsApp" in provider.prompts[0].user
    assert "Ana Ruiz" in provider.prompts[0].user


def test_generate_returns_timezone_aware_creation_date(db_session: Session) -> None:
    service = make_service(db_session, FakeAIProvider())

    created = service.generate(make_input(), user_id=OWNER)
    db_session.expunge_all()

    assert service.get(created.id, user_id=OWNER).created_at.tzinfo == UTC


@pytest.mark.parametrize("error", [AIProviderError(), AIProviderNotConfiguredError()])
def test_provider_failure_raises_and_persists_nothing(db_session: Session, error: AIProviderError) -> None:
    service = make_service(db_session, FakeAIProvider(error=error))

    with pytest.raises(type(error)):
        service.generate(make_input(), user_id=OWNER)

    assert GenerationRepository(db_session).count(user_id=OWNER) == 0


def test_provider_is_not_resolved_for_read_operations(db_session: Session) -> None:
    def unavailable_provider() -> AIProvider:
        raise AIProviderNotConfiguredError()

    service = GenerationService(
        session=db_session,
        repository=GenerationRepository(db_session),
        resolve_ai_provider=unavailable_provider,
    )

    assert service.list_generations(user_id=OWNER, limit=10, offset=0).total == 0


def test_get_missing_generation_raises_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError, match="Generation 42 was not found"):
        make_service(db_session, FakeAIProvider()).get(42, user_id=OWNER)


def test_list_generations_returns_page_and_total(db_session: Session) -> None:
    service = make_service(db_session, FakeAIProvider())
    for content_type in ("whatsapp", "follow_up", "whatsapp"):
        service.generate(make_input(content_type=content_type), user_id=OWNER)

    page = service.list_generations(user_id=OWNER, limit=1, offset=0, content_type=ContentType.WHATSAPP)

    assert page.total == 2
    assert (page.limit, page.offset) == (1, 0)
    assert len(page.items) == 1
    assert page.items[0].content_type is ContentType.WHATSAPP


# --- regenerate ------------------------------------------------------------------


def test_regenerate_updates_the_same_record(db_session: Session) -> None:
    provider = FakeAIProvider(content="Primera versión")
    service = make_service(db_session, provider)
    created = service.generate(make_input(), user_id=OWNER)
    provider.content = "Segunda versión"

    updated = service.regenerate(created.id, make_input(customer="Ana Ruiz", tone="friendly"), user_id=OWNER)
    db_session.expunge_all()
    stored = GenerationRepository(db_session).get_by_id(created.id)

    assert updated.id == created.id
    assert updated.generated_content == "Segunda versión"
    assert updated.created_at == created.created_at
    assert stored is not None
    assert (stored.customer, stored.tone, stored.generated_content) == ("Ana Ruiz", "friendly", "Segunda versión")
    assert GenerationRepository(db_session).count(user_id=OWNER) == 1
    assert "Ana Ruiz" in provider.prompts[-1].user


def test_regenerate_unknown_id_raises_not_found_without_calling_the_ai(db_session: Session) -> None:
    provider = FakeAIProvider()

    with pytest.raises(NotFoundError):
        make_service(db_session, provider).regenerate(999, make_input(), user_id=OWNER)

    assert provider.prompts == []


def test_regenerate_keeps_the_record_when_the_provider_fails(db_session: Session) -> None:
    provider = FakeAIProvider(content="Original")
    service = make_service(db_session, provider)
    created = service.generate(make_input(), user_id=OWNER)
    provider.error = AIProviderError()

    with pytest.raises(AIProviderError):
        service.regenerate(created.id, make_input(customer="Ana Ruiz"), user_id=OWNER)
    db_session.expunge_all()
    stored = GenerationRepository(db_session).get_by_id(created.id)

    assert stored is not None
    assert (stored.customer, stored.generated_content) == ("María López", "Original")


# --- delete ----------------------------------------------------------------------


def test_delete_removes_the_generation(db_session: Session) -> None:
    service = make_service(db_session, FakeAIProvider())
    created = service.generate(make_input(), user_id=OWNER)

    service.delete(created.id, user_id=OWNER)

    with pytest.raises(NotFoundError):
        service.get(created.id, user_id=OWNER)


def test_delete_unknown_id_raises_not_found(db_session: Session) -> None:
    with pytest.raises(NotFoundError):
        make_service(db_session, FakeAIProvider()).delete(999, user_id=OWNER)


def test_delete_does_not_need_an_ai_provider(db_session: Session) -> None:
    created = make_service(db_session, FakeAIProvider()).generate(make_input(), user_id=OWNER)

    def unavailable() -> AIProvider:
        raise AIProviderNotConfiguredError()

    service = GenerationService(db_session, GenerationRepository(db_session), unavailable)
    service.delete(created.id, user_id=OWNER)

    assert GenerationRepository(db_session).count(user_id=OWNER) == 0
