from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.api.dependencies import CurrentUserDep, GenerationServiceDep, SettingsDep
from app.api.responses import error_responses
from app.core.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.core.enums import ContentType
from app.config import Settings
from app.models.user import User
from app.schemas.generation import GenerationCreate, GenerationList, GenerationRead

router = APIRouter(tags=["Generations"])


def ai_call_limit(user: User, settings: Settings) -> int | None:
    """Guests have a capped number of AI calls (cost protection); registered users do not."""
    return settings.guest_max_generations if user.is_guest else None


@router.post(
    "/generate",
    response_model=GenerationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate commercial content",
    description=(
        "Generates a commercial email, sales proposal, follow-up, WhatsApp message or customer "
        "summary with AI from the customer data, then stores and returns the result. "
        "Nothing is stored when the AI provider fails."
    ),
    response_description="Content generated and stored",
    responses=error_responses(400, 401, 403, 422, 500, 502, 503),
)
def generate_content(
    data: GenerationCreate, user: CurrentUserDep, service: GenerationServiceDep, settings: SettingsDep
) -> GenerationRead:
    return service.generate(data, user_id=user.id, max_ai_calls=ai_call_limit(user, settings))


@router.get(
    "/generations",
    response_model=GenerationList,
    summary="List generations",
    description=(
        "Returns the authenticated user's generations, newest first, optionally filtered by content type."
    ),
    response_description="A page of generations",
    responses=error_responses(401, 422, 500),
)
def list_generations(
    user: CurrentUserDep,
    service: GenerationServiceDep,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT, description="Maximum number of items")] = (
        DEFAULT_PAGE_LIMIT
    ),
    offset: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    content_type: Annotated[ContentType | None, Query(description="Filter by content type")] = None,
) -> GenerationList:
    return service.list_generations(user_id=user.id, limit=limit, offset=offset, content_type=content_type)


@router.get(
    "/generations/{generation_id}",
    response_model=GenerationRead,
    summary="Get a generation",
    description="Returns one of the authenticated user's generations. Other users' generations return 404.",
    response_description="The requested generation",
    responses=error_responses(401, 404, 422, 500),
)
def get_generation(
    generation_id: Annotated[int, Path(ge=1, description="Generation id")],
    user: CurrentUserDep,
    service: GenerationServiceDep,
) -> GenerationRead:
    return service.get(generation_id, user_id=user.id)


@router.put(
    "/generations/{generation_id}",
    response_model=GenerationRead,
    summary="Regenerate a generation",
    description=(
        "Regenerates the content of an existing generation with AI from new customer data and "
        "updates the same record. The content cannot be set directly: it always comes from the AI "
        "provider. The record is left unchanged when the AI provider fails. "
        "Other users' generations return 404."
    ),
    response_description="Content regenerated and stored",
    responses=error_responses(400, 401, 403, 404, 422, 500, 502, 503),
)
def regenerate_generation(
    generation_id: Annotated[int, Path(ge=1, description="Generation id")],
    data: GenerationCreate,
    user: CurrentUserDep,
    service: GenerationServiceDep,
    settings: SettingsDep,
) -> GenerationRead:
    return service.regenerate(generation_id, data, user_id=user.id, max_ai_calls=ai_call_limit(user, settings))


@router.delete(
    "/generations/{generation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a generation",
    description="Permanently deletes one of the authenticated user's generations. Other users' generations return 404.",
    response_description="Generation deleted",
    responses=error_responses(401, 403, 404, 422, 500),
)
def delete_generation(
    generation_id: Annotated[int, Path(ge=1, description="Generation id")],
    user: CurrentUserDep,
    service: GenerationServiceDep,
) -> Response:
    service.delete(generation_id, user_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
