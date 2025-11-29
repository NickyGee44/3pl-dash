"""
File upload and processing API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import os
import shutil
from pathlib import Path
import pandas as pd
import time
import logging
from app.db.database import get_db, settings
from app.models import AuditRun, SourceFile, Shipment
from app.schemas.source_file import SourceFileResponse, FileMappingRequest, ColumnMapping
from app.services.file_parser import (
    infer_file_type, read_file, infer_column_mapping, infer_source_type
)
from app.services.normalizer import normalize_row
from app.config.mapping_loader import get_shipment_mapping_for_file

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{audit_run_id}/upload", response_model=List[SourceFileResponse], status_code=status.HTTP_201_CREATED)
async def upload_files(
    audit_run_id: UUID,
    files: List[UploadFile] = FastAPIFile(...),
    db: Session = Depends(get_db)
):
    """Upload one or more files for an audit run."""
    # Verify audit run exists
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit run {audit_run_id} not found"
        )
    
    # Ensure upload directory exists
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    saved_files = []
    
    batch_start = time.perf_counter()
    for file in files:
        file_timer = time.perf_counter()
        # Determine file type
        file_type = infer_file_type(file.filename)
        
        # Save file
        file_path = upload_dir / f"{audit_run_id}_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Infer source type from filename
        inferred_source_type = infer_source_type(file.filename)
        
        # Create source file record
        source_file = SourceFile(
            audit_run_id=audit_run_id,
            original_filename=file.filename,
            storage_path=str(file_path),
            file_type=file_type,
            inferred_source_type=inferred_source_type,
        )
        db.add(source_file)
        db.commit()
        db.refresh(source_file)
        
        saved_files.append(source_file)
        duration = time.perf_counter() - file_timer
        file_size = file_path.stat().st_size if file_path.exists() else 0
        logger.info(
            "Uploaded file %s (%.1f KB) for audit %s in %.2fs",
            file.filename,
            file_size / 1024 if file_size else 0,
            audit_run_id,
            duration,
        )
    
    total_duration = round(time.perf_counter() - batch_start, 3)
    logger.info(
        "Uploaded %d file(s) for audit %s in %.2fs",
        len(saved_files),
        audit_run_id,
        total_duration,
    )
    
    return saved_files


@router.get("/{file_id}/mappings", response_model=SourceFileResponse)
async def get_file_mappings(
    file_id: UUID,
    db: Session = Depends(get_db)
):
    """Get inferred column mappings for a file."""
    source_file = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if not source_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found"
        )
    
    # Read file and infer mappings
    try:
        df = read_file(source_file.storage_path, source_file.file_type)
        sheet_name = None
        if "__sheet_name" in df.columns and not df["__sheet_name"].isna().all():
            sheet_name = str(df["__sheet_name"].iloc[0])
        mappings = infer_column_mapping(df, source_file.original_filename, sheet_name)
        columns = [str(col) for col in df.columns]
        
        # Convert to dict format for response
        inferred_mappings = {k: v for k, v in mappings.items()}
        
        # Create response with inferred mappings
        response = SourceFileResponse(
            id=source_file.id,
            audit_run_id=source_file.audit_run_id,
            original_filename=source_file.original_filename,
            file_type=source_file.file_type,
            inferred_source_type=source_file.inferred_source_type,
            created_at=source_file.created_at,
            inferred_mappings=inferred_mappings,
            columns=columns,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reading file: {str(e)}"
        )


@router.post("/{file_id}/normalize", status_code=status.HTTP_200_OK)
async def normalize_file(
    file_id: UUID,
    mapping_request: FileMappingRequest,
    db: Session = Depends(get_db)
):
    """Normalize a file using provided column mappings."""
    source_file = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if not source_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found"
        )
    
    # Verify audit run
    audit_run = db.query(AuditRun).filter(AuditRun.id == source_file.audit_run_id).first()
    if not audit_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit run not found"
        )
    
    # Delete existing shipments from this file (for reprocessing)
    db.query(Shipment).filter(Shipment.source_file_id == file_id).delete()
    
    try:
        timings = {}
        total_start = time.perf_counter()
        # Read file
        read_start = time.perf_counter()
        df = read_file(source_file.storage_path, source_file.file_type)
        timings["read_file"] = round(time.perf_counter() - read_start, 3)
        sheet_name_hint = None
        if "__sheet_name" in df.columns and not df["__sheet_name"].isna().all():
            sheet_name_hint = str(df["__sheet_name"].iloc[0])
        
        # Load mapping defaults from config (if available) and merge with user mappings
        base_config = get_shipment_mapping_for_file(source_file.original_filename, sheet_name_hint)
        mappings = {}
        if base_config and base_config.get("columns"):
            mappings.update(base_config["columns"])
        # User-provided mappings override defaults
        user_mappings = {m.source_column: m.target_field for m in mapping_request.mappings}
        mappings.update(user_mappings)
        
        # Infer origin_dc from mapping config or source type
        origin_dc_default = base_config.get("origin_dc") if base_config else None
        if source_file.inferred_source_type:
            if "Calgary" in source_file.inferred_source_type or "CGY" in source_file.inferred_source_type:
                origin_dc_default = "CGY"
            elif "Scarborough" in source_file.inferred_source_type or "SCARB" in source_file.inferred_source_type:
                origin_dc_default = "SCARB"
            elif "Toronto" in source_file.inferred_source_type or "TOR" in source_file.inferred_source_type:
                origin_dc_default = "TOR"
            elif "Montreal" in source_file.inferred_source_type or "MTL" in source_file.inferred_source_type:
                origin_dc_default = "MTL"
        
        # Normalize each row
        shipments_created = 0
        normalize_start = time.perf_counter()
        batch: List[dict] = []
        BATCH_SIZE = 1000
        for idx, row in df.iterrows():
            row_sheet = None
            if "__sheet_name" in row and not pd.isna(row["__sheet_name"]):
                row_sheet = str(row["__sheet_name"])
            row_config = get_shipment_mapping_for_file(source_file.original_filename, row_sheet)
            row_origin_dc = origin_dc_default
            if row_config and row_config.get("origin_dc"):
                row_origin_dc = row_config["origin_dc"]
            
            normalized = normalize_row(
                row,
                mappings,
                str(source_file.id),
                str(source_file.audit_run_id),
                row.to_dict()
            )
            
            # Set origin_dc if inferred
            if row_origin_dc:
                normalized["origin_dc"] = row_origin_dc
            
            batch.append(normalized)
            shipments_created += 1
            if len(batch) >= BATCH_SIZE:
                db.bulk_insert_mappings(Shipment, batch)
                batch.clear()
        
        if batch:
            db.bulk_insert_mappings(Shipment, batch)
        
        timings["normalize_rows"] = round(time.perf_counter() - normalize_start, 3)
        commit_start = time.perf_counter()
        db.commit()
        timings["db_commit"] = round(time.perf_counter() - commit_start, 3)
        timings["total"] = round(time.perf_counter() - total_start, 3)
        logger.info(
            "Normalized file %s (%d rows) for audit %s timings=%s",
            source_file.original_filename,
            shipments_created,
            source_file.audit_run_id,
            timings,
        )
        
        return {
            "message": f"Normalized {shipments_created} shipments from file",
            "shipments_created": shipments_created,
            "timings": timings,
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error normalizing file: {str(e)}"
        )


@router.get("/{file_id}", response_model=SourceFileResponse)
async def get_file(
    file_id: UUID,
    db: Session = Depends(get_db)
):
    """Get file details."""
    source_file = db.query(SourceFile).filter(SourceFile.id == file_id).first()
    if not source_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found"
        )
    return source_file
