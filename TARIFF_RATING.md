# Tariff-Based Re-Rating System

## Overview

The platform now supports tariff-based re-rating using 3PL Links 2025 rate sheets. This allows you to compare actual charges against what shipments would cost under the 3PL Links FAK programs.

## Supported Carriers & Tariff Types

### 1. APPS - Skid Spot Tariff
- **File**: `APPS FAK Skid Rates 2025.xlsx`
- **Type**: Skid Spot
- **Origin**: Scarborough (SCARB)
- **Logic**: Flat charge per number of skid spots
- **Weight Cap**: 2,000 lb per skid spot (enforced automatically)

### 2. Rosedale - CWT Tariff
- **File**: `Rosedale Ex Toronto 2025 10lbs cwt.xlsx`
- **Type**: CWT (Hundredweight)
- **Origin**: Scarborough (SCARB)
- **Logic**: Rate per CWT with weight breaks + minimum charge

### 3. Maritime Ontario - CWT Tariff
- **File**: `MO ex TOR 10lbs cwt Maritimes 2025.xlsx`
- **Type**: CWT
- **Origin**: Scarborough (SCARB)
- **Logic**: CWT-based with min charge

### 4. Groupe Guilbault - CWT Tariff
- **File**: `Groupe Guilbault exTOR 15cwt 2025.xlsx`
- **Type**: CWT
- **Origin**: Scarborough (SCARB)
- **Logic**: CWT-based with multiple weight breaks

### 5. CFF (Safety Express) - CWT Tariff
- **File**: `CFF ex CGY 10lbs cwt to Western Canada Safety Express 2025.xlsx`
- **Type**: CWT
- **Origin**: Calgary (CGY)
- **Logic**: CWT-based for Western Canada lanes

## How It Works

### 1. Ingest Tariff Files

Upload tariff XLSX files via the API:

```bash
POST /api/tariffs/ingest?carrier_name=APPS
Content-Type: multipart/form-data
```

The system will:
- Parse the XLSX file
- Extract lane data (destination city/province)
- Store weight breaks or spot charges
- Create tariff records in the database

### 2. Re-Rate Shipments

After uploading shipment data and running the initial audit, trigger re-rating:

```bash
POST /api/audits/{audit_run_id}/rerate
```

This will:
- For each shipment, calculate expected charges for all applicable carriers
- Find the best carrier (lowest charge)
- Calculate savings vs actual charge
- Update `audit_results` with:
  - `expected_charge_per_carrier`: JSON mapping carrier → charge
  - `best_carrier`: Carrier with lowest charge
  - `best_charge`: Lowest expected charge
  - `savings_vs_actual`: Actual charge - best charge

### 3. View Results

The audit detail view shows:
- Total potential savings across all shipments
- Lane-level savings breakdown
- Best carrier recommendations per shipment

## Rating Logic

### CWT Tariffs

```python
# Calculate CWT (hundredweight)
cwt = ceil(weight / 100)

# Find appropriate weight break
# Apply rate per CWT
linehaul = cwt * rate_per_cwt

# Apply minimum charge
charge = max(linehaul, min_charge)
```

**Weight Selection**: Uses `dim_weight` if available, otherwise `weight`.

### Skid Spot Tariffs (APPS)

```python
# Calculate number of spots (pallets)
num_spots = ceil(pallets)

# Validate weight cap (2,000 lb per spot)
if weight > 2000 * num_spots:
    return None  # Invalid for APPS

# Lookup charge for that number of spots
charge = spot_charge_table[num_spots]
```

## Database Schema

### New Tables

- **tariffs**: Carrier tariff definitions
- **tariff_lanes**: Destination mappings (city/province → tariff)
- **tariff_breaks**: Weight breaks or spot charges

### Updated Tables

- **audit_results**: Added fields for re-rating results:
  - `expected_charge_per_carrier` (JSONB)
  - `best_carrier` (VARCHAR)
  - `best_charge` (NUMERIC)
  - `savings_vs_actual` (NUMERIC)

## API Endpoints

### Tariff Management

- `POST /api/tariffs/ingest?carrier_name={name}` - Upload and parse tariff file
- `GET /api/tariffs/` - List all tariffs
- `GET /api/tariffs/{id}` - Get specific tariff

### Re-Rating

- `POST /api/audits/{id}/rerate` - Re-rate all shipments in audit run
- Optional query param: `tariff_ids` - Limit to specific tariffs

## Frontend Integration

The audit detail view includes:
- **Re-Rating Section**: Button to trigger re-rating
- **Savings Display**: Shows potential savings in lane statistics
- **Best Carrier Info**: Displays recommended carrier per lane

## Example Workflow

1. **Ingest Tariffs**:
   ```bash
   curl -X POST "http://localhost:8000/api/tariffs/ingest?carrier_name=APPS" \
     -F "file=@APPS FAK Skid Rates 2025.xlsx"
   ```

2. **Upload Shipment Data**: Use the normal audit workflow

3. **Run Initial Audit**: `POST /api/audits/{id}/run`

4. **Re-Rate with Tariffs**: `POST /api/audits/{id}/rerate`

5. **View Results**: Check the audit detail view for savings breakdown

6. **Generate Report**: Executive summary now includes tariff-based savings

## Notes

- Tariffs are matched by origin DC and destination city/province
- If exact city match not found, falls back to province-only match
- APPS automatically rejects shipments exceeding 2,000 lb per skid
- CWT calculations use dim weight when available (more accurate for rating)
- All charges are stored as Decimal for precision

## Future Enhancements

- Support for fuel surcharges and accessorials
- Multiple tariff versions (effective dates)
- Postal code-based matching
- Zone-based rating
- Custom tariff uploads for other carriers

