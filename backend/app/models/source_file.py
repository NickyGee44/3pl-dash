"""
Source File model.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.db.database import Base


class SourceFile(Base):
    __tablename__ = "source_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_run_id = Column(UUID(as_uuid=True), ForeignKey("audit_runs.id"), nullable=False)
    original_filename = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)  # Path or S3 key
    file_type = Column(String, nullable=False)  # xlsx, csv, etc.
    inferred_source_type = Column(String, nullable=True)  # e.g., "Calgary DC export"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    audit_run = relationship("AuditRun", back_populates="source_files")
    shipments = relationship("Shipment", back_populates="source_file", cascade="all, delete-orphan")


