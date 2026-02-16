"""
Tariff ingestion service - parses XLSX rate sheets into database.
"""
import os
import re
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import Tariff, TariffLane, TariffBreak
from app.models.tariff import TariffType
from app.config.mapping_loader import get_tariff_mapping_for_file


def _clear_tariff_lanes_and_breaks(db: Session, tariff_id: Any) -> None:
    """
    Safely clear a tariff before re-ingest.

    Bulk deletes bypass SQLAlchemy ORM cascades, so we must delete child breaks
    before deleting parent lanes to avoid FK violations.
    """
    lane_ids = [
        row[0]
        for row in db.query(TariffLane.id).filter(TariffLane.tariff_id == tariff_id).all()
    ]
    if lane_ids:
        db.query(TariffBreak).filter(TariffBreak.tariff_lane_id.in_(lane_ids)).delete(
            synchronize_session=False
        )
    db.query(TariffLane).filter(TariffLane.tariff_id == tariff_id).delete(
        synchronize_session=False
    )
    db.flush()


def _normalize_column_key(value: Any) -> str:
    """Normalize column labels for resilient matching across file variants."""
    if value is None:
        return ""
    text = str(value).strip().upper()
    return re.sub(r"[^A-Z0-9]+", "", text)


def _read_excel_resilient(
    file_path: str,
    *,
    sheet_name: Optional[str] = None,
    expected_headers: Optional[List[Any]] = None,
    header_row: Optional[int] = None,
) -> pd.DataFrame:
    """
    Read Excel while handling shifted header rows (common in carrier templates).

    If `header_row` is not provided, scans the first few rows and chooses the row
    that best matches expected header tokens.
    """
    expected_tokens = {_normalize_column_key(h) for h in (expected_headers or []) if _normalize_column_key(h)}

    requested_sheet: Any = sheet_name if sheet_name not in (None, "") else 0

    def _read_df(*, header: Any, nrows: Optional[int] = None) -> pd.DataFrame:
        try:
            obj = pd.read_excel(file_path, sheet_name=requested_sheet, header=header, nrows=nrows)
        except Exception:
            # Fallback to first sheet if configured sheet is missing/misspelled.
            obj = pd.read_excel(file_path, sheet_name=0, header=header, nrows=nrows)

        # pandas returns a dict when sheet_name=None; coerce to first DataFrame.
        if isinstance(obj, dict):
            if not obj:
                raise ValueError("Uploaded Excel file has no readable sheets")
            return next(iter(obj.values()))
        return obj

    # Respect explicit config first.
    if header_row is not None:
        df = _read_df(header=header_row)
    else:
        candidate_header = 0
        best_score = -1
        preview = _read_df(header=None, nrows=12)

        for idx in range(len(preview.index)):
            row_values = preview.iloc[idx].tolist()
            row_tokens = {_normalize_column_key(v) for v in row_values if pd.notna(v)}
            score = len(expected_tokens.intersection(row_tokens))
            if score > best_score:
                best_score = score
                candidate_header = idx

        # Avoid accidental promotion when there is weak/no signal.
        if best_score < 2:
            candidate_header = 0

        df = _read_df(header=candidate_header)

    # Trim whitespace and normalize obvious oddities in header labels.
    df = df.rename(columns={col: str(col).strip() for col in df.columns})
    return df


def _resolve_column_name(
    df: pd.DataFrame,
    primary: Optional[Any],
    fallbacks: Optional[List[Any]] = None,
) -> Optional[Any]:
    """Resolve a desired column name to an actual DataFrame column label."""
    normalized_to_actual: Dict[str, Any] = {}
    for col in df.columns:
        norm = _normalize_column_key(col)
        if norm and norm not in normalized_to_actual:
            normalized_to_actual[norm] = col

    candidates: List[Any] = []
    if primary is not None:
        candidates.append(primary)
    candidates.extend(fallbacks or [])

    for candidate in candidates:
        norm = _normalize_column_key(candidate)
        if norm in normalized_to_actual:
            return normalized_to_actual[norm]
    return None


def _resolve_break_columns(
    df: pd.DataFrame,
    break_columns: Optional[List[Any]],
) -> List[Any]:
    """Resolve configured break columns against actual sheet column labels."""
    if not break_columns:
        return []

    resolved: List[Any] = []
    for break_def in break_columns:
        if isinstance(break_def, dict):
            raw_col = break_def.get("column")
            actual_col = _resolve_column_name(df, raw_col)
            if actual_col is None:
                continue
            normalized_def = dict(break_def)
            normalized_def["column"] = actual_col
            resolved.append(normalized_def)
        else:
            actual_col = _resolve_column_name(df, break_def)
            if actual_col is not None:
                resolved.append(actual_col)
    return resolved


