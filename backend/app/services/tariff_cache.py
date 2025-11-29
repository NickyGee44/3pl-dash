"""
Tariff cache utilities to keep tariff/lanes/breaks in memory for fast rating.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from threading import Lock
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session, selectinload

from app.models.tariff import Tariff, TariffLane, TariffBreak, TariffType


def _to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass
class CwtBreak:
    start: Optional[Decimal]
    end: Optional[Decimal]
    rate_per_cwt: Decimal


@dataclass
class SkidBreak:
    num_spots: int
    charge: Decimal


@dataclass
class TariffLaneCache:
    min_charge: Decimal
    cwt_breaks: List[CwtBreak] = field(default_factory=list)
    skid_breaks: Dict[int, Decimal] = field(default_factory=dict)


@dataclass
class TariffCacheEntry:
    id: str
    carrier_name: str
    origin_dc: str
    tariff_type: TariffType
    lanes_by_city: Dict[Tuple[str, str], TariffLaneCache] = field(default_factory=dict)
    lanes_by_province: Dict[str, TariffLaneCache] = field(default_factory=dict)

    def _normalize_key(self, city: Optional[str], province: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        city_key = city.upper().strip() if city else None
        prov_key = province.upper().strip() if province else None
        return city_key, prov_key

    def find_lane(self, dest_city: Optional[str], dest_province: Optional[str]) -> Optional[TariffLaneCache]:
        if not dest_province:
            return None
        city_key, prov_key = self._normalize_key(dest_city, dest_province)
        if city_key and prov_key:
            lane = self.lanes_by_city.get((city_key, prov_key))
            if lane:
                return lane
        if prov_key:
            return self.lanes_by_province.get(prov_key)
        return None


@dataclass
class TariffCache:
    entries: List[TariffCacheEntry]
    last_loaded: datetime


_TARIFF_CACHE: Optional[TariffCache] = None
_CACHE_LOCK = Lock()
_CACHE_TTL = timedelta(minutes=10)


def _build_lane_cache(lane: TariffLane) -> TariffLaneCache:
    min_charge = _to_decimal(lane.min_charge) or Decimal("0")
    cache = TariffLaneCache(min_charge=min_charge)

    for br in lane.breaks:
        rate = _to_decimal(br.rate_per_cwt)
        if br.num_spots and br.spot_charge is not None:
            cache.skid_breaks[int(br.num_spots)] = _to_decimal(br.spot_charge) or Decimal("0")
        elif rate is not None:
            cache.cwt_breaks.append(
                CwtBreak(
                    start=_to_decimal(br.break_from_weight),
                    end=_to_decimal(br.break_to_weight),
                    rate_per_cwt=rate,
                )
            )

    # Ensure CWT breaks sorted by start weight
    cache.cwt_breaks.sort(key=lambda b: b.start or Decimal("0"))
    return cache


def _load_tariff_cache(db: Session) -> TariffCache:
    tariffs = (
        db.query(Tariff)
        .options(selectinload(Tariff.lanes).selectinload(TariffLane.breaks))
        .all()
    )

    entries: List[TariffCacheEntry] = []
    for tariff in tariffs:
        entry = TariffCacheEntry(
            id=str(tariff.id),
            carrier_name=tariff.carrier_name,
            origin_dc=tariff.origin_dc,
            tariff_type=tariff.tariff_type,
        )
        for lane in tariff.lanes:
            lane_cache = _build_lane_cache(lane)
            prov_key = lane.dest_province.upper().strip()
            if lane.dest_city:
                city_key = lane.dest_city.upper().strip()
                entry.lanes_by_city[(city_key, prov_key)] = lane_cache
            else:
                entry.lanes_by_province[prov_key] = lane_cache
        entries.append(entry)

    return TariffCache(entries=entries, last_loaded=datetime.utcnow())


def get_tariff_cache(db: Session, force_reload: bool = False) -> TariffCache:
    global _TARIFF_CACHE
    with _CACHE_LOCK:
        should_reload = force_reload or _TARIFF_CACHE is None
        if _TARIFF_CACHE and not should_reload:
            if datetime.utcnow() - _TARIFF_CACHE.last_loaded > _CACHE_TTL:
                should_reload = True
        if should_reload:
            _TARIFF_CACHE = _load_tariff_cache(db)
        return _TARIFF_CACHE


