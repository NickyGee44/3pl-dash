"""
Report generation API endpoints (LLM, Excel, PDF).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
import os
from app.db.database import get_db
from app.models import AuditRun, LaneStat, AuditResult, Shipment
from app.services.llm_reports import generate_executive_summary
from app.services.export import generate_excel_report, generate_pdf_report

router = APIRouter()


@router.post("/{audit_run_id}/executive-summary")
async def create_executive_summary(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Generate executive summary using ChatGPT."""
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit run {audit_run_id} not found"
        )
    
    try:
        summary = generate_executive_summary(db, audit_run_id)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating summary: {str(e)}"
        )


@router.get("/{audit_run_id}/excel")
async def download_excel_report(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Download Excel report with lane breakdown and exceptions."""
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit run {audit_run_id} not found"
        )
    
    try:
        file_path = generate_excel_report(db, audit_run_id)
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"audit_report_{audit_run_id}.xlsx"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating Excel report: {str(e)}"
        )


@router.get("/{audit_run_id}/pdf")
async def download_pdf_report(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Download PDF executive summary."""
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit run {audit_run_id} not found"
        )
    
    try:
        file_path = generate_pdf_report(db, audit_run_id)
        return FileResponse(
            file_path,
            media_type="application/pdf",
            filename=f"audit_summary_{audit_run_id}.pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating PDF report: {str(e)}"
        )


@router.get("/{audit_run_id}/exceptions")
async def get_exceptions(
    audit_run_id: UUID,
    exception_type: str = "all",
    db: Session = Depends(get_db)
):
    """Get exception shipments."""
    from app.services.audit_engine import get_exceptions
    
    try:
        exceptions = get_exceptions(db, audit_run_id, exception_type)
        return {"exceptions": exceptions, "count": len(exceptions)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching exceptions: {str(e)}"
        )


@router.get("/{audit_run_id}/lanes")
async def get_lane_stats(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Get lane-level statistics."""
    lane_stats = db.query(LaneStat).filter(
        LaneStat.audit_run_id == audit_run_id
    ).order_by(LaneStat.total_spend.desc()).all()
    
    return {
        "lanes": [
            {
                "id": str(ls.id),
                "origin_dc": ls.origin_dc,
                "dest_province": ls.dest_province,
                "dest_region": ls.dest_region,
                "dest_city": ls.dest_city,
                "shipment_count": ls.shipment_count,
                "total_spend": float(ls.total_spend),
                "total_weight": float(ls.total_weight),
                "total_pallets": float(ls.total_pallets),
                "avg_cost_per_lb": float(ls.avg_cost_per_lb) if ls.avg_cost_per_lb else None,
                "avg_cost_per_pallet": float(ls.avg_cost_per_pallet) if ls.avg_cost_per_pallet else None,
                "theoretical_best_spend": float(ls.theoretical_best_spend) if ls.theoretical_best_spend else None,
                "theoretical_savings": float(ls.theoretical_savings) if ls.theoretical_savings else None,
                "savings_pct": float(ls.savings_pct) if ls.savings_pct else None,
            }
            for ls in lane_stats
        ]
    }
