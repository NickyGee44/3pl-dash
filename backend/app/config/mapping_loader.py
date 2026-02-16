"""
Utilities for loading column/tariff mapping configuration.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "column_mappings.yaml"


def _slugify(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


@lru_cache()
def load_mapping_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def get_region_from_config(province: Optional[str]) -> Optional[str]:
    if not province:
        return None
    config = load_mapping_config()
    region_map = config.get("region_map", {})
    province_upper = province.upper().strip()
    return region_map.get(province_upper, region_map.get("default"))


def _match_file_config(section: str, filename: str) -> Optional[Dict[str, Any]]:
    config = load_mapping_config().get(section, {})
    filename_lower = filename.lower()
    filename_stem_lower = Path(filename).stem.lower()
    filename_slug = _slugify(filename_stem_lower)
    best_match: Optional[Dict[str, Any]] = None
    best_score = -1
    best_key_len = -1

    for key, value in config.items():
        key_text = str(key).lower()
        key_stem = Path(key_text).stem.lower()
        key_slug = _slugify(key_stem)

        score = -1
        if key_text in filename_lower:
            # Exact configured text match (including extension) is strongest.
            score = 300
        elif key_stem and key_stem in filename_stem_lower:
            # Same source file stem but different runtime extension (e.g., .xlsx -> .csv).
            score = 220
        elif key_slug and key_slug in filename_slug:
            # Fuzzy slug match for sanitized upload names.
            score = 150

        if score > best_score or (score == best_score and len(key_stem) > best_key_len):
            best_match = value
            best_score = score
            best_key_len = len(key_stem)

    return best_match


def _match_sheet_config(file_cfg: Dict[str, Any], filename: str, sheet_name: Optional[str]) -> Optional[Dict[str, Any]]:
    sheets = file_cfg.get("sheets") or {}
    if not sheets:
        return None
    candidate_slug = _slugify(sheet_name)
    if candidate_slug:
        for cfg_name, cfg in sheets.items():
            if _slugify(cfg_name) == candidate_slug:
                return cfg
    filename_slug = _slugify(Path(filename).stem)
    for cfg_name, cfg in sheets.items():
        if _slugify(cfg_name) and _slugify(cfg_name) in filename_slug:
            return cfg
    return None


def get_shipment_mapping_for_file(filename: str, sheet_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    file_cfg = _match_file_config("shipments", filename)
    if not file_cfg:
        return None
    mapping: Dict[str, Any] = {
        "columns": dict(file_cfg.get("defaults", {}).get("columns", {}))
    }
    sheet_cfg = _match_sheet_config(file_cfg, filename, sheet_name)
    if sheet_cfg:
        mapping["columns"].update(sheet_cfg.get("columns", {}))
        if sheet_cfg.get("origin_dc"):
            mapping["origin_dc"] = sheet_cfg["origin_dc"]
    return mapping


def get_tariff_mapping_for_file(filename: str, carrier_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    config = load_mapping_config().get("tariffs", {})
    filename_lower = filename.lower()
    for key, value in config.items():
        if key.lower() in filename_lower:
            if carrier_name and value.get("carrier_name") != carrier_name:
                continue
            return value
    return None
