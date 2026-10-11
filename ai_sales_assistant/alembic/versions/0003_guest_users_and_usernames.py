"""guest users and usernames

Adds guest accounts ("Entrar sin iniciar sesión") and optional usernames:
- users.username: optional, unique, lowercase; login accepts username or email.
- users.is_guest: existing accounts become registered users (false).
- users.ai_generation_count: AI calls made by the account (guest generation limit).
- users.email and users.password_hash become nullable, but only for guests: a CHECK constraint
  keeps them mandatory for registered accounts.

Generations and existing accounts are not modified.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-08 12:31:16.681660

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The naming convention turns this into ck_users_registered_has_credentials (as in the model).
CHECK_NAME = 'registered_has_credentials'
CHECK_SQL = 'is_guest OR (email IS NOT NULL AND password_hash IS NOT NULL)'


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=30), nullable=True))
        batch_op.add_column(sa.Column('is_guest', sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column('ai_generation_count', sa.Integer(), server_default='0', nullable=False))
        batch_op.alter_column('email',
               existing_type=sa.VARCHAR(length=254),
               nullable=True)
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
        batch_op.create_unique_constraint(batch_op.f('uq_users_username'), ['username'])
        batch_op.create_check_constraint(CHECK_NAME, CHECK_SQL)


def downgrade() -> None:
    """Downgrade schema.

    Guests cannot exist without these columns: they are deleted first, with their sessions and
    generations (guest data is temporary by design). Registered accounts are kept.
    """
    guests = 'SELECT id FROM users WHERE is_guest'
    op.execute(f'DELETE FROM generations WHERE user_id IN ({guests})')
    op.execute(f'DELETE FROM user_sessions WHERE user_id IN ({guests})')
    op.execute(f'DELETE FROM password_reset_tokens WHERE user_id IN ({guests})')
    op.execute('DELETE FROM users WHERE is_guest')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_users_registered_has_credentials'), type_='check')
        batch_op.drop_constraint(batch_op.f('uq_users_username'), type_='unique')
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)
        batch_op.alter_column('email',
               existing_type=sa.VARCHAR(length=254),
               nullable=False)
        batch_op.drop_column('ai_generation_count')
        batch_op.drop_column('is_guest')
        batch_op.drop_column('username')
