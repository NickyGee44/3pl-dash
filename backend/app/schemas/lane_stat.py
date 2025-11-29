"""
Lane Stat schemas.
"""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from decimal import Decimal


class LaneStatResponse(BaseModel):
    id: UUID
    audit_run_id: UUID
    origin_dc: str
    dest_province: Optional[str] = None
    dest_region: Optional[str] = None
    dest_city: Optional[str] = None
    shipment_count: int
    total_spend: Decimal
    total_weight: Decimal
    total_pallets: Decimal
    avg_charge_per_shipment: Optional[Decimal] = None
    avg_cost_per_lb: Optional[Decimal] = None
    avg_cost_per_pallet: Optional[Decimal] = None
    theoretical_best_spend: Optional[Decimal] = None
    theoretical_savings: Optional[Decimal] = None
    savings_pct: Optional[Decimal] = None

    class Config:
        from_attributes = True