def _infer_cwt_break_columns(
    df: pd.DataFrame,
    *,
    excluded_columns: Optional[List[Any]] = None,
) -> List[Any]:
    """Infer likely CWT break columns when templates vary or config is stale."""
    excluded_norm = {_normalize_column_key(c) for c in (excluded_columns or []) if c is not None}
    inferred: List[Any] = []
    for col in df.columns:
        norm = _normalize_column_key(col)
        if not norm or norm in excluded_norm:
            continue
        if norm in {"LTL", "L5CWT"}:
            inferred.append(col)
            continue
        if "CWT" in norm:
            inferred.append(col)
            continue
        if norm.isdigit():
            inferred.append(col)
    return inferred


def parse_apps_tariff(file_path: str, db: Session) -> Tariff:
    """
    Parse APPS FAK Skid Rates 2025.xlsx
    Format: DESTINATION, PROV, 1, 2, 3, ... (spot counts)
    """
    filename = os.path.basename(file_path)
    config = get_tariff_mapping_for_file(filename, "APPS") or {}
    sheet_name = config.get("sheet")
    expected_headers = [
        config.get("dest_city_column", "DESTINATION"),
        config.get("dest_province_column", "PROV"),
    ]
    expected_headers.extend(config.get("spot_columns") or [str(i) for i in range(1, 23)])
    df = _read_excel_resilient(
        file_path,
        sheet_name=sheet_name,
        expected_headers=expected_headers,
        header_row=config.get("header_row"),
    )
    
    # Create or get tariff
    tariff = db.query(Tariff).filter(
        Tariff.carrier_name == "APPS",
        Tariff.origin_dc == "SCARB"
    ).first()
    
    if not tariff:
        tariff = Tariff(
            carrier_name="APPS",
            origin_dc="SCARB",
            tariff_type=TariffType.SKID_SPOT
        )
        db.add(tariff)
        db.flush()
    else:
        # Rebuild tariff from latest upload to avoid stale lanes/breaks lingering.
        _clear_tariff_lanes_and_breaks(db, tariff.id)
    
    # Find numeric columns (spot counts)
    requested_spots = config.get("spot_columns")
    resolved_spots = _resolve_break_columns(df, requested_spots) if requested_spots else []
    spot_columns = resolved_spots or [col for col in df.columns if _normalize_column_key(col).isdigit()]
    city_col = _resolve_column_name(
        df,
        config.get("dest_city_column", "DESTINATION"),
        ["DESTINATION", "CITY", "DESTINATION CITY"],
    )
    province_col = _resolve_column_name(
        df,
        config.get("dest_province_column", "PROV"),
        ["PROV", "PROVINCE"],
    )
    if city_col is None or province_col is None:
        raise ValueError("Could not resolve required APPS destination columns in uploaded file")
    
    for _, row in df.iterrows():
        # Normalize city/province to uppercase for consistent matching
        dest_city = str(row.get(city_col, "")).strip().upper()
        dest_province = str(row.get(province_col, "")).strip().upper()
        
        if not dest_city or not dest_province:
            continue
        
        # Get or create lane
        lane = db.query(TariffLane).filter(
            TariffLane.tariff_id == tariff.id,
            TariffLane.dest_city == dest_city,
            TariffLane.dest_province == dest_province
        ).first()
        
        if not lane:
            lane = TariffLane(
                tariff_id=tariff.id,
                dest_city=dest_city,
                dest_province=dest_province
            )
            db.add(lane)
            db.flush()
        
        # Delete existing breaks for this lane
        db.query(TariffBreak).filter(TariffBreak.tariff_lane_id == lane.id).delete()
        
        # Create breaks for each spot count
        for spot_col in spot_columns:
            num_spots = int(spot_col)
            spot_charge = row.get(spot_col)
            
            if pd.notna(spot_charge) and spot_charge:
                break_row = TariffBreak(
                    tariff_lane_id=lane.id,
                    num_spots=num_spots,
                    spot_charge=Decimal(str(spot_charge))
                )
                db.add(break_row)
    
    db.commit()
    return tariff


