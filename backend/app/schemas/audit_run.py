"""
Audit Run schemas.
"""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.audit_run import AuditRunStatus


class AuditRunCreate(BaseModel):
    customer_id: UUID
    name: str
    label: Optional[str] = None


class AuditRunResponse(BaseModel):
    id: UUID
    customer_id: UUID
    name: str
    label: Optional[str] = None
    status: AuditRunStatus
    created_at: datetime
    updated_at: datetime
    summary_metrics: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AuditRunSummary(BaseModel):
    id: UUID
    customer_name: str
    name: str
    label: Optional[str] = None
    status: AuditRunStatus
    created_at: datetime
    shipment_count: int = 0
    total_spend: Optional[float] = None
    theoretical_savings: Optional[float] = None
    carrier_savings_total: Optional[float] = None
    consolidation_savings_total: Optional[float] = None
    total_opportunity: Optional[float] = None


class AuditQuestionRequest(BaseModel):
    question: str

