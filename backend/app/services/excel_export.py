"""
Excel export service.
"""
import pandas as pd
from sqlalchemy.orm import Session
from uuid import UUID
from pathlib import Path
import tempfile
from app.models import AuditRun, LaneStat, Shipment, AuditResult
from app.services.audit_engine import get_exceptions


def generate_excel_report(db: Session, audit_run_id: UUID) -> str:
    """
    Generate Excel report with multiple sheets:
    - Summary
    - Lane Stats
    - Exceptions
    - Top Outliers
    """
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise ValueError(f"Audit run {audit_run_id} not found")
    
    # Create temp file
    temp_dir = tempfile.gettempdir()
    file_path = Path(temp_dir) / f"audit_report_{audit_run_id}.xlsx"
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        # Summary sheet
        summary_data = {
            "Metric": [
                "Audit Run Name",
                "Customer",
                "Total Shipments",
                "Total Spend",
                "Total Weight (lbs)",
                "Average Cost per Shipment",
                "Average Cost per Pound",
            ],
            "Value": [
                audit_run.name,
                audit_run.customer.name,
                audit_run.summary_metrics.get("shipment_count", 0) if audit_run.summary_metrics else 0,
                f"${audit_run.summary_metrics.get('total_spend', 0):,.2f}" if audit_run.summary_metrics else "$0.00",
                f"{audit_run.summary_metrics.get('total_weight', 0):,.0f}" if audit_run.summary_metrics else "0",
                f"${audit_run.summary_metrics.get('avg_cost_per_shipment', 0):,.2f}" if audit_run.summary_metrics else "$0.00",
                f"${audit_run.summary_metrics.get('avg_cost_per_lb', 0):,.4f}" if audit_run.summary_metrics else "$0.00",
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)
        
        # Lane Stats sheet
        lane_stats = db.query(LaneStat).filter(
            LaneStat.audit_run_id == audit_run_id
        ).order_by(LaneStat.total_spend.desc()).all()
        
        lane_data = []
        for ls in lane_stats:
            lane_data.append({
                "Origin DC": ls.origin_dc,
                "Dest Province": ls.dest_province or "",
                "Dest Region": ls.dest_region or "",
                "Shipment Count": ls.shipment_count,
                "Total Spend": float(ls.total_spend),
                "Total Weight": float(ls.total_weight),
                "Avg Cost/Lb": float(ls.avg_cost_per_lb) if ls.avg_cost_per_lb else None,
                "Theoretical Best Spend": float(ls.theoretical_best_spend) if ls.theoretical_best_spend else None,
                "Potential Savings": float(ls.theoretical_savings) if ls.theoretical_savings else None,
                "Savings %": float(ls.savings_pct) if ls.savings_pct else None,
            })
        
        if lane_data:
            pd.DataFrame(lane_data).to_excel(writer, sheet_name="Lane Stats", index=False)
        
        # Exceptions sheet
        exceptions = get_exceptions(db, audit_run_id, "all")
        if exceptions:
            pd.DataFrame(exceptions).to_excel(writer, sheet_name="Exceptions", index=False)
        
        # Top Outliers sheet
        outliers = get_exceptions(db, audit_run_id, "outliers")
        if outliers:
            pd.DataFrame(outliers).to_excel(writer, sheet_name="Top Outliers", index=False)
    
    return str(file_path)

