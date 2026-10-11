from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Session

from app.core.enums import ContentType, Language, Tone
from app.repositories import GenerationRepository
from tests.factories import OWNER, make_generation, make_user

BASE_TIME = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def owner(db_session: Session) -> None:
    """The account that owns the generations created in these tests."""
    db_session.add(make_user(id=OWNER))
    db_session.commit()


@pytest.fixture
def repository(db_session: Session) -> GenerationRepository:
    return GenerationRepository(db_session)


def add_at(repository: GenerationRepository, minutes: int, **overrides: object) -> int:
    generation = repository.add(make_generation(created_at=BASE_TIME + timedelta(minutes=minutes), **overrides))
    return generation.id


def test_add_assigns_id_and_creation_date(repository: GenerationRepository) -> None:
    generation = repository.add(make_generation())

    assert generation.id is not None
    assert generation.created_at is not None


def test_add_does_not_commit(repository: GenerationRepository, db_session: Session) -> None:
    repository.add(make_generation())
    db_session.rollback()

    assert repository.count(user_id=OWNER) == 0


def test_get_by_id_returns_stored_generation(repository: GenerationRepository, db_session: Session) -> None:
    generation_id = repository.add(make_generation(customer="Ana Ruiz")).id
    db_session.commit()
    db_session.expunge_all()

    stored = repository.get_by_id(generation_id)

    assert stored is not None
    assert stored.customer == "Ana Ruiz"
    assert stored.content_type is ContentType.COMMERCIAL_EMAIL
    assert stored.language is Language.SPANISH
    assert stored.tone is Tone.PROFESSIONAL


def test_get_by_id_returns_none_when_missing(repository: GenerationRepository) -> None:
    assert repository.get_by_id(999) is None


def test_enums_are_stored_as_their_values(repository: GenerationRepository, db_session: Session) -> None:
    repository.add(make_generation(content_type=ContentType.SALES_PROPOSAL, language=Language.FRENCH))
    db_session.commit()

    row = db_session.execute(text("SELECT content_type, language, tone FROM generations")).one()

    assert tuple(row) == ("sales_proposal", "fr", "professional")


def test_list_returns_newest_first(repository: GenerationRepository) -> None:
    oldest = add_at(repository, 0)
    newest = add_at(repository, 10)
    middle = add_at(repository, 5)

    items = repository.list_paginated(user_id=OWNER, limit=10, offset=0)

    assert [item.id for item in items] == [newest, middle, oldest]


def test_list_applies_limit_and_offset(repository: GenerationRepository) -> None:
    ids = [add_at(repository, minute) for minute in range(5)]

    page = repository.list_paginated(user_id=OWNER, limit=2, offset=1)

    assert [item.id for item in page] == [ids[3], ids[2]]


def test_list_and_count_filter_by_content_type(repository: GenerationRepository) -> None:
    add_at(repository, 0, content_type=ContentType.WHATSAPP)
    add_at(repository, 1, content_type=ContentType.FOLLOW_UP)
    add_at(repository, 2, content_type=ContentType.WHATSAPP)

    items = repository.list_paginated(user_id=OWNER, limit=10, offset=0, content_type=ContentType.WHATSAPP)

    assert {item.content_type for item in items} == {ContentType.WHATSAPP}
    assert repository.count(user_id=OWNER, content_type=ContentType.WHATSAPP) == 2
    assert repository.count(user_id=OWNER, content_type=ContentType.CUSTOMER_SUMMARY) == 0
    assert repository.count(user_id=OWNER) == 3


def test_naive_datetimes_are_rejected(repository: GenerationRepository) -> None:
    with pytest.raises(StatementError):
        repository.add(make_generation(created_at=datetime(2026, 10, 7, 12, 0)))


def test_delete_removes_the_generation(repository: GenerationRepository) -> None:
    generation = repository.add(make_generation())
    generation_id = generation.id

    repository.delete(generation)

    assert repository.get_by_id(generation_id) is None
    assert repository.count(user_id=OWNER) == 0
