"""add catalog tables (categorias/materiales)

Revision ID: a1b2c3d4e5f6
Revises: d37e995fdd51
Create Date: 2025-10-24 20:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd37e995fdd51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'catalog_categorias',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nombre', sa.String(), nullable=False, unique=True),
        sa.Column('descripcion', sa.String(), nullable=True),
    )
    op.create_table(
        'catalog_materiales',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('nombre', sa.String(), nullable=False, unique=True),
        sa.Column('descripcion', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('catalog_materiales')
    op.drop_table('catalog_categorias')

