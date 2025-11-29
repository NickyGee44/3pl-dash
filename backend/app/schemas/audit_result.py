"""
Audit Result schemas.
"""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Dict
from decimal import Decimal


class AuditResultResponse(BaseModel):
    id: UUID
    audit_run_id: UUID
    shipment_id: UUID
    cost_per_lb: Optional[Decimal] = None
    cost_per_pallet: Optional[Decimal] = None
    flags: Optional[List[str]] = None
    expected_charge_per_carrier: Optional[Dict[str, float]] = None
    best_carrier: Optional[str] = None
    best_charge: Optional[Decimal] = None
    savings_vs_actual: Optional[Decimal] = None

    class Config:
        from_attributes = True


