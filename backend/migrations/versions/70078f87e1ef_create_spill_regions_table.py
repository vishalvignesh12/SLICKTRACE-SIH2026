"""create_spill_regions_table

Revision ID: 70078f87e1ef
Revises: 968577e94564
Create Date: 2026-08-31 10:59:52.681394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2.types import Geometry


# revision identifiers, used by Alembic.
revision: str = '70078f87e1ef'
down_revision: Union[str, Sequence[str], None] = '968577e94564'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'spill_regions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('detection_id', sa.UUID(), nullable=False),
        sa.Column('region_index', sa.Integer(), nullable=False),
        sa.Column('geometry', Geometry(geometry_type='POLYGON', srid=4326, from_text='ST_GeomFromEWKT', name='geometry'), nullable=False),
        sa.Column('area_m2', sa.Float(), nullable=False),
        sa.Column('perimeter_m', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('mask_uri', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['detection_id'], ['slick_detections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_spill_regions_geometry', 'spill_regions', ['geometry'], postgresql_using='gist')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_spill_regions_geometry', table_name='spill_regions')
    op.drop_table('spill_regions')
