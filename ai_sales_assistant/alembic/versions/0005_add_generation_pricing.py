"""add pricing to generations

Adds the pricing input of a generation as exact integers:
- price_cents: original price in euro cents (179.00 EUR -> 17900).
- discount_basis_points: discount in hundredths of a percent (15 % -> 1500).

The discount amount and the final price are derived (app.services.pricing) and not stored.
Existing generations keep all their data and get NULL (no price).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-08 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, Sequence[str], None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Names without prefix: the naming convention turns them into ck_generations_<name> (as in the model).
CHECKS = {
    'price_positive': 'price_cents > 0',
    'discount_in_range': 'discount_basis_points BETWEEN 0 AND 10000',
    'discount_requires_price': 'discount_basis_points IS NULL OR price_cents IS NOT NULL',
}


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('generations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('price_cents', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('discount_basis_points', sa.Integer(), nullable=True))
        for name, condition in CHECKS.items():
            batch_op.create_check_constraint(name, condition)


def downgrade() -> None:
    """Downgrade schema (pricing data is dropped; everything else is kept)."""
    with op.batch_alter_table('generations', schema=None) as batch_op:
        for name in CHECKS:
            batch_op.drop_constraint(op.f(f'ck_generations_{name}'), type_='check')
        batch_op.drop_column('discount_basis_points')
        batch_op.drop_column('price_cents')
