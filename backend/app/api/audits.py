"""
Audit Run API endpoints.
"""
import logging
import traceback
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from app.db.database import get_db
from app.models import Customer, AuditRun
from app.schemas.audit_run import (
    AuditRunCreate,
    AuditRunResponse,
    AuditRunSummary,
    AuditQuestionRequest,
)
from app.services.audit_engine import run_audit, rerate_audit
from app.services.report_context import build_report_context
from app.services.llm_reports import answer_audit_question

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=AuditRunResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_run(
    audit_data: AuditRunCreate,
    db: Session = Depends(get_db)
):
    """Create a new audit run."""
    try:
        logger.info(f"Creating audit run: customer_id={audit_data.customer_id}, name={audit_data.name}")
        
        # Verify customer exists
        customer = db.query(Customer).filter(Customer.id == audit_data.customer_id).first()
        if not customer:
            logger.warning(f"Customer not found: {audit_data.customer_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer {audit_data.customer_id} not found"
            )
        
        # Validate audit name is not empty
        if not audit_data.name or not audit_data.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audit name cannot be empty"
            )
        
        # Process label - handle empty strings
        label_value = None
        if audit_data.label:
            label_stripped = audit_data.label.strip()
            label_value = label_stripped if label_stripped else None
        
        logger.info(f"Creating AuditRun object with: customer_id={audit_data.customer_id}, name={audit_data.name.strip()}, label={label_value}")
        
        audit_run = AuditRun(
            customer_id=audit_data.customer_id,
            name=audit_data.name.strip(),
            label=label_value,
        )
        db.add(audit_run)
        logger.info("AuditRun added to session, committing...")
        db.commit()
        logger.info("Commit successful, refreshing...")
        db.refresh(audit_run)
        logger.info(f"Audit run created successfully: id={audit_run.id}")
        
        return audit_run
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        error_trace = traceback.format_exc()
        logger.error(f"Error creating audit run: {str(e)}")
        logger.error(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create audit run: {str(e)}"
        )


@router.get("/", response_model=List[AuditRunSummary])
async def list_audit_runs(
    customer_id: UUID = None,
    db: Session = Depends(get_db)
):
    """List all audit runs, optionally filtered by customer."""
    query = db.query(AuditRun).join(Customer)
    
    if customer_id:
        query = query.filter(AuditRun.customer_id == customer_id)
    
    audit_runs = query.order_by(AuditRun.created_at.desc()).all()
    
    results = []
    for ar in audit_runs:
        summary_metrics = ar.summary_metrics or {}
        results.append(AuditRunSummary(
            id=ar.id,
            customer_name=ar.customer.name,
            name=ar.name,
            label=ar.label,
            status=ar.status,
            created_at=ar.created_at,
            shipment_count=summary_metrics.get("shipment_count", 0),
            total_spend=summary_metrics.get("total_spend"),
            theoretical_savings=summary_metrics.get("theoretical_savings"),
            carrier_savings_total=summary_metrics.get("carrier_savings_total"),
            consolidation_savings_total=summary_metrics.get("consolidation_savings_total"),
            total_opportunity=summary_metrics.get("total_opportunity"),
        ))
    
    return results


@router.get("/{audit_run_id}", response_model=AuditRunResponse)
async def get_audit_run(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific audit run."""
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit run {audit_run_id} not found"
        )
    return audit_run


@router.get("/{audit_run_id}/summary", status_code=status.HTTP_200_OK)
async def get_audit_summary(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Get comprehensive audit summary with spend, savings, and savings %."""
    from app.models import Shipment, LaneStat
    from sqlalchemy import func
    
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit run {audit_run_id} not found"
        )
    
    # Get shipment totals
    shipment_stats = db.query(
        func.count(Shipment.id).label("shipment_count"),
        func.sum(Shipment.actual_charge).label("total_spend"),
        func.sum(Shipment.weight).label("total_weight"),
        func.sum(Shipment.pallets).label("total_pallets"),
    ).filter(Shipment.audit_run_id == audit_run_id).first()
    
    # Get lane stats summary
    lane_stats = db.query(LaneStat).filter(LaneStat.audit_run_id == audit_run_id).all()
    
    # Calculate totals from lane stats
    total_theoretical_savings = sum(
        float(ls.theoretical_savings or 0) for ls in lane_stats
    )
    total_theoretical_best = sum(
        float(ls.theoretical_best_spend or 0) for ls in lane_stats
    )
    
    total_spend = float(shipment_stats.total_spend or 0)
    savings_pct = (total_theoretical_savings / total_spend * 100) if total_spend > 0 else 0
    
    # Get summary metrics from audit run
    summary_metrics = audit_run.summary_metrics or {}
    
    return {
        "audit_id": str(audit_run.id),
        "audit_name": audit_run.name,
        "status": audit_run.status,
        "shipment_count": shipment_stats.shipment_count or 0,
        "total_spend": total_spend,
        "total_weight": float(shipment_stats.total_weight or 0),
        "total_pallets": float(shipment_stats.total_pallets or 0),
        "avg_cost_per_shipment": total_spend / shipment_stats.shipment_count if shipment_stats.shipment_count else 0,
        "avg_cost_per_lb": total_spend / float(shipment_stats.total_weight) if shipment_stats.total_weight else 0,
        # Savings from tariff re-rating
        "carrier_savings_total": summary_metrics.get("carrier_savings_total", 0),
        "consolidation_savings_total": summary_metrics.get("consolidation_savings_total", 0),
        "total_opportunity": summary_metrics.get("total_opportunity", 0),
        # Lane-level theoretical savings
        "theoretical_best_spend": total_theoretical_best,
        "theoretical_savings": total_theoretical_savings,
        "savings_pct": round(savings_pct, 2),
        # Lane count
        "lane_count": len(lane_stats),
        # Origin DC breakdown
        "origin_dc_breakdown": _get_origin_dc_breakdown(db, audit_run_id),
        # Region breakdown
        "region_breakdown": _get_region_breakdown(db, audit_run_id),
    }


