"""
Tariff schemas.
"""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.tariff import TariffType


class TariffCreate(BaseModel):
    carrier_name: str
    origin_dc: str
    tariff_type: TariffType
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None


class TariffResponse(BaseModel):
    id: UUID
    carrier_name: str
    origin_dc: str
    tariff_type: TariffType
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    tariff_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    lane_count: Optional[int] = None
    break_count: Optional[int] = None

    class Config:
        from_attributes = True

