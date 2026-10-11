import pytest
from sqlalchemy.orm import Session

from app.cli import AccountNotFoundError, assign_orphan_generations, main
from app.models import Generation
from tests.factories import make_generation, make_user


@pytest.fixture
def data(db_session: Session) -> dict[str, int]:
    owner = make_user(email="maria@example.com")
    other = make_user(name="Ana", email="ana@example.com")
    db_session.add_all([owner, other])
    db_session.flush()
    db_session.add_all(
        [
            make_generation(user_id=None, customer="Antigua 1"),
            make_generation(user_id=None, customer="Antigua 2"),
            make_generation(user_id=other.id, customer="De Ana"),
        ]
    )
    db_session.commit()
    return {"owner": owner.id, "other": other.id}


def owners(db_session: Session) -> dict[str, int | None]:
    db_session.expire_all()
    return {g.customer: g.user_id for g in db_session.query(Generation).all()}


def test_dry_run_counts_without_changing_anything(db_session: Session, data: dict[str, int]) -> None:
    count, message = assign_orphan_generations(db_session, "maria@example.com", dry_run=True)

    assert count == 2
    assert "dry-run" in message
    assert owners(db_session)["Antigua 1"] is None


def test_assigns_only_unowned_generations(db_session: Session, data: dict[str, int]) -> None:
    count, _ = assign_orphan_generations(db_session, "MARIA@example.com")

    assert count == 2
    assert owners(db_session) == {"Antigua 1": data["owner"], "Antigua 2": data["owner"], "De Ana": data["other"]}


def test_running_twice_assigns_nothing_more(db_session: Session, data: dict[str, int]) -> None:
    assign_orphan_generations(db_session, "maria@example.com")

    count, _ = assign_orphan_generations(db_session, "maria@example.com")

    assert count == 0


def test_unknown_email_is_an_error(db_session: Session, data: dict[str, int]) -> None:
    with pytest.raises(AccountNotFoundError):
        assign_orphan_generations(db_session, "nobody@example.com")
    assert owners(db_session)["Antigua 1"] is None


def test_main_exit_codes(db_session: Session, data: dict[str, int], capsys: pytest.CaptureFixture[str]) -> None:
    def factory() -> Session:
        return db_session

    assert main(["assign-orphan-generations", "--email", "nobody@example.com"], session_factory=factory) == 1
    assert "No account found" in capsys.readouterr().err

    assert main(["assign-orphan-generations", "--email", "maria@example.com"], session_factory=factory) == 0
    assert "2 generation(s) assigned" in capsys.readouterr().out
