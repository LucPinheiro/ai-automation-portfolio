"""add salesperson to generations

Adds the sender of each communication: `salesperson` and `salesperson_company`, both optional.
Existing generations keep all their data and get NULL in the new columns: no name is invented.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-08 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('salesperson', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('salesperson_company', sa.String(length=150), nullable=True))


def downgrade() -> None:
    """Downgrade schema (the salesperson data is dropped; everything else is kept)."""
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.drop_column('salesperson_company')
        batch_op.drop_column('salesperson')
