# Quick Start: Ingest Your 5 Tariff Files

Your 5 Excel tariff files are ready to be loaded into the database.

## Quick Steps

### 1. Install Python Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

This installs: pandas, openpyxl, sqlalchemy, psycopg2, etc.

### 2. Run the Ingestion Script

```powershell
python scripts/ingest_all_tariffs.py
```

The script will:
- ✅ Find all 5 Excel files automatically
- ✅ Parse each one (APPS, Rosedale, Maritime Ontario, Guilbault, CFF)
- ✅ Load lanes and breaks into the database
- ✅ Show a summary of what was loaded

### Expected Output

```
Ingesting APPS tariff from G:\3PL\APPS FAK Skid Rates 2025.xlsx...
✓ APPS: 45 lanes loaded

Ingesting Rosedale tariff from G:\3PL\Rosedale Ex Toronto 2025 10lbs cwt.xlsx...
✓ Rosedale: 120 lanes loaded

Ingesting Maritime Ontario tariff from G:\3PL\MO ex TOR  10lbs cwt Maritimes 2025.xlsx...
✓ Maritime Ontario: 25 lanes loaded

Ingesting Groupe Guilbault tariff from G:\3PL\Groupe Guilbault exTOR 15cwt 2025.xlsx...
✓ Groupe Guilbault: 200 lanes loaded

Ingesting CFF tariff from G:\3PL\CFF ex CGY 10lbs cwt to Western Canada Saftey Express 2025.xlsx...
✓ CFF: 80 lanes loaded

==================================================
Ingestion Summary:
==================================================
APPS: 45 lanes (ID: ...)
Rosedale: 120 lanes (ID: ...)
Maritime Ontario: 25 lanes (ID: ...)
Groupe Guilbault: 200 lanes (ID: ...)
CFF: 80 lanes (ID: ...)

✓ All tariffs ingested successfully!
```

## Alternative: Use the API (if server is running)

If you prefer to use the web interface:

1. Start the backend: `uvicorn app.main:app --reload`
2. Go to `http://localhost:8000/docs`
3. Use the `POST /api/tariffs/ingest` endpoint for each file

## What Happens Next?

Once tariffs are loaded:
1. ✅ Upload your shipment data files
2. ✅ Run the audit
3. ✅ Click "Re-rate with Tariffs" button
4. ✅ See potential savings calculated!

## Troubleshooting

**"ModuleNotFoundError: No module named 'psycopg2'"**
→ Run: `pip install -r requirements.txt`

**"File not found"**
→ Make sure you're running from the `backend` directory
→ Verify Excel files are in `/3PL` (project root)

**"Database connection error"**
→ Check `.env` file has correct `DATABASE_URL`
→ Verify Neon database is accessible

## Files Being Ingested

- ✅ `APPS FAK Skid Rates 2025.xlsx` → Skid-spot tariff
- ✅ `Rosedale Ex Toronto 2025 10lbs cwt.xlsx` → CWT tariff
- ✅ `MO ex TOR  10lbs cwt Maritimes 2025.xlsx` → CWT tariff
- ✅ `Groupe Guilbault exTOR 15cwt 2025.xlsx` → CWT tariff
- ✅ `CFF ex CGY 10lbs cwt to Western Canada Saftey Express 2025.xlsx` → CWT tariff

All files are in the correct location! 🎉

