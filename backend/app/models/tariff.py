"""
Tariff models for carrier rate sheets.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from app.db.database import Base


class TariffType(str, enum.Enum):
    CWT = "cwt"
    SKID_SPOT = "skid_spot"


class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    carrier_name = Column(String, nullable=False)  # "APPS", "Rosedale", "Maritime Ontario", etc.
    origin_dc = Column(String, nullable=False)  # "SCARB", "CGY"
    tariff_type = Column(SQLEnum(TariffType), nullable=False)
    effective_from = Column(DateTime, nullable=True)
    effective_to = Column(DateTime, nullable=True)
    tariff_metadata = Column(JSONB, nullable=True)  # For future extension
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lanes = relationship("TariffLane", back_populates="tariff", cascade="all, delete-orphan")


class TariffLane(Base):
    __tablename__ = "tariff_lanes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tariff_id = Column(UUID(as_uuid=True), ForeignKey("tariffs.id"), nullable=False)
    dest_city = Column(String, nullable=True)
    dest_province = Column(String, nullable=False)
    postal_prefix = Column(String, nullable=True)
    zone_code = Column(String, nullable=True)
    min_charge = Column(Numeric(10, 2), nullable=True)  # For CWT tariffs
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tariff = relationship("Tariff", back_populates="lanes")
    breaks = relationship("TariffBreak", back_populates="lane", cascade="all, delete-orphan")


class TariffBreak(Base):
    __tablename__ = "tariff_breaks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tariff_lane_id = Column(UUID(as_uuid=True), ForeignKey("tariff_lanes.id"), nullable=False)
    
    # For CWT tariffs: weight range and rate
    break_from_weight = Column(Numeric(10, 2), nullable=True)  # Inclusive
    break_to_weight = Column(Numeric(10, 2), nullable=True)  # Exclusive or None for max
    rate_per_cwt = Column(Numeric(10, 4), nullable=True)  # $/CWT
    
    # For SKID_SPOT tariffs: number of spots and charge
    num_spots = Column(Integer, nullable=True)  # For APPS
    spot_charge = Column(Numeric(10, 2), nullable=True)  # Flat charge for that many spots
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    lane = relationship("TariffLane", back_populates="breaks")

