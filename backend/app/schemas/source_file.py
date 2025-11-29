"""
Source File schemas.
"""
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, List


class ColumnMapping(BaseModel):
    """Column mapping from source to normalized field."""
    source_column: str
    target_field: str  # e.g., "weight", "pallets", "actual_charge"
    confidence: Optional[float] = None  # 0-1, for inferred mappings


class FileMappingRequest(BaseModel):
    """Request to set column mappings for a file."""
    file_id: UUID
    mappings: List[ColumnMapping]


class SourceFileResponse(BaseModel):
    id: UUID
    audit_run_id: UUID
    original_filename: str
    file_type: str
    inferred_source_type: Optional[str] = None
    created_at: datetime
    inferred_mappings: Optional[Dict[str, str]] = None  # Proposed column mappings
    columns: Optional[List[str]] = None

    class Config:
        from_attributes = True


