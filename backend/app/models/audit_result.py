"""
Audit Result model - computed metrics and flags per shipment.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.db.database import Base


class AuditResult(Base):
    __tablename__ = "audit_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_run_id = Column(UUID(as_uuid=True), ForeignKey("audit_runs.id"), nullable=False)
    shipment_id = Column(UUID(as_uuid=True), ForeignKey("shipments.id"), nullable=False, unique=True)
    
    cost_per_lb = Column(Numeric(10, 4), nullable=True)
    cost_per_pallet = Column(Numeric(10, 2), nullable=True)
    flags = Column(ARRAY(String), nullable=True)  # e.g., ["ZERO_CHARGE", "NEGATIVE_PRICE", "DIM_HEAVY"]
    
    # For re-rating
    expected_charge_per_carrier = Column(JSONB, nullable=True)  # {"APPS": 150.00, "Rosedale": 145.00, ...}
    best_carrier = Column(String, nullable=True)
    best_charge = Column(Numeric(10, 2), nullable=True)
    savings_vs_actual = Column(Numeric(10, 2), nullable=True)
    
    # Tariff matching status - NEVER overwrite dest_city/dest_province
    # Instead, track match status separately
    tariff_match_status = Column(String, nullable=True)  # "MATCHED", "NO_LANE", "MULTIPLE_LANES"
    tariff_match_notes = Column(String, nullable=True)  # e.g., "City not in tariff"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    audit_run = relationship("AuditRun")
    shipment = relationship("Shipment", back_populates="audit_result")