def parse_cwt_tariff(
    file_path: str,
    db: Session,
    carrier_name: str,
    origin_dc: str,
    min_col: str = "MIN",
    break_columns: Optional[List[Any]] = None
) -> Tariff:
    """
    Parse CWT-based tariff (Rosedale, Maritime Ontario, Guilbault, CFF).
    
    Args:
        file_path: Path to XLSX file
        carrier_name: Name of carrier
        origin_dc: Origin DC code
        min_col: Column name for minimum charge
        break_columns: List of break column names (e.g., ["5CWT", "10CWT", ...])
                       If None, will auto-detect numeric/CWT columns
    """
    filename = os.path.basename(file_path)
    config_override = get_tariff_mapping_for_file(filename, carrier_name) or {}
    sheet_name = config_override.get("sheet")
    
    # Create or get tariff
    tariff = db.query(Tariff).filter(
        Tariff.carrier_name == carrier_name,
        Tariff.origin_dc == origin_dc
    ).first()
    
    if not tariff:
        tariff = Tariff(
            carrier_name=carrier_name,
            origin_dc=origin_dc,
            tariff_type=TariffType.CWT
        )
        db.add(tariff)
        db.flush()
    else:
        # Rebuild tariff from latest upload to avoid stale lanes/breaks lingering.
        _clear_tariff_lanes_and_breaks(db, tariff.id)
    
    # Auto-detect break columns if not provided
    if config_override.get("origin_dc"):
        origin_dc = config_override["origin_dc"]
    min_col = config_override.get("min_charge_column", min_col)
    dest_city_column = config_override.get("dest_city_column")
    dest_province_column = config_override.get("dest_province_column", "PROV")
    break_columns = config_override.get("breaks", break_columns)

    expected_headers = [
        dest_city_column or "DESTINATION",
        "DESTINATION CITY",
        "CITY",
        dest_province_column,
        min_col,
        "LTL",
        "500",
        "1000",
        "2000",
        "5000",
        "10000",
    ]
    if break_columns:
        for break_def in break_columns:
            expected_headers.append(break_def.get("column") if isinstance(break_def, dict) else break_def)

    df = _read_excel_resilient(
        file_path,
        sheet_name=sheet_name,
        expected_headers=expected_headers,
        header_row=config_override.get("header_row"),
    )

    if break_columns is None:
        inferred_breaks = []
        for col in df.columns:
            col_str = str(col).upper()
            if "CWT" in col_str or (col_str.isdigit() and int(col_str) >= 500):
                if col_str not in ["DESTINATION", "CITY", "PROV", "MIN", "LTL"]:
                    inferred_breaks.append(col)
        break_columns = inferred_breaks

    city_col = _resolve_column_name(
        df,
        dest_city_column or "DESTINATION",
        ["CITY", "DESTINATION", "DESTINATION CITY", "LOCATION"],
    )
    province_col = _resolve_column_name(
        df,
        dest_province_column,
        ["PROV", "PROVINCE", "STATE"],
    )
    min_charge_col = _resolve_column_name(
        df,
        min_col,
        ["MIN", "MINIMUM", "MIN CHARGE", "MINCHARGE", "LTL MIN", "LTLMIN"],
    )

    if province_col is None:
        raise ValueError("Could not resolve province column for CWT tariff sheet")

    resolved_break_columns = _resolve_break_columns(df, break_columns)
    if not resolved_break_columns:
        resolved_break_columns = _infer_cwt_break_columns(
            df,
            excluded_columns=[city_col, province_col, min_charge_col],
        )

    # Determine city column name
    for _, row in df.iterrows():
        # Normalize city/province to uppercase for consistent matching
        dest_city = str(row.get(city_col, "")).strip().upper() if city_col else ""
        dest_province = str(row.get(province_col, "")).strip().upper()
        
        if not dest_province:
            continue
        
        min_charge = row.get(min_charge_col) if min_charge_col else None
        if pd.isna(min_charge):
            min_charge = None
        
        # Get or create lane
        lane = db.query(TariffLane).filter(
            TariffLane.tariff_id == tariff.id,
            TariffLane.dest_city == dest_city,
            TariffLane.dest_province == dest_province
        ).first()
        
        if not lane:
            lane = TariffLane(
                tariff_id=tariff.id,
                dest_city=dest_city if dest_city else None,
                dest_province=dest_province,
                min_charge=Decimal(str(min_charge)) if min_charge else None
            )
            db.add(lane)
            db.flush()
        else:
            lane.min_charge = Decimal(str(min_charge)) if min_charge else None
        
        # Delete existing breaks
        db.query(TariffBreak).filter(TariffBreak.tariff_lane_id == lane.id).delete()
        
        # Parse breaks using TransX analyst's weight break mapping:
        # LTL/L5CWT = 0-499 lb
        # 500/5CWT = 500-999 lb  
        # 1000/10CWT = 1000-1999 lb
        # 2000/20CWT = 2000-4999 lb
        # 5000/50CWT = 5000-9999 lb
        # 10000/100CWT+ = 10000+ lb
        
        # Standard break ranges (from_weight, to_weight) based on column label
        STANDARD_BREAK_RANGES = {
            "LTL": (0, 500),
            "L5CWT": (0, 500),
            "500": (500, 1000),
            "5CWT": (500, 1000),
            "1000": (1000, 2000),
            "10CWT": (1000, 2000),
            "2000": (2000, 5000),
            "20CWT": (2000, 5000),
            "3000": (3000, 5000),  # Some tariffs have 3000 break
            "30CWT": (3000, 5000),
            "5000": (5000, 10000),
            "50CWT": (5000, 10000),
            "10000": (10000, None),  # Open-ended
            "100CWT": (10000, 20000),
            "200CWT": (20000, 30000),
            "300CWT": (30000, 50000),
            "500CWT": (50000, 100000),
            "1000CWT": (100000, None),  # Open-ended
        }
        
        for break_def in resolved_break_columns:
            if isinstance(break_def, dict):
                break_col = break_def.get("column")
                rate = row.get(break_col)
                from_weight = break_def.get("from")
                to_weight = break_def.get("to")
            else:
                break_col = break_def
                rate = row.get(break_col)
                from_weight = None
                to_weight = None
            
            if pd.isna(rate) or rate is None or rate == "":
                continue
            
            col_str = str(break_col).upper().strip()
            
            # If not explicitly defined, look up standard ranges
            if from_weight is None or to_weight is None:
                if col_str in STANDARD_BREAK_RANGES:
                    std_from, std_to = STANDARD_BREAK_RANGES[col_str]
                    from_weight = from_weight if from_weight is not None else std_from
                    to_weight = to_weight if to_weight is not None else std_to
                else:
                    # Try to parse numeric column names
                    if col_str.isdigit():
                        weight_val = int(col_str)
                        # Infer range based on common patterns
                        if weight_val < 500:
                            from_weight, to_weight = 0, 500
                        elif weight_val < 1000:
                            from_weight, to_weight = 500, 1000
                        elif weight_val < 2000:
                            from_weight, to_weight = 1000, 2000
                        elif weight_val < 5000:
                            from_weight, to_weight = 2000, 5000
                        elif weight_val < 10000:
                            from_weight, to_weight = 5000, 10000
                        else:
                            from_weight, to_weight = 10000, None
                    else:
                        continue  # Can't parse, skip
            
            from_decimal = Decimal(str(from_weight)) if from_weight is not None else Decimal("0")
            to_decimal = Decimal(str(to_weight)) if to_weight is not None else None
            
            break_row = TariffBreak(
                tariff_lane_id=lane.id,
                break_from_weight=from_decimal,
                break_to_weight=to_decimal,
                rate_per_cwt=Decimal(str(rate))
            )
            db.add(break_row)
    
    db.commit()
    return tariff


