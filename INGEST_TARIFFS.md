# How to Ingest Tariff Files

You have 5 Excel tariff files in the `/3PL` folder. Here are two ways to ingest them:

## Option 1: Using the Python Script (Recommended)

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Run the Ingestion Script

```bash
python scripts/ingest_all_tariffs.py
```

This will automatically:
- Find all 5 tariff files in the project root
- Parse each one according to its format
- Load them into the database
- Show a summary of lanes loaded

## Option 2: Using the API Endpoints

If the backend server is running, you can use the API:

### Start the Backend Server

```bash
cd backend
uvicorn app.main:app --reload
```

### Ingest Each File via API

```bash
# APPS
curl -X POST "http://localhost:8000/api/tariffs/ingest?carrier_name=APPS" \
  -F "file=@APPS FAK Skid Rates 2025.xlsx"

# Rosedale
curl -X POST "http://localhost:8000/api/tariffs/ingest?carrier_name=Rosedale" \
  -F "file=@Rosedale Ex Toronto 2025 10lbs cwt.xlsx"

# Maritime Ontario
curl -X POST "http://localhost:8000/api/tariffs/ingest?carrier_name=Maritime Ontario" \
  -F "file=@MO ex TOR  10lbs cwt Maritimes 2025.xlsx"

# Groupe Guilbault
curl -X POST "http://localhost:8000/api/tariffs/ingest?carrier_name=Groupe Guilbault" \
  -F "file=@Groupe Guilbault exTOR 15cwt 2025.xlsx"

# CFF
curl -X POST "http://localhost:8000/api/tariffs/ingest?carrier_name=CFF" \
  -F "file=@CFF ex CGY 10lbs cwt to Western Canada Saftey Express 2025.xlsx"
```

### Or Use a Browser/Postman

1. Navigate to `http://localhost:8000/docs` (FastAPI Swagger UI)
2. Find the `POST /api/tariffs/ingest` endpoint
3. Set `carrier_name` parameter
4. Upload the file
5. Repeat for each carrier

## Verify Tariffs Were Loaded

```bash
# List all tariffs
curl http://localhost:8000/api/tariffs/

# Or check in the database
# The script will show a summary after ingestion
```

## Expected Results

After ingestion, you should see:
- **APPS**: Skid-spot tariff with lanes for various destinations
- **Rosedale**: CWT tariff with weight breaks
- **Maritime Ontario**: CWT tariff for Maritimes destinations
- **Groupe Guilbault**: CWT tariff with multiple weight breaks
- **CFF**: CWT tariff for Western Canada from Calgary

Each tariff will have:
- Multiple lanes (destination city/province combinations)
- Weight breaks or spot charges depending on tariff type
- Minimum charges where applicable

## Troubleshooting

### File Not Found
- Make sure the Excel files are in the project root (`/3PL` folder)
- Check file names match exactly (case-sensitive)

### Database Connection Error
- Verify `.env` file has correct `DATABASE_URL`
- Ensure database is accessible

### Parsing Errors
- Check that Excel files are not corrupted
- Verify file format matches expected structure
- Check console output for specific error messages

## Next Steps

After ingesting tariffs:
1. Upload shipment data files
2. Run the audit: `POST /api/audits/{id}/run`
3. Re-rate with tariffs: `POST /api/audits/{id}/rerate`
4. View savings in the audit detail view

