"""Expand lane_stats.savings_pct precision

Revision ID: 20251129_expand_savings_pct
Revises: 
Create Date: 2025-11-29 16:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251129_expand_savings_pct"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "lane_stats",
        "savings_pct",
        type_=sa.Numeric(10, 4),
        existing_type=sa.Numeric(5, 2),
        existing_nullable=True,
    )


def downgrade():
    op.alter_column(
        "lane_stats",
        "savings_pct",
        type_=sa.Numeric(5, 2),
        existing_type=sa.Numeric(10, 4),
        existing_nullable=True,
    )

