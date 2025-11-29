"""
Vectorized rating and consolidation pipeline for audits.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import Shipment
from app.models.tariff import TariffType
from app.services.rating_engine import (
    _select_billable_weight,
    _to_decimal,
    rate_cwt_cached,
    rate_skid_spot_cached,
)
from app.services.tariff_cache import TariffCacheEntry, get_tariff_cache


def _normalize(value: Optional[str]) -> str:
    return value.strip().upper() if value else ""


@dataclass
class ShipmentRecord:
    shipment_id: str
    origin_dc: str
    dest_city: Optional[str]
    dest_province: Optional[str]
    dest_region: Optional[str]
    ship_date: Optional[date]
    pallets: Optional[Decimal]
    weight: Optional[Decimal]
    dim_weight: Optional[Decimal]
    actual_charge: Optional[Decimal]
    billable_weight: Optional[Decimal]

    @property
    def origin_key(self) -> str:
        return _normalize(self.origin_dc) or "UNKNOWN"

    @property
    def dest_city_key(self) -> str:
        return _normalize(self.dest_city)

    @property
    def dest_province_key(self) -> str:
        return _normalize(self.dest_province)


@dataclass
class ShipmentRatingUpdate:
    shipment_id: str
    expected_charge_per_carrier: Dict[str, float]
    best_carrier: Optional[str]
    best_charge: Optional[Decimal]
    savings_vs_actual: Decimal
    tariff_match_status: str  # "MATCHED", "NO_LANE", "NO_TARIFF"
    tariff_match_notes: Optional[str] = None


@dataclass
class ConsolidationOpportunity:
    origin_dc: str
    dest_city: str
    dest_province: str
    ship_date: date
    shipment_count: int
    actual_sum: Decimal
    individual_best_sum: Decimal
    consolidated_charge: Decimal
    incremental_savings: Decimal
    carrier: Optional[str]


@dataclass
class VectorizedRerateResult:
    shipment_updates: List[ShipmentRatingUpdate]
    carrier_savings_total: Decimal
    carrier_best_total: Decimal
    rerated_count: int
    consolidation_savings_total: Decimal
    consolidation_groups: List[ConsolidationOpportunity]
    consolidation_group_count: int


def _records_to_dataframe(records: List[ShipmentRecord]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=[
                "shipment_id",
                "origin_dc",
                "dest_city",
                "dest_province",
                "dest_region",
                "ship_date",
                "pallets",
                "weight",
                "billable_weight",
                "actual_charge",
            ]
        )

    data = []
    for rec in records:
        data.append(
            {
                "shipment_id": rec.shipment_id,
                "origin_dc": rec.origin_key,
                "dest_city": rec.dest_city or "",
                "dest_province": rec.dest_province or "",
                "dest_region": rec.dest_region or "",
                "ship_date": rec.ship_date,
                "pallets": float(rec.pallets) if rec.pallets is not None else np.nan,
                "weight": float(rec.weight) if rec.weight is not None else np.nan,
                "billable_weight": float(rec.billable_weight)
                if rec.billable_weight is not None
                else np.nan,
                "actual_charge": float(rec.actual_charge)
                if rec.actual_charge is not None
                else np.nan,
            }
        )

    return pd.DataFrame(data)


def _load_records(db: Session, audit_run_id: UUID) -> List[ShipmentRecord]:
    shipments = db.query(Shipment).filter(Shipment.audit_run_id == audit_run_id).all()
    records: List[ShipmentRecord] = []
    for shipment in shipments:
        billable = _select_billable_weight(shipment.weight, shipment.dim_weight)
        records.append(
            ShipmentRecord(
                shipment_id=str(shipment.id),
                origin_dc=shipment.origin_dc or "UNKNOWN",
                dest_city=shipment.dest_city,
                dest_province=shipment.dest_province,
                dest_region=shipment.dest_region,
                ship_date=shipment.ship_date,
                pallets=_to_decimal(shipment.pallets),
                weight=_to_decimal(shipment.weight),
                dim_weight=_to_decimal(shipment.dim_weight),
                actual_charge=_to_decimal(shipment.actual_charge),
                billable_weight=billable,
            )
        )
    return records


def _filter_tariff_entries(
    db: Session, tariff_ids: Optional[List[UUID]]
) -> List[TariffCacheEntry]:
    cache = get_tariff_cache(db)
    if tariff_ids:
        allowed = {str(tid) for tid in tariff_ids}
        return [entry for entry in cache.entries if entry.id in allowed]
    return cache.entries


def _compute_carrier_columns(
    df: pd.DataFrame, records: List[ShipmentRecord], entries: List[TariffCacheEntry]
) -> Tuple[List[str], Dict[str, str]]:
    carrier_columns: List[str] = []
    column_to_carrier: Dict[str, str] = {}

    for entry in entries:
        column_name = f"carrier_{entry.id}"
        charges: List[float] = []
        lane_lookup: Dict[Tuple[str, str], Optional[object]] = {}

        for rec in records:
            if rec.origin_key != _normalize(entry.origin_dc):
                charges.append(np.nan)
                continue

            lane_key = (rec.dest_city_key, rec.dest_province_key)
            if lane_key not in lane_lookup:
                lane_lookup[lane_key] = entry.find_lane(rec.dest_city, rec.dest_province)
            lane_cache = lane_lookup[lane_key]

            if not lane_cache:
                charges.append(np.nan)
                continue

            if entry.tariff_type == TariffType.CWT:
                charge = rate_cwt_cached(rec.billable_weight, lane_cache)
            else:
                charge = rate_skid_spot_cached(rec.pallets, rec.weight, lane_cache)

            charges.append(float(charge) if charge is not None else np.nan)

        df[column_name] = charges
        carrier_columns.append(column_name)
        column_to_carrier[column_name] = entry.carrier_name

    return carrier_columns, column_to_carrier


def _build_shipment_updates(
    df: pd.DataFrame,
    records: List[ShipmentRecord],
    carrier_columns: List[str],
    column_to_carrier: Dict[str, str],
) -> Tuple[List[ShipmentRatingUpdate], Decimal, Decimal, int]:
    updates: List[ShipmentRatingUpdate] = []
    carrier_savings_total = Decimal("0")
    best_charge_total = Decimal("0")
    rerated_count = 0

    if not carrier_columns:
        return updates, carrier_savings_total, best_charge_total, rerated_count

    for idx, rec in enumerate(records):
        row = df.iloc[idx]
        best_charge_float: Optional[float] = None
        best_carrier_col: Optional[str] = None

        for col in carrier_columns:
            value = row[col]
            if np.isnan(value):
                continue
            if best_charge_float is None or value < best_charge_float:
                best_charge_float = value
                best_carrier_col = col

        expected_charge_per_carrier: Dict[str, float] = {}
        for col, carrier_name in column_to_carrier.items():
            value = row[col]
            if np.isnan(value):
                continue
            expected_charge_per_carrier[carrier_name] = round(float(value), 2)

        best_charge_decimal: Optional[Decimal] = None
        savings = Decimal("0")
        if best_charge_float is not None:
            best_charge_decimal = Decimal(str(round(best_charge_float, 4)))
            actual = rec.actual_charge or Decimal("0")
            if actual > 0 and best_charge_decimal is not None:
                diff = actual - best_charge_decimal
                if diff > 0:
                    savings = diff
                    carrier_savings_total += diff
            best_charge_total += best_charge_decimal
            rerated_count += 1

        # Determine tariff match status
        if best_charge_float is not None:
            tariff_match_status = "MATCHED"
            tariff_match_notes = None
        elif not carrier_columns:
            tariff_match_status = "NO_TARIFF"
            tariff_match_notes = "No tariffs loaded for rating"
        else:
            tariff_match_status = "NO_LANE"
            tariff_match_notes = f"No lane found for {rec.dest_city}/{rec.dest_province}"

        updates.append(
            ShipmentRatingUpdate(
                shipment_id=rec.shipment_id,
                expected_charge_per_carrier=expected_charge_per_carrier,
                best_carrier=column_to_carrier.get(best_carrier_col) if best_carrier_col else None,
                best_charge=best_charge_decimal,
                savings_vs_actual=savings,
                tariff_match_status=tariff_match_status,
                tariff_match_notes=tariff_match_notes,
            )
        )

    return updates, carrier_savings_total, best_charge_total, rerated_count


def _best_consolidated_charge(
    origin_key: str,
    dest_city: Optional[str],
    dest_province: Optional[str],
    billable_weight: Optional[Decimal],
    pallets: Optional[Decimal],
    weight: Optional[Decimal],
    entries_by_origin: Dict[str, List[TariffCacheEntry]],
) -> Tuple[Optional[Decimal], Optional[str]]:
    entries = entries_by_origin.get(origin_key, [])
    best_charge: Optional[Decimal] = None
    best_carrier: Optional[str] = None

    for entry in entries:
        lane_cache = entry.find_lane(dest_city, dest_province)
        if not lane_cache:
            continue
        if entry.tariff_type == TariffType.CWT:
            charge = rate_cwt_cached(billable_weight, lane_cache)
        else:
            charge = rate_skid_spot_cached(pallets, weight, lane_cache)

        if charge is None:
            continue
        if best_charge is None or charge < best_charge:
            best_charge = charge
            best_carrier = entry.carrier_name

    return best_charge, best_carrier


def _get_week_key(ship_date: date) -> Tuple[int, int]:
    """Get (year, week_number) for a date."""
    iso_cal = ship_date.isocalendar()
    return (iso_cal[0], iso_cal[1])


def _is_mon_thu(ship_date: date) -> bool:
    """Check if date is Monday through Thursday (weekday 0-3)."""
    return ship_date.weekday() <= 3  # Mon=0, Tue=1, Wed=2, Thu=3


def _compute_consolidation_opportunities(
    records: List[ShipmentRecord],
    updates: List[ShipmentRatingUpdate],
    entries: List[TariffCacheEntry],
    use_weekly_consolidation: bool = True,
) -> Tuple[Decimal, List[ConsolidationOpportunity], int]:
    """
    Compute consolidation opportunities.
    
    Two modes:
    1. Same-day consolidation (original): group by exact ship_date
    2. Weekly Mon-Thu consolidation (TransX model): group Mon-Thu shipments 
       into consolidated Thursday departures
    
    The weekly mode matches what the TransX analyst did in their Excel model.
    """
    by_key: Dict[Tuple[str, str, str, any], List[int]] = defaultdict(list)

    for idx, rec in enumerate(records):
        if not rec.ship_date or not rec.dest_province_key:
            continue
        
        if use_weekly_consolidation:
            # Mon-Thu consolidation: group by week, only include Mon-Thu shipments
            if not _is_mon_thu(rec.ship_date):
                continue  # Skip Fri-Sun shipments for weekly consolidation
            week_key = _get_week_key(rec.ship_date)
            key = (rec.origin_key, rec.dest_city_key, rec.dest_province_key, week_key)
        else:
            # Same-day consolidation (original behavior)
            key = (rec.origin_key, rec.dest_city_key, rec.dest_province_key, rec.ship_date)
        
        by_key[key].append(idx)

    entries_by_origin: Dict[str, List[TariffCacheEntry]] = defaultdict(list)
    for entry in entries:
        entries_by_origin[_normalize(entry.origin_dc)].append(entry)

    consolidation_savings_total = Decimal("0")
    opportunities: List[ConsolidationOpportunity] = []
    group_count = 0

    for key, indices in by_key.items():
        if len(indices) < 2:
            continue
        origin_key, dest_city_key, dest_province_key, ship_date = key
        actual_sum = Decimal("0")
        individual_best_sum = Decimal("0")
        pallets_total = Decimal("0")
        weight_total = Decimal("0")
        dim_total = Decimal("0")
        valid_records = 0

        for idx in indices:
            rec = records[idx]
            update = updates[idx]
            actual_sum += rec.actual_charge or Decimal("0")
            if update.best_charge is not None:
                individual_best_sum += update.best_charge
            else:
                individual_best_sum += rec.actual_charge or Decimal("0")
            pallets_total += rec.pallets or Decimal("0")
            weight_total += rec.weight or Decimal("0")
            dim_total += rec.dim_weight or Decimal("0")
            valid_records += 1

        if valid_records < 2:
            continue

        billable = max(weight_total, dim_total) if any([weight_total, dim_total]) else None
        consolidated_charge, carrier = _best_consolidated_charge(
            origin_key,
            records[indices[0]].dest_city,
            records[indices[0]].dest_province,
            billable,
            pallets_total,
            weight_total,
            entries_by_origin,
        )

        if consolidated_charge is None:
            continue

        incremental = individual_best_sum - consolidated_charge
        if incremental <= 0:
            continue

        consolidation_savings_total += incremental
        group_count += 1
        
        # For weekly consolidation, use the Thursday of that week as the "ship_date"
        # For same-day, use the actual ship_date
        if use_weekly_consolidation and isinstance(key[3], tuple):
            # key[3] is (year, week_number)
            # Find the Thursday of that week
            first_rec_date = records[indices[0]].ship_date
            days_until_thursday = (3 - first_rec_date.weekday()) % 7
            consolidated_ship_date = first_rec_date + timedelta(days=days_until_thursday)
        else:
            consolidated_ship_date = key[3] if isinstance(key[3], date) else records[indices[0]].ship_date
        
        opportunities.append(
            ConsolidationOpportunity(
                origin_dc=records[indices[0]].origin_dc,
                dest_city=records[indices[0]].dest_city or "",
                dest_province=records[indices[0]].dest_province or "",
                ship_date=consolidated_ship_date,
                shipment_count=len(indices),
                actual_sum=actual_sum,
                individual_best_sum=individual_best_sum,
                consolidated_charge=consolidated_charge,
                incremental_savings=incremental,
                carrier=carrier,
            )
        )

    opportunities.sort(key=lambda o: o.incremental_savings, reverse=True)
    return consolidation_savings_total, opportunities[:15], group_count


def run_vectorized_rerate(
    db: Session, audit_run_id: UUID, tariff_ids: Optional[List[UUID]] = None
) -> VectorizedRerateResult:
    records = _load_records(db, audit_run_id)
    if not records:
        return VectorizedRerateResult(
            shipment_updates=[],
            carrier_savings_total=Decimal("0"),
            carrier_best_total=Decimal("0"),
            rerated_count=0,
            consolidation_savings_total=Decimal("0"),
            consolidation_groups=[],
            consolidation_group_count=0,
        )

    entries = _filter_tariff_entries(db, tariff_ids)
    if not entries:
        raise ValueError("No tariffs available for re-rating")

    df = _records_to_dataframe(records)
    carrier_columns, column_to_carrier = _compute_carrier_columns(df, records, entries)
    shipment_updates, carrier_savings_total, best_total, rerated_count = _build_shipment_updates(
        df, records, carrier_columns, column_to_carrier
    )
    consolidation_total, consolidation_groups, consolidation_group_count = _compute_consolidation_opportunities(
        records, shipment_updates, entries
    )

    return VectorizedRerateResult(
        shipment_updates=shipment_updates,
        carrier_savings_total=carrier_savings_total,
        carrier_best_total=best_total,
        rerated_count=rerated_count,
        consolidation_savings_total=consolidation_total,
        consolidation_groups=consolidation_groups,
        consolidation_group_count=consolidation_group_count,
    )


