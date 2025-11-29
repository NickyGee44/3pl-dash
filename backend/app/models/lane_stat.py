"""
Lane Stat model - aggregated statistics by origin DC and destination.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.db.database import Base


class LaneStat(Base):
    __tablename__ = "lane_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_run_id = Column(UUID(as_uuid=True), ForeignKey("audit_runs.id"), nullable=False)
    
    origin_dc = Column(String, nullable=False)
    dest_province = Column(String, nullable=True)
    dest_region = Column(String, nullable=True)
    dest_city = Column(String, nullable=True)
    
    shipment_count = Column(Integer, default=0)
    total_spend = Column(Numeric(12, 2), default=0)
    total_weight = Column(Numeric(12, 2), default=0)
    total_pallets = Column(Numeric(12, 2), default=0)
    avg_charge_per_shipment = Column(Numeric(10, 2), nullable=True)
    avg_cost_per_lb = Column(Numeric(10, 4), nullable=True)
    avg_cost_per_pallet = Column(Numeric(10, 2), nullable=True)
    
    # Theoretical best-case savings
    theoretical_best_spend = Column(Numeric(12, 2), nullable=True)
    theoretical_savings = Column(Numeric(12, 2), nullable=True)
    savings_pct = Column(Numeric(10, 4), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    audit_run = relationship("AuditRun", back_populates="lane_stats")


