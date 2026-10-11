"""Administrative commands.

    python -m app.cli assign-orphan-generations --email you@example.com [--dry-run]
    python -m app.cli purge-expired-guests

Generations created before user accounts existed have no owner (user_id NULL) and are
invisible to every user. This command assigns all of them to one registered account.
"""

import argparse
import sys
from collections.abc import Callable, Sequence
from datetime import timedelta

from sqlalchemy.orm import Session

from app.repositories.generation_repository import GenerationRepository
from app.repositories.user_repository import UserRepository


class AccountNotFoundError(LookupError):
    pass


def assign_orphan_generations(session: Session, email: str, *, dry_run: bool = False) -> tuple[int, str]:
    """Assign every unowned generation to the account with `email`. Returns (count, message)."""
    user = UserRepository(session).get_by_email(email)
    if user is None:
        raise AccountNotFoundError(f"No account found for {email!r}. Register it first in the web app.")

    generations = GenerationRepository(session)
    if dry_run:
        pending = generations.count_unassigned()
        return pending, f"[dry-run] {pending} unassigned generation(s) would be assigned to user {user.id}."

    try:
        assigned = generations.assign_unassigned_to(user.id)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return assigned, f"{assigned} generation(s) assigned to user {user.id}."


def purge_expired_guests(session: Session) -> int:
    from app.config import get_settings
    from app.services.auth_service import AuthService

    settings = get_settings()
    auth = AuthService(
        session,
        session_ttl=timedelta(hours=settings.session_ttl_hours),
        reset_token_ttl=timedelta(minutes=settings.password_reset_ttl_minutes),
    )
    return auth.purge_expired_guests()


def main(argv: Sequence[str] | None = None, session_factory: Callable[[], Session] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="AI Sales Assistant administration.")
    commands = parser.add_subparsers(dest="command", required=True)
    assign = commands.add_parser(
        "assign-orphan-generations", help="Assign generations without an owner to a registered account."
    )
    assign.add_argument("--email", required=True, help="Email of the registered account that will own them.")
    assign.add_argument("--dry-run", action="store_true", help="Only show how many would be assigned.")
    commands.add_parser(
        "purge-expired-guests", help="Delete guests whose session expired, with their generations."
    )
    args = parser.parse_args(argv)

    if session_factory is None:
        from app.database import SessionLocal

        session_factory = SessionLocal

    with session_factory() as session:
        if args.command == "purge-expired-guests":
            print(f"{purge_expired_guests(session)} expired guest(s) deleted with their generations.")
            return 0
        try:
            _, message = assign_orphan_generations(session, args.email, dry_run=args.dry_run)
        except AccountNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
