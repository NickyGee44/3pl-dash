"""
Data normalization service - converts raw DataFrame rows to Shipment model.
"""
import pandas as pd
from typing import Dict, Optional, Any, List
from datetime import datetime
from decimal import Decimal, InvalidOperation
from app.services.file_parser import normalize_province_to_region


def normalize_row(
    row: pd.Series,
    mappings: Dict[str, str],
    source_file_id: str,
    audit_run_id: str,
    raw_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Normalize a single row from source file to shipment data.
    
    Args:
        row: pandas Series representing one row
        mappings: dict mapping source_column -> target_field
        source_file_id: UUID of source file
        audit_run_id: UUID of audit run
        raw_data: optional dict of all original row data
    
    Returns:
        dict with normalized shipment fields
    """
    def sanitize_raw(value):
        if isinstance(value, dict):
            return {k: sanitize_raw(v) for k, v in value.items()}
        if isinstance(value, list):
            return [sanitize_raw(v) for v in value]
        try:
            if pd.isna(value):
                return None
        except TypeError:
            # pd.isna raises TypeError for some objects (e.g., dicts) – just return value
            pass
        return value
    
    raw_dict = raw_data or row.to_dict()
    result = {
        "source_file_id": source_file_id,
        "audit_run_id": audit_run_id,
        "raw_data": sanitize_raw(raw_dict),
    }
    
    # Helper to safely get value
    def get_value(field_name: str, default=None, aliases: Optional[List[str]] = None):
        search_fields = [field_name] + (aliases or [])
        source_col = None
        for candidate in search_fields:
            for src_col, tgt_field in mappings.items():
                if tgt_field == candidate:
                    source_col = src_col
                    break
            if source_col:
                break
        
        if source_col and source_col in row.index:
            val = row[source_col]
            # Handle pandas NaN
            if pd.isna(val):
                return default
            return val
        return default
    
    def norm_text(val):
        """Normalize text: strip whitespace, uppercase for matching."""
        if val is None:
            return None
        s = str(val).strip()
        return s if s else None
    
    def norm_text_upper(val):
        """Normalize text and uppercase for city/province matching."""
        if val is None:
            return None
        s = str(val).strip().upper()
        return s if s else None
    
    # Normalize each field
    result["shipment_ref"] = norm_text(get_value("shipment_ref", ""))
    
    # Origin - uppercase for consistency
    result["origin_city"] = norm_text_upper(get_value("origin_city", ""))
    result["origin_province"] = norm_text_upper(get_value("origin_province", ""))
    result["origin_postal"] = norm_text_upper(get_value("origin_postal", ""))
    
    # Destination - uppercase for tariff lane matching
    result["dest_city"] = norm_text_upper(get_value("dest_city", ""))
    result["dest_province"] = norm_text_upper(get_value("dest_province", ""))
    result["dest_postal"] = norm_text_upper(get_value("dest_postal", ""))
    result["dest_region"] = normalize_province_to_region(result["dest_province"])
    
    # Dates
    ship_date = get_value("ship_date")
    if ship_date:
        if isinstance(ship_date, str):
            try:
                result["ship_date"] = pd.to_datetime(ship_date).date()
            except:
                result["ship_date"] = None
        elif isinstance(ship_date, (datetime, pd.Timestamp)):
            result["ship_date"] = ship_date.date() if hasattr(ship_date, 'date') else None
        else:
            result["ship_date"] = None
    else:
        result["ship_date"] = None
    
    # Numeric fields
    def safe_decimal(val, default=None):
        """
        Safely convert a value to Decimal.
        
        Handles common freight file formats like:
        - "1,234.56"
        - "$1,234.56"
        - "(1,234.56)" for negatives
        """
        if val is None or pd.isna(val):
            return default
        try:
            if isinstance(val, str):
                s = val.strip()
                if not s:
                    return default
                # Handle negatives in parentheses: (123.45) -> -123.45
                negative = False
                if s.startswith("(") and s.endswith(")"):
                    negative = True
                    s = s[1:-1]
                # Remove currency symbols and thousands separators
                for ch in ["$", ","]:
                    s = s.replace(ch, "")
                s = s.strip()
                if negative:
                    s = "-" + s
                val = s
            return Decimal(str(val))
        except (InvalidOperation, ValueError, TypeError):
            return default
    
    result["pallets"] = safe_decimal(get_value("pallets", aliases=["pieces"]))
    
    # Weight fields:
    # - weight = INVWGT (scale/actual weight)
    # - dim_weight = PRBWGT (billed weight - what carrier charges on)
    # The rating engine uses max(weight, dim_weight) for CWT calculations
    result["weight"] = safe_decimal(get_value("weight", aliases=["scale_weight"]))
    
    # PRBWGT (billed weight) maps to dim_weight in our model
    # This is the weight the carrier actually used for rating
    # Try billed_weight first (from PRBWGT), then fall back to dim_weight
    billed = get_value("billed_weight")
    if billed is None:
        billed = get_value("dim_weight")
    result["dim_weight"] = safe_decimal(billed)
    
    result["actual_charge"] = safe_decimal(get_value("charge", aliases=["actual_charge"]))
    
    # Carrier
    result["carrier"] = str(get_value("carrier", "")).strip() or None
    
    # Origin DC - derive from shipper city (SHCITY)
    # Common values: TOR, SCARB, BRAMP, NIAGARA, RICHMOND, CALGARY, etc.
    origin_city = result.get("origin_city")
    if origin_city:
        # Map common city names/abbreviations to DC codes
        origin_dc = _infer_origin_dc(origin_city)
        result["origin_dc"] = origin_dc
    else:
        result["origin_dc"] = None
    
    return result


# Mapping of shipper cities to origin DC codes
# This maps the actual city names found in SHCITY to standardized DC codes
ORIGIN_DC_MAPPINGS = {
    # Toronto area
    "TOR": "TOR",
    "TORONTO": "TOR",
    "SCARB": "SCARB",
    "SCARBOROUGH": "SCARB",
    "BRAMP": "BRAMP",
    "BRAMPTON": "BRAMP",
    "MISS": "MISS",
    "MISSISSAUGA": "MISS",
    "NIAGARA": "NIAGARA",
    "NIAGARA FALLS": "NIAGARA",
    # Calgary area
    "CGY": "CGY",
    "CALGARY": "CGY",
    "CLG": "CGY",
    # Vancouver area
    "RICHMOND": "RICHMOND",
    "VAN": "VAN",
    "VANCOUVER": "VAN",
    # Montreal area
    "MTL": "MTL",
    "MONTREAL": "MTL",
    # Edmonton
    "EDM": "EDM",
    "EDMONTON": "EDM",
}


def _infer_origin_dc(origin_city: str) -> str:
    """
    Infer the origin DC code from the shipper city.
    
    Returns the standardized DC code if found in mappings,
    otherwise returns the city name as-is (uppercased).
    """
    if not origin_city:
        return None
    
    city_upper = origin_city.upper().strip()
    
    # Check direct mapping
    if city_upper in ORIGIN_DC_MAPPINGS:
        return ORIGIN_DC_MAPPINGS[city_upper]
    
    # Check if city contains any of the mapped names
    for key, dc_code in ORIGIN_DC_MAPPINGS.items():
        if key in city_upper:
            return dc_code
    
    # Return the city as-is if no mapping found
    # This preserves the actual city name for lane statistics
    return city_upper


