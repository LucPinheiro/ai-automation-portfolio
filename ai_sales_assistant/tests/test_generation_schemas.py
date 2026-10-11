from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.core.constants import CUSTOMER_MAX_LENGTH, CUSTOMER_NEEDS_MAX_LENGTH
from app.core.enums import ContentType, Language, Tone
from app.schemas.generation import GenerationCreate, GenerationRead
from tests.factories import generation_payload, make_generation


def error_types(exc: ValidationError) -> dict[str, str]:
    return {".".join(str(part) for part in error["loc"]): error["type"] for error in exc.errors()}


def test_valid_payload_is_parsed_into_enums() -> None:
    data = GenerationCreate.model_validate(generation_payload())

    assert data.content_type is ContentType.COMMERCIAL_EMAIL
    assert data.language is Language.SPANISH
    assert data.tone is Tone.PROFESSIONAL


@pytest.mark.parametrize("content_type", [member.value for member in ContentType])
def test_all_content_types_are_accepted(content_type: str) -> None:
    assert GenerationCreate.model_validate(generation_payload(content_type=content_type))


def test_surrounding_whitespace_is_stripped() -> None:
    data = GenerationCreate.model_validate(generation_payload(customer="  María López  "))

    assert data.customer == "María López"


@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_empty_or_blank_text_is_rejected(value: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        GenerationCreate.model_validate(generation_payload(customer=value))

    assert error_types(exc_info.value) == {"customer": "string_too_short"}


@pytest.mark.parametrize(
    ("field", "max_length"),
    [("customer", CUSTOMER_MAX_LENGTH), ("customer_needs", CUSTOMER_NEEDS_MAX_LENGTH)],
)
def test_text_longer_than_limit_is_rejected(field: str, max_length: int) -> None:
    GenerationCreate.model_validate(generation_payload(**{field: "x" * max_length}))

    with pytest.raises(ValidationError) as exc_info:
        GenerationCreate.model_validate(generation_payload(**{field: "x" * (max_length + 1)}))

    assert error_types(exc_info.value) == {field: "string_too_long"}


@pytest.mark.parametrize(
    ("field", "value"),
    [("content_type", "blog_post"), ("language", "de"), ("tone", "aggressive"), ("tone", "Professional")],
)
def test_unknown_enum_values_are_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        GenerationCreate.model_validate(generation_payload(**{field: value}))

    assert error_types(exc_info.value) == {field: "enum"}


def test_missing_required_field_is_rejected() -> None:
    payload = generation_payload()
    del payload["industry"]

    with pytest.raises(ValidationError) as exc_info:
        GenerationCreate.model_validate(payload)

    assert error_types(exc_info.value) == {"industry": "missing"}


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        GenerationCreate.model_validate(generation_payload(discount=50))

    assert error_types(exc_info.value) == {"discount": "extra_forbidden"}


def test_non_string_text_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        GenerationCreate.model_validate(generation_payload(company=123))

    assert error_types(exc_info.value) == {"company": "string_type"}


def test_read_schema_is_built_from_orm_model() -> None:
    generation = make_generation(id=7, created_at=datetime(2026, 10, 7, tzinfo=UTC))

    data = GenerationRead.model_validate(generation)

    assert data.id == 7
    assert data.content_type is ContentType.COMMERCIAL_EMAIL
    assert data.generated_content == generation.generated_content
    assert "prompt_tokens" not in data.model_dump()