def ingest_rosedale_tariff(file_path: str, db: Session) -> Tariff:
    """Parse Rosedale Ex Toronto 2025 10lbs cwt.xlsx"""
    break_cols = ["L5CWT", "5CWT", "10CWT", "20CWT", "30CWT", "50CWT",
                  "100CWT", "200CWT", "300CWT", "500CWT", "1000CWT"]
    return parse_cwt_tariff(file_path, db, "Rosedale", "SCARB", "MIN", break_cols)


def ingest_maritime_ontario_tariff(file_path: str, db: Session) -> Tariff:
    """Parse MO ex TOR 10lbs cwt Maritimes 2025.xlsx"""
    break_cols = ["L5CWT", "5CWT", "10CWT", "20CWT", "30CWT", "50CWT",
                  "100CWT", "200CWT", "300CWT", "500CWT", "1000CWT"]
    return parse_cwt_tariff(file_path, db, "Maritime Ontario", "SCARB", "MIN", break_cols)


def ingest_guilbault_tariff(file_path: str, db: Session) -> Tariff:
    """Parse Groupe Guilbault exTOR 15cwt 2025.xlsx"""
    break_cols = ["LTL", "500", "1000", "2000", "5000", "10000"]
    return parse_cwt_tariff(file_path, db, "Groupe Guilbault", "SCARB", "MIN", break_cols)


def ingest_cff_tariff(file_path: str, db: Session) -> Tariff:
    """Parse CFF ex CGY 10lbs cwt to Western Canada Safety Express 2025.xlsx"""
    break_cols = ["LTL", "500", "1000", "2000", "5000", "10000"]
    return parse_cwt_tariff(file_path, db, "CFF", "CGY", "MIN", break_cols)
