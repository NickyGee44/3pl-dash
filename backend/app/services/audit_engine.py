"""
Audit engine - computes metrics, lane stats, and exceptions.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Dict, Any, Optional
from decimal import Decimal
from uuid import UUID
import time
import logging
from app.models import Shipment, AuditResult, LaneStat, AuditRun
from app.models.audit_run import AuditRunStatus
from app.services.rating_pipeline import run_vectorized_rerate


logger = logging.getLogger(__name__)

def compute_cost_metrics(shipment: Shipment) -> Dict[str, Optional[Decimal]]:
    """Compute cost per lb and cost per pallet for a shipment."""
    cost_per_lb = None
    cost_per_pallet = None
    
    if shipment.actual_charge and shipment.weight and shipment.weight > 0:
        cost_per_lb = shipment.actual_charge / shipment.weight
    
    if shipment.actual_charge and shipment.pallets and shipment.pallets > 0:
        cost_per_pallet = shipment.actual_charge / shipment.pallets
    
    return {
        "cost_per_lb": cost_per_lb,
        "cost_per_pallet": cost_per_pallet,
    }


def compute_flags(shipment: Shipment, cost_per_lb: Optional[Decimal] = None) -> List[str]:
    """Compute exception flags for a shipment."""
    flags = []
    
    if not shipment.actual_charge or shipment.actual_charge <= 0:
        flags.append("ZERO_CHARGE")
    elif shipment.actual_charge < 0:
        flags.append("NEGATIVE_PRICE")
    
    if shipment.actual_charge and shipment.actual_charge > 0:
        if not shipment.weight or shipment.weight <= 0:
            flags.append("ZERO_WEIGHT")
        if not shipment.pallets or shipment.pallets <= 0:
            flags.append("ZERO_PALLETS")
    
    # Dim weight check
    if shipment.dim_weight and shipment.weight:
        dim_weight = Decimal(str(shipment.dim_weight))
        actual_weight = Decimal(str(shipment.weight))
        if dim_weight > actual_weight * Decimal("1.1"):  # 10% tolerance
            flags.append("DIM_HEAVY")
    
    return flags


def run_audit(db: Session, audit_run_id: UUID) -> Dict[str, Any]:
    """
    Run audit computations for an audit run.
    
    Returns summary dict with key metrics.
    """
    # Update status
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise ValueError(f"Audit run {audit_run_id} not found")
    
    audit_run.status = AuditRunStatus.PROCESSING.value
    db.commit()
    
    try:
        timings: Dict[str, float] = {}
        overall_start = time.perf_counter()
        # Load all shipments
        load_start = time.perf_counter()
        shipments = db.query(Shipment).filter(Shipment.audit_run_id == audit_run_id).all()
        timings["load_shipments"] = round(time.perf_counter() - load_start, 3)
        
        if not shipments:
            audit_run.status = AuditRunStatus.COMPLETED.value
            db.commit()
            return {
                "shipment_count": 0,
                "total_spend": 0,
                "total_weight": 0,
                "total_pallets": 0,
            }
        
        # Compute audit results for each shipment
        total_spend = Decimal(0)
        total_weight = Decimal(0)
        total_pallets = Decimal(0)
        
        processing_start = time.perf_counter()
        for shipment in shipments:
            metrics = compute_cost_metrics(shipment)
            flags = compute_flags(shipment, metrics["cost_per_lb"])
            
            # Get or create audit result
            audit_result = db.query(AuditResult).filter(
                AuditResult.shipment_id == shipment.id
            ).first()
            
            if not audit_result:
                audit_result = AuditResult(
                    audit_run_id=audit_run_id,
                    shipment_id=shipment.id,
                )
                db.add(audit_result)
            
            audit_result.cost_per_lb = metrics["cost_per_lb"]
            audit_result.cost_per_pallet = metrics["cost_per_pallet"]
            audit_result.flags = flags
            
            # Accumulate totals
            if shipment.actual_charge:
                total_spend += shipment.actual_charge
            if shipment.weight:
                total_weight += shipment.weight
            if shipment.pallets:
                total_pallets += shipment.pallets
        
        db.commit()
        timings["compute_metrics"] = round(time.perf_counter() - processing_start, 3)
        
        # Compute lane-level stats
        lane_start = time.perf_counter()
        compute_lane_stats(db, audit_run_id)
        timings["lane_stats"] = round(time.perf_counter() - lane_start, 3)
        
        # Compute theoretical best
        theoretical_start = time.perf_counter()
        compute_theoretical_best(db, audit_run_id)
        timings["theoretical_best"] = round(time.perf_counter() - theoretical_start, 3)
        
        # Build summary
        summary = {
            "shipment_count": len(shipments),
            "total_spend": float(total_spend),
            "total_weight": float(total_weight),
            "total_pallets": float(total_pallets),
            "avg_cost_per_shipment": float(total_spend / len(shipments)) if shipments else 0,
            "avg_cost_per_lb": float(total_spend / total_weight) if total_weight > 0 else None,
            "avg_cost_per_pallet": float(total_spend / total_pallets) if total_pallets > 0 else None,
            "timings": {**timings, "total": round(time.perf_counter() - overall_start, 3)},
        }
        
        # Update audit run
        audit_run.status = AuditRunStatus.COMPLETED.value
        audit_run.summary_metrics = summary
        db.commit()
        logger.info("Audit %s completed timings=%s", audit_run_id, summary["timings"])
        
        return summary
        
    except Exception as e:
        audit_run.status = AuditRunStatus.FAILED.value
        db.commit()
        raise


def compute_lane_stats(db: Session, audit_run_id: UUID) -> None:
    """Compute aggregated statistics by lane (origin_dc × dest_province/region)."""
    # Delete existing lane stats
    db.query(LaneStat).filter(LaneStat.audit_run_id == audit_run_id).delete()
    
    # Group by origin_dc and dest_province/region
    results = db.query(
        Shipment.origin_dc,
        Shipment.dest_province,
        Shipment.dest_region,
        Shipment.dest_city,
        func.count(Shipment.id).label("shipment_count"),
        func.sum(Shipment.actual_charge).label("total_spend"),
        func.sum(Shipment.weight).label("total_weight"),
        func.sum(Shipment.pallets).label("total_pallets"),
        func.avg(Shipment.actual_charge).label("avg_charge"),
    ).filter(
        Shipment.audit_run_id == audit_run_id
    ).group_by(
        Shipment.origin_dc,
        Shipment.dest_province,
        Shipment.dest_region,
        Shipment.dest_city,
    ).all()
    
    for row in results:
        lane_stat = LaneStat(
            audit_run_id=audit_run_id,
            origin_dc=row.origin_dc or "UNKNOWN",
            dest_province=row.dest_province,
            dest_region=row.dest_region,
            dest_city=row.dest_city,
            shipment_count=row.shipment_count or 0,
            total_spend=row.total_spend or Decimal(0),
            total_weight=row.total_weight or Decimal(0),
            total_pallets=row.total_pallets or Decimal(0),
            avg_charge_per_shipment=row.avg_charge,
        )
        
        # Compute averages
        if lane_stat.total_weight > 0:
            lane_stat.avg_cost_per_lb = lane_stat.total_spend / lane_stat.total_weight
        if lane_stat.total_pallets > 0:
            lane_stat.avg_cost_per_pallet = lane_stat.total_spend / lane_stat.total_pallets
        
        db.add(lane_stat)
    
    db.commit()


def compute_theoretical_best(db: Session, audit_run_id: UUID) -> None:
    """
    Compute theoretical best-case savings per lane.
    Uses minimum cost_per_lb within each lane as the "best case".
    (Legacy method - now prefer rerate_audit for tariff-based savings)
    """
    # Get all lane stats
    lane_stats = db.query(LaneStat).filter(LaneStat.audit_run_id == audit_run_id).all()
    
    # For each lane, find minimum cost_per_lb from shipments
    for lane_stat in lane_stats:
        min_cost_per_lb = db.query(
            func.min(AuditResult.cost_per_lb)
        ).join(
            Shipment, AuditResult.shipment_id == Shipment.id
        ).filter(
            and_(
                Shipment.audit_run_id == audit_run_id,
                Shipment.origin_dc == lane_stat.origin_dc,
                Shipment.dest_province == lane_stat.dest_province,
                AuditResult.cost_per_lb.isnot(None),
                AuditResult.cost_per_lb > 0,
            )
        ).scalar()
        
        if min_cost_per_lb and lane_stat.total_weight > 0:
            lane_stat.theoretical_best_spend = min_cost_per_lb * lane_stat.total_weight
            lane_stat.theoretical_savings = lane_stat.total_spend - lane_stat.theoretical_best_spend
            
            if lane_stat.total_spend > 0:
                lane_stat.savings_pct = (lane_stat.theoretical_savings / lane_stat.total_spend) * 100
    
    db.commit()


def rerate_audit(db: Session, audit_run_id: UUID, tariff_ids: Optional[List[UUID]] = None) -> Dict[str, Any]:
    """
    Re-rate all shipments in an audit run using tariff data.
    
    Args:
        audit_run_id: Audit run to re-rate
        tariff_ids: Optional list of specific tariff IDs to use. If None, uses all tariffs.
    
    Returns:
        Summary dict with total savings, etc.
    """
    timings: Dict[str, float] = {}
    overall_start = time.perf_counter()
    rerate_start = time.perf_counter()
    result = run_vectorized_rerate(db, audit_run_id, tariff_ids)
    timings["rerate_engine"] = round(time.perf_counter() - rerate_start, 3)
    
    db_update_start = time.perf_counter()
    shipments = db.query(Shipment).filter(Shipment.audit_run_id == audit_run_id).all()
    shipment_lookup = {str(s.id): s for s in shipments}
    
    for update in result.shipment_updates:
        shipment = shipment_lookup.get(update.shipment_id)
        if not shipment:
            continue
        
        audit_result = db.query(AuditResult).filter(
            AuditResult.shipment_id == shipment.id
        ).first()
        
        if not audit_result:
            audit_result = AuditResult(
                audit_run_id=audit_run_id,
                shipment_id=shipment.id
            )
            db.add(audit_result)
        
        audit_result.expected_charge_per_carrier = update.expected_charge_per_carrier
        audit_result.best_carrier = update.best_carrier
        audit_result.best_charge = update.best_charge
        audit_result.savings_vs_actual = update.savings_vs_actual
        audit_result.tariff_match_status = update.tariff_match_status
        audit_result.tariff_match_notes = update.tariff_match_notes
    
    db.commit()
    timings["db_update"] = round(time.perf_counter() - db_update_start, 3)
    
    # Recompute lane stats with tariff-based savings
    lane_start = time.perf_counter()
    compute_lane_stats_with_tariffs(db, audit_run_id)
    timings["lane_stats_with_tariffs"] = round(time.perf_counter() - lane_start, 3)
    
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    summary_metrics = audit_run.summary_metrics or {}
    summary_timings = summary_metrics.get("timings", {})
    summary_timings.update({f"rerate_{k}": v for k, v in timings.items()})
    summary_timings["rerate_total"] = round(time.perf_counter() - overall_start, 3)
    
    carrier_savings = result.carrier_savings_total
    carrier_best = result.carrier_best_total
    consolidation_savings = result.consolidation_savings_total
    total_opportunity = carrier_savings + consolidation_savings
    
    def _decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
        return float(value) if value is not None else None
    
    summary_metrics.update({
        "carrier_savings_total": _decimal_to_float(carrier_savings),
        "carrier_best_total": _decimal_to_float(carrier_best),
        "consolidation_savings_total": _decimal_to_float(consolidation_savings),
        "total_opportunity": _decimal_to_float(total_opportunity),
        "consolidation_groups": [
            {
                "origin_dc": group.origin_dc,
                "dest_city": group.dest_city,
                "dest_province": group.dest_province,
                "ship_date": group.ship_date.isoformat(),
                "shipment_count": group.shipment_count,
                "actual_sum": _decimal_to_float(group.actual_sum),
                "individual_best_sum": _decimal_to_float(group.individual_best_sum),
                "consolidated_charge": _decimal_to_float(group.consolidated_charge),
                "incremental_savings": _decimal_to_float(group.incremental_savings),
                "carrier": group.carrier,
            }
            for group in result.consolidation_groups
        ],
        "consolidation_group_count": result.consolidation_group_count,
        "theoretical_savings": _decimal_to_float(total_opportunity),
        "timings": summary_timings,
    })
    
    audit_run.summary_metrics = summary_metrics
    db.commit()
    logger.info("Rerate audit %s timings=%s", audit_run_id, summary_timings)
    
    return {
        "rerated_shipments": result.rerated_count,
        "total_potential_savings": _decimal_to_float(carrier_savings),
        "total_best_charge": _decimal_to_float(carrier_best),
        "consolidation_savings": _decimal_to_float(consolidation_savings),
        "total_opportunity": _decimal_to_float(total_opportunity),
        "top_consolidation": summary_metrics["consolidation_groups"],
    }


def compute_lane_stats_with_tariffs(db: Session, audit_run_id: UUID) -> None:
    """Update lane stats with tariff-based savings."""
    # Get lane stats
    lane_stats = db.query(LaneStat).filter(LaneStat.audit_run_id == audit_run_id).all()
    
    for lane_stat in lane_stats:
        # Aggregate savings from audit_results
        filters = [
            Shipment.audit_run_id == audit_run_id,
            Shipment.origin_dc == lane_stat.origin_dc,
        ]
        if lane_stat.dest_province:
            filters.append(Shipment.dest_province == lane_stat.dest_province)
        else:
            filters.append(Shipment.dest_province.is_(None))
        if lane_stat.dest_region:
            filters.append(Shipment.dest_region == lane_stat.dest_region)
        else:
            filters.append(Shipment.dest_region.is_(None))
        if lane_stat.dest_city:
            filters.append(Shipment.dest_city == lane_stat.dest_city)
        else:
            filters.append(Shipment.dest_city.is_(None))

        results = db.query(
            func.sum(AuditResult.savings_vs_actual).label("total_savings"),
            func.sum(AuditResult.best_charge).label("total_best")
        ).join(
            Shipment, AuditResult.shipment_id == Shipment.id
        ).filter(
            and_(*filters)
        ).first()
        
        if results and results.total_best:
            lane_stat.theoretical_best_spend = results.total_best
            lane_stat.theoretical_savings = results.total_savings or Decimal(0)
            
            if lane_stat.total_spend > 0:
                lane_stat.savings_pct = (lane_stat.theoretical_savings / lane_stat.total_spend) * 100
    
    db.commit()


def get_exceptions(db: Session, audit_run_id: UUID, exception_type: str = "all") -> List[Dict[str, Any]]:
    """
    Get exception shipments (zero charges, outliers, etc.).
    
    exception_type: "zero_charge", "outliers", "zero_weight", "all"
    """
    shipments = db.query(Shipment).join(
        AuditResult, Shipment.id == AuditResult.shipment_id
    ).filter(
        Shipment.audit_run_id == audit_run_id
    ).all()
    
    exceptions = []
    
    for shipment in shipments:
        audit_result = shipment.audit_result
        if not audit_result:
            continue
        
        flags = audit_result.flags or []
        
        if exception_type == "all" or exception_type in [f.lower().replace("_", "") for f in flags]:
            exceptions.append({
                "shipment_id": str(shipment.id),
                "shipment_ref": shipment.shipment_ref,
                "origin_dc": shipment.origin_dc,
                "dest_city": shipment.dest_city,
                "dest_province": shipment.dest_province,
                "weight": float(shipment.weight) if shipment.weight else None,
                "pallets": float(shipment.pallets) if shipment.pallets else None,
                "actual_charge": float(shipment.actual_charge) if shipment.actual_charge else None,
                "cost_per_lb": float(audit_result.cost_per_lb) if audit_result.cost_per_lb else None,
                "flags": flags,
                "tariff_match_status": audit_result.tariff_match_status,
                "tariff_match_notes": audit_result.tariff_match_notes,
                "expected_charge": float(audit_result.best_charge) if audit_result.best_charge else None,
                "best_carrier": audit_result.best_carrier,
            })
    
    # For outliers, sort by cost_per_lb descending
    if exception_type == "outliers":
        exceptions.sort(key=lambda x: x["cost_per_lb"] or 0, reverse=True)
        # Return top 50
        exceptions = exceptions[:50]
    
    return exceptions

