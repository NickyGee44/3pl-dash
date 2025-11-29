"""
Audit Run model.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.db.database import Base


class AuditRunStatus(str, enum.Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    name = Column(String, nullable=False)
    label = Column(String, nullable=True)  # e.g., "Global Industrial – July–Dec 2024"
    status = Column(
        SQLEnum(
            AuditRunStatus,
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            validate_strings=True,
        ),
        default=AuditRunStatus.CREATED.value,
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user_id = Column(UUID(as_uuid=True), nullable=True)  # For future auth
    summary_metrics = Column(JSONB, nullable=True)  # Denormalized cache of key metrics

    # Relationships
    customer = relationship("Customer", back_populates="audit_runs")
    source_files = relationship("SourceFile", back_populates="audit_run", cascade="all, delete-orphan")
    shipments = relationship("Shipment", back_populates="audit_run", cascade="all, delete-orphan")
    lane_stats = relationship("LaneStat", back_populates="audit_run", cascade="all, delete-orphan")


