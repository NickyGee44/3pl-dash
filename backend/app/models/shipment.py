"""
Shipment model - normalized shipment data.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.db.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_run_id = Column(UUID(as_uuid=True), ForeignKey("audit_runs.id"), nullable=False)
    source_file_id = Column(UUID(as_uuid=True), ForeignKey("source_files.id"), nullable=False)
    
    # Normalized fields
    shipment_ref = Column(String, nullable=True)
    origin_dc = Column(String, nullable=True)  # e.g., "CGY", "SCARB"
    origin_city = Column(String, nullable=True)
    origin_province = Column(String, nullable=True)
    origin_postal = Column(String, nullable=True)
    dest_city = Column(String, nullable=True)
    dest_province = Column(String, nullable=True)
    dest_postal = Column(String, nullable=True)
    dest_region = Column(String, nullable=True)  # e.g., "West", "ON", "QC"
    ship_date = Column(Date, nullable=True)
    pallets = Column(Numeric(10, 2), nullable=True)
    weight = Column(Numeric(10, 2), nullable=True)  # Scale weight
    dim_weight = Column(Numeric(10, 2), nullable=True)
    actual_charge = Column(Numeric(10, 2), nullable=True)
    carrier = Column(String, nullable=True)
    
    # Raw JSON of extra columns for debugging
    raw_data = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    audit_run = relationship("AuditRun", back_populates="shipments")
    source_file = relationship("SourceFile", back_populates="shipments")
    audit_result = relationship("AuditResult", back_populates="shipment", uselist=False, cascade="all, delete-orphan")


