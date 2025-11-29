# 3PL Links Freight Audit Platform

A web platform for freight audit and analytics that normalizes shipment data from multiple sources, computes key metrics, identifies anomalies, and generates executive reports.

## Architecture

- **Backend**: Python 3 + FastAPI
- **Database**: PostgreSQL
- **Frontend**: React + TypeScript (Vite)
- **Data Processing**: pandas
- **LLM Integration**: OpenAI API (ChatGPT)

## Project Structure

```
.
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── models/   # SQLAlchemy models
│   │   ├── schemas/  # Pydantic schemas
│   │   ├── api/      # API routers
│   │   ├── services/ # Business logic
│   │   └── db/       # Database setup
│   ├── alembic/      # Database migrations
│   ├── scripts/      # Utility scripts
│   └── requirements.txt
├── frontend/         # React application
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── api/
│   │   └── types/
│   └── package.json
├── README.md
└── SETUP.md          # Detailed setup instructions
```

## Quick Start

See [SETUP.md](SETUP.md) for detailed setup instructions.

### Backend

1. Create virtual environment and install dependencies:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Set up `.env` file (see `.env.example`)

3. Create database and run migrations:
```bash
# Create PostgreSQL database first
alembic upgrade head
```

4. Start server:
```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Key Features

### 1. Multi-File Upload & Normalization
- Accepts XLSX and CSV files
- Automatic column mapping inference
- Manual mapping override
- Normalizes to unified shipment data model

### 2. Freight Audit Engine
- Computes key metrics (total spend, cost per lb, cost per pallet)
- Lane-level analytics (origin DC × destination)
- Exception detection (zero charges, outliers, missing data)
- Theoretical best-case savings calculation

### 3. Reporting & Analytics
- Executive summary generation via ChatGPT
- Excel export with lane breakdown and exceptions
- PDF export of executive summary
- Interactive dashboard with charts and tables

### 4. Data Model
- Customers
- Audit Runs
- Source Files
- Normalized Shipments
- Audit Results (metrics and flags)
- Lane Statistics (aggregated by origin/destination)

## API Endpoints

- `GET /api/customers/` - List customers
- `POST /api/customers/` - Create customer
- `GET /api/audits/` - List audit runs
- `POST /api/audits/` - Create audit run
- `POST /api/files/{audit_run_id}/upload` - Upload files
- `GET /api/files/{file_id}/mappings` - Get column mappings
- `POST /api/files/{file_id}/normalize` - Normalize file
- `POST /api/audits/{id}/run` - Run audit
- `GET /api/reports/{id}/lanes` - Get lane statistics
- `GET /api/reports/{id}/exceptions` - Get exceptions
- `POST /api/reports/{id}/executive-summary` - Generate summary
- `GET /api/reports/{id}/excel` - Download Excel
- `GET /api/reports/{id}/pdf` - Download PDF

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `OPENAI_API_KEY`: OpenAI API key for report generation (optional)
- `UPLOAD_DIR`: Directory for uploaded files (default: `./uploads`)

## Development

The platform is designed to be extensible:
- Add new column mapping patterns in `backend/app/services/file_parser.py`
- Extend audit engine with new metrics in `backend/app/services/audit_engine.py`
- Customize LLM prompts in `backend/app/services/llm_reports.py`
- Add new UI components in `frontend/src/components/`

## License

Proprietary - 3PL Links


