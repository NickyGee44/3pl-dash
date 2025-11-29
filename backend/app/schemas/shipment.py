"""
Shipment schemas.
"""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime, date
from typing import Optional, Dict, Any
from decimal import Decimal


class ShipmentResponse(BaseModel):
    id: UUID
    audit_run_id: UUID
    source_file_id: UUID
    shipment_ref: Optional[str] = None
    origin_dc: Optional[str] = None
    origin_city: Optional[str] = None
    origin_province: Optional[str] = None
    origin_postal: Optional[str] = None
    dest_city: Optional[str] = None
    dest_province: Optional[str] = None
    dest_postal: Optional[str] = None
    dest_region: Optional[str] = None
    ship_date: Optional[date] = None
    pallets: Optional[Decimal] = None
    weight: Optional[Decimal] = None
    dim_weight: Optional[Decimal] = None
    actual_charge: Optional[Decimal] = None
    carrier: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


