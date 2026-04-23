"""merge heads

Revision ID: 5b08bf447c19
Revises: 4574cf78c46d, 8a7f9c1d2e3f
Create Date: 2026-04-23 10:27:24.385854

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b08bf447c19'
down_revision: Union[str, None] = ('4574cf78c46d', '8a7f9c1d2e3f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
