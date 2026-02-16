"""Bootstrap schema and ensure lane_stats.savings_pct precision

Revision ID: 20251129_expand_savings_pct
Revises: 
Create Date: 2025-11-29 16:40:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20251129_expand_savings_pct"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    app_tables = {
        "customers",
        "audit_runs",
        "source_files",
        "shipments",
        "audit_results",
        "lane_stats",
        "tariffs",
        "tariff_lanes",
        "tariff_breaks",
    }

    existing_tables = set(inspector.get_table_names())

    # Fresh DB bootstrap: create all modeled tables if app schema doesn't exist yet.
    if not existing_tables.intersection(app_tables):
        from app.db.database import Base
        from app.models import (  # noqa: F401
            Customer,
            AuditRun,
            SourceFile,
            Shipment,
            AuditResult,
            LaneStat,
            Tariff,
            TariffLane,
            TariffBreak,
        )

        Base.metadata.create_all(bind=bind)
        inspector = inspect(bind)
        existing_tables = set(inspector.get_table_names())

    # Legacy DB compatibility: ensure new audit_results columns exist.
    if "audit_results" in existing_tables:
        audit_results_columns = {
            col["name"] for col in inspector.get_columns("audit_results")
        }
        if "tariff_match_status" not in audit_results_columns:
            op.add_column(
                "audit_results",
                sa.Column("tariff_match_status", sa.String(length=50), nullable=True),
            )
        if "tariff_match_notes" not in audit_results_columns:
            op.add_column(
                "audit_results",
                sa.Column("tariff_match_notes", sa.String(length=255), nullable=True),
            )
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_results_tariff_match_status "
            "ON audit_results(tariff_match_status)"
        )

    # Keep precision migration behavior for lane_stats.savings_pct.
    if "lane_stats" in existing_tables:
        lane_columns = {col["name"] for col in inspector.get_columns("lane_stats")}
        if "savings_pct" in lane_columns:
            op.execute(
                "ALTER TABLE lane_stats "
                "ALTER COLUMN savings_pct TYPE NUMERIC(10,4)"
            )


def downgrade():
    # Non-destructive baseline migration. No automatic downgrade.
    pass
