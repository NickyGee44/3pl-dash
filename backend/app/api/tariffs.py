"""
Tariff management API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File as FastAPIFile
from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from uuid import UUID
import os
from pathlib import Path
from app.db.database import get_db, settings
from app.models import Tariff, TariffLane
from app.schemas.tariff import TariffResponse, TariffCreate
from app.services.tariff_cache import get_tariff_cache
from app.services.tariff_ingestion import (
    parse_apps_tariff,
    ingest_rosedale_tariff,
    ingest_maritime_ontario_tariff,
    ingest_guilbault_tariff,
    ingest_cff_tariff
)

router = APIRouter()

# Mapping of carrier names to ingestion functions
TARIFF_INGESTION_MAP = {
    "APPS": parse_apps_tariff,
    "Rosedale": ingest_rosedale_tariff,
    "Maritime Ontario": ingest_maritime_ontario_tariff,
    "Groupe Guilbault": ingest_guilbault_tariff,
    "CFF": ingest_cff_tariff,
}


@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_tariff_file(
    carrier_name: str,
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db)
):
    """
    Ingest a tariff file for a specific carrier.
    
    Supported carriers: APPS, Rosedale, Maritime Ontario, Groupe Guilbault, CFF
    """
    if carrier_name not in TARIFF_INGESTION_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported carrier: {carrier_name}. Supported: {list(TARIFF_INGESTION_MAP.keys())}"
        )
    
    # Save uploaded file temporarily
    upload_dir = Path(settings.upload_dir) / "tariffs"
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    file_path = upload_dir / file.filename
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    try:
        # Call appropriate ingestion function
        ingestion_func = TARIFF_INGESTION_MAP[carrier_name]
        tariff = ingestion_func(str(file_path), db)
        
        return {
            "message": f"Tariff ingested successfully for {carrier_name}",
            "tariff_id": str(tariff.id),
            "carrier_name": tariff.carrier_name,
            "origin_dc": tariff.origin_dc,
            "tariff_type": tariff.tariff_type.value
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error ingesting tariff: {str(e)}"
        )
    finally:
        # Clean up temp file
        if file_path.exists():
            file_path.unlink()


@router.get("/", response_model=List[TariffResponse])
async def list_tariffs(
    carrier_name: Optional[str] = None,
    origin_dc: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all tariffs, optionally filtered."""
    query = db.query(Tariff).options(
        selectinload(Tariff.lanes).selectinload(TariffLane.breaks)
    )
    
    if carrier_name:
        query = query.filter(Tariff.carrier_name == carrier_name)
    if origin_dc:
        query = query.filter(Tariff.origin_dc == origin_dc)
    
    tariffs = query.all()
    for tariff in tariffs:
        lane_count = len(tariff.lanes or [])
        break_count = sum(len(lane.breaks or []) for lane in tariff.lanes or [])
        setattr(tariff, "lane_count", lane_count)
        setattr(tariff, "break_count", break_count)
    return tariffs


@router.get("/{tariff_id}", response_model=TariffResponse)
async def get_tariff(
    tariff_id: UUID,
    db: Session = Depends(get_db)
):
    """Get a specific tariff."""
    tariff = db.query(Tariff).filter(Tariff.id == tariff_id).first()
    if not tariff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tariff {tariff_id} not found"
        )
    lane_count = len(tariff.lanes or [])
    break_count = sum(len(lane.breaks or []) for lane in (tariff.lanes or []))
    setattr(tariff, "lane_count", lane_count)
    setattr(tariff, "break_count", break_count)
    return tariff


@router.post("/refresh-cache", status_code=status.HTTP_200_OK)
async def refresh_tariff_cache(
    db: Session = Depends(get_db)
):
    """Force refresh the in-memory tariff cache."""
    get_tariff_cache(db, force_reload=True)
    return {"message": "Tariff cache refreshed"}

