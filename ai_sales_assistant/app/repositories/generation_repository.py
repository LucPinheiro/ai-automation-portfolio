from typing import Any

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.orm import Session

from app.core.enums import ContentType
from app.models.generation import Generation


class GenerationRepository:
    """Persistence operations for `Generation`.

    Transactions are owned by the caller (the service layer): this class
    flushes but never commits.

    Every user-facing query is scoped to an owner (`user_id`), so a generation
    can never be read, listed, changed or deleted through another account.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, generation: Generation) -> Generation:
        self._session.add(generation)
        self._session.flush()
        return generation

    def delete(self, generation: Generation) -> None:
        self._session.delete(generation)
        self._session.flush()

    def get_by_id(self, generation_id: int) -> Generation | None:
        """Unscoped lookup, for internal use only (never with ids coming from a client)."""
        return self._session.get(Generation, generation_id)

    def get_for_user(self, generation_id: int, *, user_id: int) -> Generation | None:
        statement = _owned_by(select(Generation), user_id).where(Generation.id == generation_id)
        return self._session.scalar(statement)

    def list_paginated(
        self, *, user_id: int, limit: int, offset: int, content_type: ContentType | None = None
    ) -> list[Generation]:
        statement = (
            self._filtered(_owned_by(select(Generation), user_id), content_type)
            .order_by(Generation.created_at.desc(), Generation.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.scalars(statement))

    def count(self, *, user_id: int, content_type: ContentType | None = None) -> int:
        statement = self._filtered(_owned_by(select(func.count()).select_from(Generation), user_id), content_type)
        return self._session.scalar(statement) or 0

    # --- Bulk operations on an owner's generations -----------------------------------

    def delete_all_for_users(self, user_ids: list[int]) -> int:
        if not user_ids:
            return 0
        return self._session.execute(delete(Generation).where(Generation.user_id.in_(user_ids))).rowcount or 0

    def transfer(self, *, from_user_id: int, to_user_id: int) -> int:
        result = self._session.execute(
            update(Generation).where(Generation.user_id == from_user_id).values(user_id=to_user_id)
        )
        return result.rowcount or 0

    # --- Generations created before user accounts existed (user_id IS NULL) ---------

    def count_unassigned(self) -> int:
        return self._session.scalar(select(func.count()).select_from(Generation).where(Generation.user_id.is_(None))) or 0

    def assign_unassigned_to(self, user_id: int) -> int:
        result = self._session.execute(
            update(Generation).where(Generation.user_id.is_(None)).values(user_id=user_id)
        )
        return result.rowcount or 0

    @staticmethod
    def _filtered(statement: Select[Any], content_type: ContentType | None) -> Select[Any]:
        if content_type is None:
            return statement
        return statement.where(Generation.content_type == content_type)


def _owned_by(statement: Select[Any], user_id: int) -> Select[Any]:
    # `Generation.user_id == None` would become `IS NULL` and expose unassigned rows.
    if not isinstance(user_id, int):
        raise ValueError("An owner user_id is required.")
    return statement.where(Generation.user_id == user_id)
