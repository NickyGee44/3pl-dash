"""
File parsing and column mapping services.
"""
import pandas as pd
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from app.config.mapping_loader import (
    get_region_from_config,
    get_shipment_mapping_for_file,
)


# Known column name patterns for mapping (case-insensitive matching)
# Extended to cover all known variants from GI shipment files
COLUMN_PATTERNS = {
    # Scale/actual weight
    "weight": [
        "wgt", "weight", "invwgt", "actual_weight", "ship_weight",
        "actwgt", "actual weight", "scale_weight", "scalewgt",
    ],
    # Billed/rated weight (what carrier charges on)
    "billed_weight": [
        "prbwgt", "billwgt", "billed_weight", "chargeable_weight",
        "billed weight", "rated_weight", "ratedwgt",
    ],
    # Pallets / pieces
    "pallets": [
        "invpcs", "pcs", "pieces", "pallets", "pallet", "qty_pallets",
        "pallet_count", "skids", "skd", "handling_units",
    ],
    # Charge / amount
    "charge": [
        "trfamt", "price", "amount", "charge", "cost", "freight_charge",
        "total_charge", "linehaul", "total charge", "freight",
    ],
    # Shipment reference / PRO
    "shipment_ref": [
        "pronumber", "pro number", "pro_number", "pro no", "prono",
        "ref", "shipment", "pro", "tracking", "shipment_id",
        "bol", "bolnumber", "bol number",
    ],
    # Origin fields (shipper)
    "origin_city": [
        "shpcity", "shcity", "s.city", "shipper city", "shipper_city",
        "origin", "origin_city", "from_city", "ship_from_city", "scity",
    ],
    "origin_province": [
        "shpst", "shstate", "shprv", "shp prov", "shp_prov", "sprov",
        "origin_prov", "from_prov", "ship_from_prov", "origin_province",
        "shipper_province", "shipper province",
    ],
    "origin_postal": [
        "shppc", "shpcode", "shp postal", "shp_zip", "szip", "spostal",
        "origin_postal", "from_postal", "ship_from_postal", "origin_zip",
        "shpostal", "sh postal", "shipper postal",
    ],
    "origin_name": [
        "shname", "shipper name", "shpname", "shipper_name", "sname",
    ],
    "origin_address": [
        "shadd1", "shp add1", "shipper address", "shipper_address", "saddr",
    ],
    # Destination fields (consignee)
    "dest_city": [
        "cnpcity", "cncity", "ccity", "dcity", "destcity", "ccityname",
        "dest", "destination", "dest_city", "to_city", "ship_to_city",
        "consignee_city", "consignee city",
    ],
    "dest_province": [
        "cnpst", "cprov", "cstate", "destprov", "c_prov", "dprov",
        "dest_prov", "to_prov", "ship_to_prov", "dest_province", "province",
        "consignee_province", "consignee province",
    ],
    "dest_postal": [
        "cnppc", "cpostal", "cpc", "czip", "destpostal", "dzip",
        "dest_postal", "to_postal", "ship_to_postal", "dest_zip", "postal",
    ],
    "dest_name": [
        "cnname", "consignee name", "cname", "consignee_name", "dname",
    ],
    "dest_address": [
        "cnadd1", "cadd1", "dest address", "consignee_address", "daddr",
    ],
    # Dates
    "ship_date": [
        "ship_date", "date", "shipment_date", "ship_dt", "shipdate",
    ],
    # Carrier
    "carrier": [
        "carrier", "carrier_name", "transport", "trucking", "scac",
    ],
    # Dimensional weight
    "dim_weight": [
        "dim_weight", "dimensional_weight", "dim_wgt", "cube_weight",
        "dimwgt", "dim weight",
    ],
    # Customer reference
    "customer_ref": [
        "customer ref", "custref", "customerref", "ref", "cust_ref",
        "customer_ref", "customer reference",
    ],
    # Transit days
    "std_transit_days": [
        "standd", "std_days", "standard_days", "std transit",
    ],
    "actual_transit_days": [
        "actdys", "act_days", "actualdays", "actual_days", "actual transit",
    ],
    # POD
    "pod_signed": [
        "signed", "pod signed", "pod_signed", "podsigned",
    ],
    "pod_signature": [
        "signature", "pod name", "pod_signature", "podsignature",
    ],
}


def infer_file_type(filename: str) -> str:
    """Infer file type from extension."""
    ext = Path(filename).suffix.lower()
    if ext == ".xlsx" or ext == ".xls":
        return "xlsx"
    elif ext == ".csv":
        return "csv"
    else:
        return ext.lstrip(".")


def read_file(file_path: str, file_type: str) -> pd.DataFrame:
    """Read file into pandas DataFrame."""
    if file_type == "xlsx":
        # Read all non-empty sheets and combine
        excel_file = pd.ExcelFile(file_path)
        dataframes = []
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            if not df.empty:
                df["__sheet_name"] = sheet_name  # keep track of origin sheet
                dataframes.append(df)
        if dataframes:
            return pd.concat(dataframes, ignore_index=True)
        raise ValueError("No data found in Excel file")
    elif file_type == "csv":
        # Try different encodings
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV file")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def infer_column_mapping(df: pd.DataFrame, filename: Optional[str] = None, sheet_name: Optional[str] = None) -> Dict[str, str]:
    """
    Infer column mappings from DataFrame column names.
    Returns dict mapping source_column -> target_field.
    
    Priority:
    1. Config file explicit mapping (if filename matches)
    2. Pattern-based inference from COLUMN_PATTERNS
    """
    mappings = {}
    
    # First, try config-based mapping
    if filename:
        config_mapping = get_shipment_mapping_for_file(filename, sheet_name)
        if config_mapping and config_mapping.get("columns"):
            mappings = dict(config_mapping["columns"])
    
    # Then, augment with pattern-based inference for any unmapped columns
    df_columns = [str(col).lower().strip() for col in df.columns]
    already_mapped_targets = set(mappings.values())
    
    for target_field, patterns in COLUMN_PATTERNS.items():
        if target_field in already_mapped_targets:
            continue  # Already have a mapping from config
        
        best_match = None
        best_score = 0
        
        for col_idx, col_name in enumerate(df_columns):
            original_col = df.columns[col_idx]
            if original_col in mappings:
                continue  # This source column is already mapped
            
            for pattern in patterns:
                if pattern == col_name:
                    # Exact match
                    score = 1.0
                elif pattern in col_name:
                    # Contains match
                    score = 0.5
                else:
                    continue
                
                if score > best_score:
                    best_score = score
                    best_match = original_col
        
        if best_match:
            mappings[best_match] = target_field
    
    return mappings


def infer_source_type(filename: str) -> Optional[str]:
    """Infer source type (e.g., DC name) from filename."""
    filename_upper = filename.upper()
    
    # Common patterns
    if "CLG" in filename_upper or "CALGARY" in filename_upper or "CGY" in filename_upper:
        return "Calgary DC export"
    elif "SCARB" in filename_upper or "SC-" in filename_upper:
        return "Scarborough DC export"
    elif "TORONTO" in filename_upper or "TOR" in filename_upper:
        return "Toronto DC export"
    elif "MONTREAL" in filename_upper or "MTL" in filename_upper:
        return "Montreal DC export"
    
    return None


def normalize_province_to_region(province: str) -> Optional[str]:
    """Map province to region."""
    return get_region_from_config(province)


