# Setup Instructions

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL database
- OpenAI API key (optional, for report generation)

## Backend Setup

1. Navigate to backend directory:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file in `backend/` directory:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/3pl_audit
OPENAI_API_KEY=your_openai_api_key_here
SECRET_KEY=your_secret_key_here
UPLOAD_DIR=./uploads
ENVIRONMENT=development
```

5. Create PostgreSQL database:
```sql
CREATE DATABASE 3pl_audit;
```

6. Run migrations:
```bash
alembic upgrade head
```

7. Start the server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Creating Your First Customer

You can create a customer via the API:

```bash
curl -X POST http://localhost:8000/api/customers/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Global Industrial", "contact_name": "Nick", "contact_email": "nick@example.com"}'
```

Or use the UI: Navigate to "New Audit" and create a customer if needed.

## Usage Workflow

1. **Create a Customer** (if not exists)
2. **Create an Audit Run**: Select customer, name, and period
3. **Upload Files**: Upload XLSX or CSV files with shipment data
4. **Review Mappings**: System infers column mappings; review and adjust if needed
5. **Process**: System normalizes data and runs audit
6. **View Results**: See summary, lane statistics, and exceptions
7. **Generate Reports**: Create executive summary, download Excel/PDF

## File Format

The system expects files with columns that can be mapped to:
- Weight (wgt, weight, invwgt, etc.)
- Pallets (pcs, pallets, invpcs, etc.)
- Charge (price, amount, trfamt, etc.)
- Origin/Destination (origin_city, dest_city, etc.)
- Shipment reference (ref, pro, shipment_id, etc.)

See `backend/app/services/file_parser.py` for full list of recognized patterns.

