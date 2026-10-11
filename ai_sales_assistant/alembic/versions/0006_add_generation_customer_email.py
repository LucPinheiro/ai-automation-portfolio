"""add customer email to generations

Adds `customer_email`, optional: it pre-fills the recipient of the share-by-email button and is
never sent to the AI provider. Existing generations keep all their data and get NULL.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-09 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, Sequence[str], None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('customer_email', sa.String(length=254), nullable=True))


def downgrade() -> None:
    """Downgrade schema (the customer emails are dropped; everything else is kept)."""
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.drop_column('customer_email')
