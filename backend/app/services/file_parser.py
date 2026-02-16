"""
File parsing and column mapping services.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional
from pathlib import Path

import pandas as pd
from openai import OpenAI

from app.config.mapping_loader import (
    get_region_from_config,
    get_shipment_mapping_for_file,
)

logger = logging.getLogger(__name__)


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
        "sh_city", "shippercity", "shipfromcity", "shipcity",
    ],
    "origin_province": [
        "shpst", "shstate", "shprv", "shp prov", "shp_prov", "sprov",
        "origin_prov", "from_prov", "ship_from_prov", "origin_province",
        "shipper_province", "shipper province", "sh_prov", "shprov",
    ],
    "origin_postal": [
        "shppc", "shpcode", "shp postal", "shp_zip", "szip", "spostal",
        "origin_postal", "from_postal", "ship_from_postal", "origin_zip",
        "shpostal", "sh postal", "shipper postal", "sh_postal", "shzip",
    ],
    "origin_name": [
        "shname", "shipper name", "shpname", "shipper_name", "sname",
        "shipper", "sender", "shipperid", "shipper_no",
    ],
    "origin_address": [
        "shadd1", "shp add1", "shipper address", "shipper_address", "saddr",
        "shaddr", "sh_address", "shstrno", "sh_street",
    ],
    # Destination fields (consignee)
    "dest_city": [
        "cnpcity", "cncity", "ccity", "dcity", "destcity", "ccityname",
        "dest", "destination", "dest_city", "to_city", "ship_to_city",
        "consignee_city", "consignee city", "rccity", "rc_city",
        "receiver_city", "receivercity", "rcvcity",
    ],
    "dest_province": [
        "cnpst", "cprov", "cstate", "destprov", "c_prov", "dprov",
        "dest_prov", "to_prov", "ship_to_prov", "dest_province", "province",
        "consignee_province", "consignee province", "rcprov", "rc_prov",
        "rcstate", "rc_st", "receiver_province",
    ],
    "dest_postal": [
        "cnppc", "cpostal", "cpc", "czip", "destpostal", "dzip",
        "dest_postal", "to_postal", "ship_to_postal", "dest_zip", "postal",
        "rcpostal", "rc_postal", "rczip", "receiver_postal",
    ],
    "dest_country": [
        "dest_country", "destination country", "country", "consignee_country",
        "receiver_country", "rccountry", "rc_country", "cncountry",
    ],
    "dest_name": [
        "cnname", "consignee name", "cname", "consignee_name", "dname",
        "rcname", "receiver_name", "receivername", "receiver",
    ],
    "dest_address": [
        "cnadd1", "cadd1", "dest address", "consignee_address", "daddr",
        "rcadd1", "rc_address", "rcaddr", "rcstrno", "receiver_address",
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

TARGET_FIELD_DESCRIPTIONS: Dict[str, str] = {
    "shipment_ref": "Shipment reference identifier (PRO/BOL/tracking).",
    "origin_dc": "Origin distribution center code.",
    "origin_city": "Shipper origin city.",
    "origin_province": "Shipper origin province/state.",
    "origin_postal": "Shipper origin postal/zip code.",
    "origin_name": "Shipper company/location name.",
    "origin_address": "Shipper address line.",
    "dest_city": "Consignee destination city.",
    "dest_province": "Consignee destination province/state.",
    "dest_postal": "Consignee destination postal/zip code.",
    "dest_country": "Consignee destination country.",
    "dest_name": "Consignee name.",
    "dest_address": "Consignee address line.",
    "dest_region": "Destination region grouping (derived from province).",
    "ship_date": "Shipment date.",
    "pallets": "Pallet/skid/piece count.",
    "weight": "Actual/scale shipment weight.",
    "billed_weight": "Carrier-rated or billed weight.",
    "dim_weight": "Dimensional/cube weight.",
    "charge": "Actual freight charge amount.",
    "carrier": "Carrier name/scac.",
    "customer_ref": "Customer reference identifier.",
    "std_transit_days": "Standard transit days.",
    "actual_transit_days": "Actual transit days.",
    "pod_signed": "Proof of delivery signature present flag.",
    "pod_signature": "Proof of delivery signer/signature text.",
}

PATTERN_MATCH_MIN_CONFIDENCE = 0.55
AI_MATCH_MIN_CONFIDENCE = 0.55
AI_DEFAULT_MODEL = os.getenv("COLUMN_MAPPING_MODEL", "gpt-4o-mini")
_OPENAI_CLIENT: Any = None


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _token_set(value: Any) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", str(value).lower()) if token}


def _is_meta_column(column_name: Any) -> bool:
    return str(column_name).startswith("__")


def _resolve_source_column(df_columns: List[Any], configured_name: Any) -> Optional[Any]:
    """Resolve configured column names against real columns case/format-insensitively."""
    target_norm = _normalize_token(configured_name)
    if not target_norm:
        return None
    for col in df_columns:
        if _normalize_token(col) == target_norm:
            return col
    return None


def _score_pattern_match(column_name: str, pattern: str) -> float:
    col_norm = _normalize_token(column_name)
    pat_norm = _normalize_token(pattern)
    if not col_norm or not pat_norm:
        return 0.0
    if col_norm == pat_norm:
        return 1.0
    if col_norm.startswith(pat_norm) or col_norm.endswith(pat_norm):
        return 0.92
    if pat_norm in col_norm:
        return 0.82
    col_tokens = _token_set(column_name)
    pat_tokens = _token_set(pattern)
    if not col_tokens or not pat_tokens:
        return 0.0
    overlap = len(col_tokens.intersection(pat_tokens))
    if overlap == 0:
        return 0.0
    return min(0.8, overlap / max(len(col_tokens), len(pat_tokens)))


def _build_column_samples(df: pd.DataFrame, max_values: int = 3) -> Dict[str, List[str]]:
    samples: Dict[str, List[str]] = {}
    for col in df.columns:
        if _is_meta_column(col):
            continue
        values: List[str] = []
        series = df[col]
        for val in series:
            if pd.isna(val):
                continue
            text = str(val).strip()
            if not text:
                continue
            values.append(text[:80])
            if len(values) >= max_values:
                break
        if values:
            samples[str(col)] = values
    return samples


def _infer_role_based_target(column_name: str) -> Optional[Dict[str, Any]]:
    """
    Infer mappings from common carrier abbreviations:
    - RC_* => receiver/consignee (destination)
    - SH_* => shipper/origin
    """
    norm = _normalize_token(column_name)
    if not norm:
        return None
    tokens = _token_set(column_name)

    is_receiver = (
        norm.startswith("rc")
        or "receiver" in tokens
        or "consignee" in tokens
        or norm.startswith("cn")
    )
    is_shipper = (
        norm.startswith("sh")
        or "shipper" in tokens
        or "sender" in tokens
        or "origin" in tokens
    )
    if not is_receiver and not is_shipper:
        return None

    target_prefix = "dest" if is_receiver else "origin"

    def has(*candidates: str) -> bool:
        return any(candidate in tokens for candidate in candidates) or any(
            candidate in norm for candidate in candidates
        )

    if has("city"):
        return {
            "target_field": f"{target_prefix}_city",
            "confidence": 0.96,
            "reason": f"{'Receiver' if is_receiver else 'Shipper'} city pattern.",
        }
    if has("province", "prov", "state"):
        return {
            "target_field": f"{target_prefix}_province",
            "confidence": 0.93,
            "reason": f"{'Receiver' if is_receiver else 'Shipper'} province/state pattern.",
        }
    if has("postal", "zip", "pc"):
        return {
            "target_field": f"{target_prefix}_postal",
            "confidence": 0.92,
            "reason": f"{'Receiver' if is_receiver else 'Shipper'} postal/zip pattern.",
        }
    if is_receiver and has("country", "cntry", "ctry"):
        return {
            "target_field": "dest_country",
            "confidence": 0.92,
            "reason": "Receiver country pattern.",
        }
    if has("name"):
        return {
            "target_field": f"{target_prefix}_name",
            "confidence": 0.85,
            "reason": f"{'Receiver' if is_receiver else 'Shipper'} name pattern.",
        }
    if has("addr", "address", "street", "line", "strno"):
        return {
            "target_field": f"{target_prefix}_address",
            "confidence": 0.78,
            "reason": f"{'Receiver' if is_receiver else 'Shipper'} address pattern.",
        }
    if is_receiver and norm in {"rc", "receiver"}:
        return {
            "target_field": "dest_name",
            "confidence": 0.62,
            "reason": "Receiver identifier likely destination name.",
        }
    if is_shipper and norm in {"sh", "shipper", "sender"}:
        return {
            "target_field": "origin_name",
            "confidence": 0.62,
            "reason": "Shipper identifier likely origin name.",
        }
    return None


def _get_openai_client() -> Optional[OpenAI]:
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            _OPENAI_CLIENT = False
        else:
            try:
                _OPENAI_CLIENT = OpenAI(api_key=api_key)
            except Exception as exc:
                logger.warning("Failed to initialize OpenAI client for mapping: %s", exc)
                _OPENAI_CLIENT = False
    return _OPENAI_CLIENT if _OPENAI_CLIENT is not False else None


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    payload = text.strip()
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        pass

    start = payload.find("{")
    end = payload.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(payload[start : end + 1])
    except json.JSONDecodeError:
        return None


def _infer_mappings_with_ai(
    *,
    columns: List[str],
    column_samples: Dict[str, List[str]],
    deterministic_suggestions: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Ask the LLM for semantic column mapping suggestions with confidence.
    Returns normalized suggestions list; failures return [].
    """
    client = _get_openai_client()
    if not client or not columns:
        return []

    prompt = {
        "task": "Map shipment source columns to canonical fields",
        "allowed_target_fields": TARGET_FIELD_DESCRIPTIONS,
        "source_columns": columns,
        "column_samples": column_samples,
        "deterministic_suggestions": deterministic_suggestions,
        "rules": [
            "Return strict JSON only.",
            "Use target_field empty string if unknown.",
            "confidence is float 0.0-1.0.",
            "Set confidence=1.0 only when mapping is unambiguous.",
            "Prefer deterministic suggestions when they are clearly correct.",
        ],
        "response_schema": {
            "mappings": [
                {
                    "source_column": "string",
                    "target_field": "string",
                    "confidence": "float",
                    "reason": "string",
                }
            ]
        },
    }

    try:
        response = client.chat.completions.create(
            model=AI_DEFAULT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a logistics data mapping assistant that outputs strict JSON only.",
                },
                {"role": "user", "content": json.dumps(prompt)},
            ],
            temperature=0,
            max_tokens=900,
        )
        content = response.choices[0].message.content if response.choices else ""
        payload = _extract_json_object(content or "")
        if not payload:
            return []
        suggestions = payload.get("mappings")
        if not isinstance(suggestions, list):
            return []

        normalized: List[Dict[str, Any]] = []
        allowed_targets = set(TARGET_FIELD_DESCRIPTIONS.keys())
        allowed_targets.add("")
        for item in suggestions:
            if not isinstance(item, dict):
                continue
            source_column = str(item.get("source_column", "")).strip()
            if source_column not in columns:
                continue
            target_field = str(item.get("target_field", "")).strip()
            if target_field not in allowed_targets:
                target_field = ""
            try:
                confidence = float(item.get("confidence", 0))
            except (TypeError, ValueError):
                confidence = 0.0
            confidence = max(0.0, min(1.0, confidence))
            reason = str(item.get("reason", "")).strip()
            normalized.append(
                {
                    "source_column": source_column,
                    "target_field": target_field,
                    "confidence": confidence,
                    "reason": reason,
                }
            )
        return normalized
    except Exception as exc:
        logger.warning("AI mapping inference failed: %s", exc)
        return []


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
        # Try different encodings + detect shifted header rows.
        expected_header_tokens = {
            "shipmentref",
            "pronumber",
            "shipdate",
            "origincity",
            "destcity",
            "province",
            "postal",
            "weight",
            "charge",
            "trfamt",
            "invwgt",
            "prbwgt",
            "shcity",
            "cnpcity",
            "rccity",
            "rcprov",
            "rcpostal",
        }
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                preview = pd.read_csv(file_path, encoding=encoding, header=None, nrows=8)
                best_header_idx = 0
                best_score = -1
                for idx in range(len(preview.index)):
                    row_values = preview.iloc[idx].tolist()
                    row_tokens = {
                        _normalize_token(value)
                        for value in row_values
                        if pd.notna(value) and _normalize_token(value)
                    }
                    score = len(row_tokens.intersection(expected_header_tokens))
                    if score > best_score:
                        best_score = score
                        best_header_idx = idx

                if best_score >= 2 and best_header_idx > 0:
                    return pd.read_csv(file_path, encoding=encoding, header=best_header_idx)
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode CSV file")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def infer_column_mapping_detailed(
    df: pd.DataFrame,
    filename: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Infer column mappings with metadata for review workflows.

    Returns one detail row per source column:
      - source_column
      - target_field
      - confidence
      - needs_review
      - method (config|pattern|ai|unmapped)
      - reason
    """
    column_order: List[str] = []
    details_by_column: Dict[str, Dict[str, Any]] = {}
    for col in df.columns:
        if _is_meta_column(col):
            continue
        col_name = str(col)
        column_order.append(col_name)
        details_by_column[col_name] = {
            "source_column": col_name,
            "target_field": "",
            "confidence": 0.0,
            "needs_review": True,
            "method": "unmapped",
            "reason": "No mapping inferred.",
        }

    if not column_order:
        return []

    target_owner: Dict[str, str] = {}
    deterministic_suggestions: Dict[str, Dict[str, Any]] = {}

    # 1) Config mappings are authoritative and treated as fully trusted.
    if filename:
        config_mapping = get_shipment_mapping_for_file(filename, sheet_name)
        if config_mapping and config_mapping.get("columns"):
            for configured_source, target_field in config_mapping["columns"].items():
                if not target_field:
                    continue
                resolved = _resolve_source_column(list(df.columns), configured_source)
                if resolved is None or _is_meta_column(resolved):
                    continue
                source_column = str(resolved)
                if source_column not in details_by_column:
                    continue
                # Keep one owner per target field; avoid duplicate auto-maps for same target.
                existing_owner = target_owner.get(target_field)
                if existing_owner and existing_owner != source_column:
                    existing_detail = details_by_column.get(existing_owner)
                    if existing_detail and existing_detail.get("method") == "config":
                        continue

                details_by_column[source_column].update(
                    {
                        "target_field": target_field,
                        "confidence": 1.0,
                        "needs_review": False,
                        "method": "config",
                        "reason": f"Mapped from config '{configured_source}'.",
                    }
                )
                target_owner[target_field] = source_column
                deterministic_suggestions[source_column] = {
                    "target_field": target_field,
                    "confidence": 1.0,
                    "reason": "Configuration mapping",
                }

    # 2) Deterministic pattern mapping for targets not already mapped by config.
    for source_column in column_order:
        detail = details_by_column[source_column]
        if detail.get("target_field"):
            continue
        semantic = _infer_role_based_target(source_column)
        if not semantic:
            continue
        target_field = str(semantic.get("target_field") or "")
        if not target_field:
            continue
        if target_field in target_owner:
            continue
        confidence = float(semantic.get("confidence") or 0.0)
        detail.update(
            {
                "target_field": target_field,
                "confidence": confidence,
                "needs_review": confidence < 1.0,
                "method": "pattern",
                "reason": str(semantic.get("reason") or "Semantic prefix mapping."),
            }
        )
        target_owner[target_field] = source_column
        deterministic_suggestions[source_column] = {
            "target_field": target_field,
            "confidence": confidence,
            "reason": str(semantic.get("reason") or "Semantic prefix mapping"),
        }

    # 3) Deterministic pattern mapping for targets not already mapped by config.
    for target_field, patterns in COLUMN_PATTERNS.items():
        if target_field in target_owner:
            continue
        best_source: Optional[str] = None
        best_pattern: Optional[str] = None
        best_score = 0.0
        for source_column in column_order:
            detail = details_by_column[source_column]
            if detail.get("target_field"):
                continue
            for pattern in patterns:
                score = _score_pattern_match(source_column, pattern)
                if score > best_score:
                    best_score = score
                    best_source = source_column
                    best_pattern = pattern

        if best_source and best_score >= PATTERN_MATCH_MIN_CONFIDENCE:
            details_by_column[best_source].update(
                {
                    "target_field": target_field,
                    "confidence": best_score,
                    "needs_review": best_score < 1.0,
                    "method": "pattern",
                    "reason": f"Pattern match '{best_pattern}' ({best_score:.2f}).",
                }
            )
            target_owner[target_field] = best_source
            deterministic_suggestions[best_source] = {
                "target_field": target_field,
                "confidence": best_score,
                "reason": f"Pattern '{best_pattern}'",
            }

    # 4) AI pass for semantic mapping and confidence scoring.
    should_call_ai = any(
        (not details_by_column[col]["target_field"]) or details_by_column[col]["confidence"] < 1.0
        for col in column_order
    )
    if should_call_ai:
        ai_suggestions = _infer_mappings_with_ai(
            columns=column_order,
            column_samples=_build_column_samples(df),
            deterministic_suggestions=deterministic_suggestions,
        )
        ai_suggestions.sort(key=lambda item: float(item.get("confidence", 0.0)), reverse=True)

        for suggestion in ai_suggestions:
            source_column = str(suggestion.get("source_column", ""))
            target_field = str(suggestion.get("target_field", ""))
            confidence = float(suggestion.get("confidence", 0.0))
            reason = str(suggestion.get("reason", "")).strip()

            if (
                not source_column
                or source_column not in details_by_column
                or not target_field
                or confidence < AI_MATCH_MIN_CONFIDENCE
            ):
                continue

            detail = details_by_column[source_column]
            if detail.get("method") == "config":
                continue

            current_target = str(detail.get("target_field") or "")
            current_conf = float(detail.get("confidence") or 0.0)

            should_apply = False
            if not current_target:
                should_apply = True
            elif current_target == target_field and confidence > current_conf:
                should_apply = True
            elif confidence >= current_conf + 0.08:
                should_apply = True

            if not should_apply:
                continue

            existing_owner = target_owner.get(target_field)
            if existing_owner and existing_owner != source_column:
                existing_detail = details_by_column.get(existing_owner)
                if existing_detail:
                    if existing_detail.get("method") == "config":
                        continue
                    existing_conf = float(existing_detail.get("confidence") or 0.0)
                    if confidence <= existing_conf + 0.02:
                        continue
                    existing_detail.update(
                        {
                            "target_field": "",
                            "confidence": 0.0,
                            "needs_review": True,
                            "method": "unmapped",
                            "reason": f"Replaced by stronger AI match for '{target_field}'.",
                        }
                    )

            if current_target and target_owner.get(current_target) == source_column and current_target != target_field:
                target_owner.pop(current_target, None)

            detail.update(
                {
                    "target_field": target_field,
                    "confidence": confidence,
                    "needs_review": confidence < 1.0,
                    "method": "ai",
                    "reason": reason or "AI semantic mapping.",
                }
            )
            target_owner[target_field] = source_column

    # Normalize confidence precision + review flag consistency.
    result: List[Dict[str, Any]] = []
    for source_column in column_order:
        detail = details_by_column[source_column]
        confidence = max(0.0, min(1.0, float(detail.get("confidence") or 0.0)))
        detail["confidence"] = round(confidence, 3)
        detail["needs_review"] = (not detail.get("target_field")) or confidence < 1.0
        result.append(detail)

    return result


def infer_column_mapping(
    df: pd.DataFrame,
    filename: Optional[str] = None,
    sheet_name: Optional[str] = None,
) -> Dict[str, str]:
    """
    Backward-compatible mapping API.
    Returns dict mapping source_column -> target_field.
    """
    detailed = infer_column_mapping_detailed(df, filename, sheet_name)
    return {
        item["source_column"]: item["target_field"]
        for item in detailed
        if item.get("target_field")
    }


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
