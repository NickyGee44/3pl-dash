"""
Script to ingest all 2025 tariff files into the database.
Run this after setting up the database and installing dependencies.
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.services.tariff_ingestion import (
    parse_apps_tariff,
    ingest_rosedale_tariff,
    ingest_maritime_ontario_tariff,
    ingest_guilbault_tariff,
    ingest_cff_tariff
)

# Path to tariff files (assuming they're in the project root, one level up from backend)
# Script is in: backend/scripts/ingest_all_tariffs.py
# Files are in: /3PL/ (project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Verify we found the right directory
if not (PROJECT_ROOT / "APPS FAK Skid Rates 2025.xlsx").exists():
    # Try alternative: current working directory
    alt_root = Path.cwd()
    if (alt_root / "APPS FAK Skid Rates 2025.xlsx").exists():
        PROJECT_ROOT = alt_root
    else:
        print(f"Warning: Could not find tariff files in {PROJECT_ROOT} or {alt_root}")
        print("Please ensure Excel files are in the project root directory.")
TARIFF_FILES = {
    "APPS": PROJECT_ROOT / "APPS FAK Skid Rates 2025.xlsx",
    "Rosedale": PROJECT_ROOT / "Rosedale Ex Toronto 2025 10lbs cwt.xlsx",
    "Maritime Ontario": PROJECT_ROOT / "MO ex TOR  10lbs cwt Maritimes 2025.xlsx",
    "Groupe Guilbault": PROJECT_ROOT / "Groupe Guilbault exTOR 15cwt 2025.xlsx",
    "CFF": PROJECT_ROOT / "CFF ex CGY 10lbs cwt to Western Canada Saftey Express 2025.xlsx",
}


def ingest_all_tariffs():
    """Ingest all tariff files."""
    db = SessionLocal()
    
    try:
        results = {}
        
        # Ingest APPS
        if TARIFF_FILES["APPS"].exists():
            print(f"Ingesting APPS tariff from {TARIFF_FILES['APPS']}...")
            tariff = parse_apps_tariff(str(TARIFF_FILES["APPS"]), db)
            results["APPS"] = {"id": str(tariff.id), "lanes": len(tariff.lanes)}
            print(f"✓ APPS: {len(tariff.lanes)} lanes loaded")
        else:
            print(f"✗ APPS file not found: {TARIFF_FILES['APPS']}")
        
        # Ingest Rosedale
        if TARIFF_FILES["Rosedale"].exists():
            print(f"\nIngesting Rosedale tariff from {TARIFF_FILES['Rosedale']}...")
            tariff = ingest_rosedale_tariff(str(TARIFF_FILES["Rosedale"]), db)
            results["Rosedale"] = {"id": str(tariff.id), "lanes": len(tariff.lanes)}
            print(f"✓ Rosedale: {len(tariff.lanes)} lanes loaded")
        else:
            print(f"✗ Rosedale file not found: {TARIFF_FILES['Rosedale']}")
        
        # Ingest Maritime Ontario
        if TARIFF_FILES["Maritime Ontario"].exists():
            print(f"\nIngesting Maritime Ontario tariff from {TARIFF_FILES['Maritime Ontario']}...")
            tariff = ingest_maritime_ontario_tariff(str(TARIFF_FILES["Maritime Ontario"]), db)
            results["Maritime Ontario"] = {"id": str(tariff.id), "lanes": len(tariff.lanes)}
            print(f"✓ Maritime Ontario: {len(tariff.lanes)} lanes loaded")
        else:
            print(f"✗ Maritime Ontario file not found: {TARIFF_FILES['Maritime Ontario']}")
        
        # Ingest Groupe Guilbault
        if TARIFF_FILES["Groupe Guilbault"].exists():
            print(f"\nIngesting Groupe Guilbault tariff from {TARIFF_FILES['Groupe Guilbault']}...")
            tariff = ingest_guilbault_tariff(str(TARIFF_FILES["Groupe Guilbault"]), db)
            results["Groupe Guilbault"] = {"id": str(tariff.id), "lanes": len(tariff.lanes)}
            print(f"✓ Groupe Guilbault: {len(tariff.lanes)} lanes loaded")
        else:
            print(f"✗ Groupe Guilbault file not found: {TARIFF_FILES['Groupe Guilbault']}")
        
        # Ingest CFF
        if TARIFF_FILES["CFF"].exists():
            print(f"\nIngesting CFF tariff from {TARIFF_FILES['CFF']}...")
            tariff = ingest_cff_tariff(str(TARIFF_FILES["CFF"]), db)
            results["CFF"] = {"id": str(tariff.id), "lanes": len(tariff.lanes)}
            print(f"✓ CFF: {len(tariff.lanes)} lanes loaded")
        else:
            print(f"✗ CFF file not found: {TARIFF_FILES['CFF']}")
        
        print("\n" + "="*50)
        print("Ingestion Summary:")
        print("="*50)
        for carrier, info in results.items():
            print(f"{carrier}: {info['lanes']} lanes (ID: {info['id']})")
        
        print("\n✓ All tariffs ingested successfully!")
        
    except Exception as e:
        print(f"\n✗ Error ingesting tariffs: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    ingest_all_tariffs()

