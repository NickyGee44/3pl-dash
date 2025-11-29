"""
Builds structured JSON context for audits (used by AI + PPT generation).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AuditRun, LaneStat, Shipment, AuditResult
from app.services.audit_engine import get_exceptions

REGION_MAP = {
    "BC": "West",
    "AB": "West",
    "SK": "West",
    "MB": "West",
    "ON": "Ontario",
    "QC": "Quebec",
    "NB": "Maritimes",
    "NS": "Maritimes",
    "PE": "Maritimes",
    "NL": "Maritimes",
    "YT": "North",
    "NT": "North",
    "NU": "North",
}


def _decimal_to_float(value: Optional[Decimal]) -> Optional[float]:
    return float(value) if value is not None else None


def _format_currency(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"))) if value is not None else 0.0


def _infer_region(shipment: Shipment) -> str:
    if shipment.dest_region:
        return shipment.dest_region
    province = (shipment.dest_province or "").upper().strip()
    return REGION_MAP.get(province, province or "Unknown")


def _gather_shipments(db: Session, audit_run_id: UUID) -> List[Shipment]:
    return db.query(Shipment).filter(Shipment.audit_run_id == audit_run_id).all()


def _gather_lane_stats(db: Session, audit_run_id: UUID) -> List[LaneStat]:
    return (
        db.query(LaneStat)
        .filter(LaneStat.audit_run_id == audit_run_id)
        .order_by(LaneStat.total_spend.desc())
        .all()
    )


def _carrier_savings(db: Session, audit_run_id: UUID) -> Decimal:
    value = (
        db.query(func.sum(AuditResult.savings_vs_actual))
        .join(Shipment, AuditResult.shipment_id == Shipment.id)
        .filter(Shipment.audit_run_id == audit_run_id)
        .scalar()
    )
    return value or Decimal("0")


def build_report_context(db: Session, audit_run_id: UUID) -> Dict[str, Any]:
    audit_run = (
        db.query(AuditRun)
        .filter(AuditRun.id == audit_run_id)
        .first()
    )
    if not audit_run:
        raise ValueError(f"Audit run {audit_run_id} not found")

    shipments = _gather_shipments(db, audit_run_id)
    lane_stats = _gather_lane_stats(db, audit_run_id)

    total_shipments = len(shipments)
    total_spend = Decimal("0")
    total_weight = Decimal("0")
    total_pallets = Decimal("0")

    dc_stats: Dict[str, Dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    region_stats: Dict[str, Dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))

    for shipment in shipments:
        actual = shipment.actual_charge or Decimal("0")
        weight = shipment.weight or Decimal("0")
        pallets = shipment.pallets or Decimal("0")

        total_spend += actual
        total_weight += weight
        total_pallets += pallets

        dc_key = (shipment.origin_dc or "UNKNOWN").upper()
        dc_stats[dc_key]["shipments"] += 1
        dc_stats[dc_key]["spend"] += actual
        dc_stats[dc_key]["weight"] += weight

        region_key = _infer_region(shipment)
        region_stats[region_key]["shipments"] += 1
        region_stats[region_key]["spend"] += actual
        region_stats[region_key]["weight"] += weight

    summary_metrics = audit_run.summary_metrics or {}
    carrier_savings = summary_metrics.get("carrier_savings_total")
    consolidation_savings = summary_metrics.get("consolidation_savings_total")

    # Fallback to DB values if summary not populated
    carrier_savings_decimal = (
        Decimal(str(carrier_savings))
        if carrier_savings is not None
        else _carrier_savings(db, audit_run_id)
    )
    consolidation_savings_decimal = (
        Decimal(str(consolidation_savings))
        if consolidation_savings is not None
        else Decimal("0")
    )

    total_opportunity = carrier_savings_decimal + consolidation_savings_decimal

    lane_spend = [
        {
            "origin_dc": lane.origin_dc,
            "destination": lane.dest_province or lane.dest_region or lane.dest_city or "Unknown",
            "total_spend": _decimal_to_float(lane.total_spend),
            "shipments": lane.shipment_count,
            "savings": _decimal_to_float(lane.theoretical_savings),
        }
        for lane in lane_stats[:10]
    ]

    top_savings = [
        {
            "origin_dc": lane.origin_dc,
            "destination": lane.dest_province or lane.dest_region or lane.dest_city or "Unknown",
            "savings": _decimal_to_float(lane.theoretical_savings),
            "savings_pct": _decimal_to_float(lane.savings_pct),
        }
        for lane in sorted(
            lane_stats,
            key=lambda ls: ls.theoretical_savings or Decimal("0"),
            reverse=True,
        )[:10]
        if lane.theoretical_savings
    ]

    exceptions = get_exceptions(db, audit_run_id, "all")
    zero_charge = sum(1 for exc in exceptions if "ZERO_CHARGE" in exc.get("flags", []))
    dim_heavy = sum(1 for exc in exceptions if "DIM_HEAVY" in exc.get("flags", []))

    return {
        "audit": {
            "id": str(audit_run.id),
            "name": audit_run.name,
            "label": audit_run.label,
            "customer": audit_run.customer.name if audit_run.customer else None,
            "status": audit_run.status.value,
            "created_at": audit_run.created_at.isoformat(),
        },
        "totals": {
            "shipments": total_shipments,
            "spend": _format_currency(total_spend),
            "weight": _format_currency(total_weight),
            "pallets": _format_currency(total_pallets),
            "avg_cost_per_shipment": _format_currency(total_spend / total_shipments)
            if total_shipments
            else 0.0,
        },
        "carrier_optimization": {
            "savings": _decimal_to_float(carrier_savings_decimal),
            "best_charge_total": summary_metrics.get("carrier_best_total"),
            "opportunity_pct": float(total_opportunity / total_spend * 100)
            if total_spend > 0 and total_opportunity
            else 0.0,
        },
        "consolidation": {
            "savings": _decimal_to_float(consolidation_savings_decimal),
            "opportunities": summary_metrics.get("consolidation_groups", []),
        },
        "total_opportunity": _decimal_to_float(total_opportunity),
        "dc_breakdown": [
            {
                "origin_dc": dc,
                "shipments": int(stats["shipments"]),
                "spend": _format_currency(stats["spend"]),
                "weight": _format_currency(stats["weight"]),
            }
            for dc, stats in dc_stats.items()
        ],
        "region_breakdown": [
            {
                "region": region,
                "shipments": int(stats["shipments"]),
                "spend": _format_currency(stats["spend"]),
                "weight": _format_currency(stats["weight"]),
            }
            for region, stats in region_stats.items()
        ],
        "top_lanes_by_spend": lane_spend,
        "top_lanes_by_savings": top_savings,
        "exceptions": {
            "total": len(exceptions),
            "zero_charge": zero_charge,
            "dim_heavy": dim_heavy,
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