def _get_origin_dc_breakdown(db: Session, audit_run_id: UUID) -> list:
    """Get spend breakdown by origin DC."""
    from app.models import Shipment
    from sqlalchemy import func
    
    results = db.query(
        Shipment.origin_dc,
        func.count(Shipment.id).label("shipment_count"),
        func.sum(Shipment.actual_charge).label("total_spend"),
    ).filter(
        Shipment.audit_run_id == audit_run_id
    ).group_by(Shipment.origin_dc).all()
    
    return [
        {
            "origin_dc": r.origin_dc or "UNKNOWN",
            "shipment_count": r.shipment_count,
            "total_spend": float(r.total_spend or 0),
        }
        for r in results
    ]


def _get_region_breakdown(db: Session, audit_run_id: UUID) -> list:
    """Get spend breakdown by destination region."""
    from app.models import Shipment
    from sqlalchemy import func
    
    results = db.query(
        Shipment.dest_region,
        func.count(Shipment.id).label("shipment_count"),
        func.sum(Shipment.actual_charge).label("total_spend"),
    ).filter(
        Shipment.audit_run_id == audit_run_id
    ).group_by(Shipment.dest_region).all()
    
    return [
        {
            "region": r.dest_region or "UNKNOWN",
            "shipment_count": r.shipment_count,
            "total_spend": float(r.total_spend or 0),
        }
        for r in results
    ]


@router.post("/{audit_run_id}/run", status_code=status.HTTP_200_OK)
async def trigger_audit(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Trigger audit computation for an audit run."""
    try:
        summary = run_audit(db, audit_run_id)
        return {"message": "Audit completed successfully", "summary": summary}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit failed: {str(e)}"
        )


@router.post("/{audit_run_id}/rerate", status_code=status.HTTP_200_OK)
async def trigger_rerate(
    audit_run_id: UUID,
    tariff_ids: Optional[List[UUID]] = None,
    db: Session = Depends(get_db)
):
    """Re-rate all shipments in an audit run using tariff data."""
    try:
        result = rerate_audit(db, audit_run_id, tariff_ids)
        return {"message": "Re-rating completed successfully", "result": result}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Re-rating failed: {str(e)}"
        )


@router.get("/{audit_run_id}/report-context", status_code=status.HTTP_200_OK)
async def get_report_context(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Return structured JSON context for an audit run."""
    try:
        context = build_report_context(db, audit_run_id)
        return {"context": context}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build report context: {str(e)}"
        )


@router.get("/{audit_run_id}/lane-stats", status_code=status.HTTP_200_OK)
async def get_lane_stats(
    audit_run_id: UUID,
    db: Session = Depends(get_db)
):
    """Get detailed lane statistics for an audit run."""
    from app.models import LaneStat
    
    lane_stats = db.query(LaneStat).filter(
        LaneStat.audit_run_id == audit_run_id
    ).order_by(
        LaneStat.total_spend.desc()
    ).all()
    
    return {
        "lane_stats": [
            {
                "origin_dc": ls.origin_dc,
                "dest_city": ls.dest_city,
                "dest_province": ls.dest_province,
                "dest_region": ls.dest_region,
                "shipment_count": ls.shipment_count,
                "total_spend": float(ls.total_spend) if ls.total_spend else 0,
                "total_weight": float(ls.total_weight) if ls.total_weight else 0,
                "total_pallets": float(ls.total_pallets) if ls.total_pallets else 0,
                "avg_charge_per_shipment": float(ls.avg_charge_per_shipment) if ls.avg_charge_per_shipment else None,
                "avg_cost_per_lb": float(ls.avg_cost_per_lb) if ls.avg_cost_per_lb else None,
                "avg_cost_per_pallet": float(ls.avg_cost_per_pallet) if ls.avg_cost_per_pallet else None,
                "theoretical_best_spend": float(ls.theoretical_best_spend) if ls.theoretical_best_spend else None,
                "theoretical_savings": float(ls.theoretical_savings) if ls.theoretical_savings else None,
                "savings_pct": float(ls.savings_pct) if ls.savings_pct else None,
            }
            for ls in lane_stats
        ]
    }


@router.get("/{audit_run_id}/exceptions", status_code=status.HTTP_200_OK)
async def get_audit_exceptions(
    audit_run_id: UUID,
    exception_type: str = "all",
    db: Session = Depends(get_db)
):
    """Get exception shipments for an audit run."""
    from app.services.audit_engine import get_exceptions
    
    exceptions = get_exceptions(db, audit_run_id, exception_type)
    return {"exceptions": exceptions, "count": len(exceptions)}


@router.post("/{audit_run_id}/ask", status_code=status.HTTP_200_OK)
async def ask_ai_about_audit(
    audit_run_id: UUID,
    payload: AuditQuestionRequest,
    db: Session = Depends(get_db)
):
    """Allow users to ask AI questions about a specific audit run."""
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty"
        )
    try:
        answer = answer_audit_question(db, audit_run_id, question)
        return {"answer": answer}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI analysis failed: {str(e)}"
        )

