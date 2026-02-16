# 3PL Links Freight Audit Platform - Admin Guide

## Administration & Technical Operations

This guide covers platform administration, configuration, maintenance, and troubleshooting for system administrators.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Installation & Setup](#installation--setup)
3. [Environment Configuration](#environment-configuration)
4. [Database Management](#database-management)
5. [Tariff Management](#tariff-management)
6. [Adding New Carriers](#adding-new-carriers)
7. [User Management](#user-management)
8. [Monitoring & Logging](#monitoring--logging)
9. [Backup & Restore](#backup--restore)
10. [Security Hardening](#security-hardening)
11. [Performance Optimization](#performance-optimization)
12. [Troubleshooting](#troubleshooting)

---

## System Architecture

### Technology Stack

**Backend:**
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15+ with PostGIS extension
- **ORM**: SQLAlchemy 2.x
- **API**: RESTful JSON API

**Frontend:**
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 7
- **Router**: React Router v6
- **Charts**: Recharts
- **Icons**: Lucide React

**Infrastructure:**
- **Web Server**: Uvicorn (ASGI)
- **Reverse Proxy**: Nginx (recommended for production)
- **SSL/TLS**: Let's Encrypt (recommended)

### Directory Structure

```
3pl-dash/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── main.py       # Application entry point
│   │   ├── models.py     # SQLAlchemy models
│   │   ├── schemas.py    # Pydantic schemas
│   │   ├── database.py   # DB connection
│   │   └── routers/      # API endpoints
│   ├── requirements.txt  # Python dependencies
│   ├── .env.example      # Environment template
│   └── alembic/          # Database migrations
├── frontend/             # React application
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── api/          # API client
│   │   └── types/        # TypeScript types
│   ├── package.json      # Node dependencies
│   └── vite.config.ts    # Vite configuration
├── docs/                 # Documentation
├── sample-data/          # Test data files
└── config/               # Configuration files
```

---

## Installation & Setup

### Prerequisites

- **Node.js**: v18+ (v25.6.1 recommended)
- **Python**: 3.11+
- **PostgreSQL**: 15+ with PostGIS
- **npm** or **yarn** package manager

### Quick Start

See `SETUP.md` for detailed installation instructions.

**Backend:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Production Build:**
```bash
cd frontend
npm run build
# Serve the dist/ folder with Nginx
```

---

## Environment Configuration

### Backend Environment Variables

Edit `backend/.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/freight_audit
# For PostGIS: postgresql://user:password@localhost:5432/freight_audit

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false  # Set to false in production

# CORS (adjust for your frontend domain)
CORS_ORIGINS=["http://localhost:5173", "https://yourdomain.com"]

# Security
SECRET_KEY=your-secret-key-here  # Generate with: openssl rand -hex 32
ALLOWED_HOSTS=["localhost", "yourdomain.com"]

# File Upload
MAX_UPLOAD_SIZE_MB=50
UPLOAD_DIR=./uploads

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FILE=./logs/app.log

# Optional: External Services
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USER=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
```

### Frontend Environment Variables

Create `frontend/.env.production`:

```bash
VITE_API_URL=https://api.yourdomain.com
# For development: http://localhost:8000
```

### Security Best Practices

- **Never commit `.env` files** to version control
- **Use strong SECRET_KEY** (32+ random characters)
- **Enable HTTPS** in production (use Let's Encrypt)
- **Restrict CORS_ORIGINS** to your actual domains
- **Use environment-specific configs** (dev, staging, prod)

---

## Database Management

### Initial Setup

```bash
# Create database
createdb freight_audit

# Enable PostGIS (for geographic queries)
psql freight_audit -c "CREATE EXTENSION IF NOT EXISTS postgis;"

# Run migrations
cd backend
alembic upgrade head
```

### Database Schema

**Core Tables:**
- `audit_runs`: Audit metadata
- `shipments`: Individual shipment records
- `tariffs`: Carrier rate tables
- `zones`: Postal code to zone mappings
- `exceptions`: Audit exceptions/issues

**Relationships:**
- `audit_runs` → `shipments` (one-to-many)
- `tariffs` → `zones` (one-to-many)
- `shipments` → `exceptions` (one-to-many)

### Running Migrations

```bash
cd backend

# Generate new migration (after model changes)
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

### Database Maintenance

**Vacuum & Analyze (recommended weekly):**
```sql
VACUUM ANALYZE;
```

**Check Database Size:**
```sql
SELECT pg_size_pretty(pg_database_size('freight_audit'));
```

**Largest Tables:**
```sql
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Tariff Management

### Tariff Structure

Each tariff defines:
- **Carrier**: FedEx, UPS, Purolator, etc.
- **Service Level**: Ground, Express, Priority, etc.
- **Zone Mappings**: Postal codes → zone IDs
- **Rate Tables**: Weight breaks → price per zone

### Uploading Tariffs

**See**: `INGEST_TARIFFS.md` and `QUICK_START_TARIFFS.md` for detailed instructions.

**Via API:**
```bash
curl -X POST http://localhost:8000/tariffs/upload \
  -F "file=@tariff.csv" \
  -F "carrier=FedEx" \
  -F "service_level=Ground"
```

**Expected CSV Format:**
```csv
origin_zone,dest_zone,weight_min,weight_max,rate
1,1,0,5,12.50
1,1,5,10,18.75
1,2,0,5,15.00
...
```

### Zone Mappings

**Upload Zone CSV:**
```csv
postal_code,zone_id
M5H,1
M4W,1
V6B,2
...
```

**API Endpoint:**
```bash
POST /zones/upload
```

### Validating Tariffs

```bash
# List all tariffs
curl http://localhost:8000/tariffs/

# Get specific tariff
curl http://localhost:8000/tariffs/{tariff_id}

# Test rate lookup
curl -X POST http://localhost:8000/tariffs/rate-lookup \
  -H "Content-Type: application/json" \
  -d '{
    "carrier": "FedEx",
    "service_level": "Ground",
    "origin_postal": "M5H2N2",
    "dest_postal": "V6B1A1",
    "weight": 15.5
  }'
```

---

## Adding New Carriers

### Backend Steps

1. **Add carrier to enum** (if using enum validation):
   - Edit `backend/app/models.py`
   - Add carrier name to `CarrierEnum`

2. **Upload tariff data**:
   - See [Tariff Management](#tariff-management)

3. **Add zone mappings**:
   - Map postal codes to carrier's zone system

4. **Test rating**:
   - Use rate lookup API to verify correct calculations

### Frontend Steps

1. **Update carrier dropdown** (if hardcoded):
   - Edit `frontend/src/pages/NewAuditWizard.tsx`
   - Add carrier to dropdown options

2. **Add carrier logo** (optional):
   - Place logo in `frontend/public/carriers/`
   - Update display logic

### Carrier-Specific Configuration

Some carriers may require custom logic:

**Example: FedEx Dimensional Weight**
```python
# backend/app/services/rating.py
def calculate_billable_weight(weight, dimensions):
    if carrier == "FedEx":
        dim_weight = (length * width * height) / 139
        return max(weight, dim_weight)
    return weight
```

---

## User Management

### Authentication (Future Enhancement)

Currently, the platform operates without authentication. To add user management:

1. **Install Auth Library**:
   ```bash
   pip install python-jose[cryptography] passlib[bcrypt]
   ```

2. **Add User Model**:
   - Create `User` table (username, hashed_password, role)
   - Add JWT token generation/validation

3. **Protect Endpoints**:
   ```python
   from fastapi import Depends, HTTPException, status
   from fastapi.security import OAuth2PasswordBearer

   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

   @app.get("/audits/")
   async def get_audits(token: str = Depends(oauth2_scheme)):
       # Validate token
       ...
   ```

4. **Frontend Login**:
   - Add login page
   - Store JWT in localStorage
   - Include token in API requests

---

## Monitoring & Logging

### Application Logs

**Backend Logs:**
- **Location**: `backend/logs/app.log` (configure in `.env`)
- **Format**: JSON structured logging (timestamp, level, message, context)

**View Logs:**
```bash
tail -f backend/logs/app.log

# Filter by error level
grep "ERROR" backend/logs/app.log

# Last 100 errors
grep "ERROR" backend/logs/app.log | tail -100
```

### Database Logs

**PostgreSQL Query Logs:**
Edit `postgresql.conf`:
```conf
log_statement = 'mod'  # Log all data-modifying queries
log_duration = on
log_min_duration_statement = 1000  # Log queries >1 second
```

### Health Checks

**Backend Health Endpoint:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "uptime_seconds": 12345
}
```

### Performance Metrics

**Monitor:**
- API response times (aim for <500ms p95)
- Database query times (slow query log)
- Upload processing times
- Memory usage (should stay <2GB for typical loads)

**Tools:**
- **Prometheus + Grafana**: Metrics collection & dashboards
- **Sentry**: Error tracking
- **DataDog/New Relic**: APM (Application Performance Monitoring)

---

## Backup & Restore

### Database Backup

**Automated Daily Backup** (cron job):
```bash
#!/bin/bash
# /etc/cron.daily/backup-freight-audit

BACKUP_DIR=/backups/freight-audit
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE=$BACKUP_DIR/freight_audit_$DATE.sql.gz

pg_dump freight_audit | gzip > $BACKUP_FILE

# Keep last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
```

**Manual Backup:**
```bash
pg_dump freight_audit > backup_$(date +%Y%m%d).sql
```

**Backup with Compression:**
```bash
pg_dump freight_audit | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore from Backup

```bash
# Drop existing database (CAUTION!)
dropdb freight_audit

# Create fresh database
createdb freight_audit

# Restore from backup
gunzip < backup_20240215.sql.gz | psql freight_audit
# OR for uncompressed:
psql freight_audit < backup_20240215.sql
```

### File Backup

**Uploaded Files:**
- Location: `backend/uploads/` (or path in `.env`)
- Backup method: rsync to remote storage

```bash
rsync -avz --delete backend/uploads/ backup-server:/backups/uploads/
```

### Disaster Recovery Plan

1. **Daily automated database backups** (retained 30 days)
2. **Weekly full system snapshots** (retained 12 weeks)
3. **Off-site backup replication** (AWS S3, Google Cloud Storage)
4. **Test restore procedure monthly** (verify backup integrity)

---

## Security Hardening

### Production Checklist

- [ ] **HTTPS enabled** (Let's Encrypt SSL certificate)
- [ ] **Firewall configured** (only ports 80, 443 open)
- [ ] **Database not exposed** (localhost only)
- [ ] **Strong passwords** (database, admin accounts)
- [ ] **CORS restricted** (only whitelisted domains)
- [ ] **File upload limits** (size + type validation)
- [ ] **SQL injection prevention** (use ORM, parameterized queries)
- [ ] **XSS prevention** (sanitize user input)
- [ ] **CSRF protection** (if using cookies for auth)
- [ ] **Rate limiting** (prevent abuse)
- [ ] **Regular updates** (dependencies, OS patches)

### Recommended Security Headers

**Nginx Configuration:**
```nginx
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "no-referrer-when-downgrade" always;
add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
```

### Security Scanning

```bash
# Python dependency vulnerabilities
pip install safety
safety check

# Node dependency vulnerabilities
npm audit

# Fix auto-fixable issues
npm audit fix
```

---

## Performance Optimization

### Database Indexes

**Add indexes on frequently queried columns:**
```sql
CREATE INDEX idx_shipments_audit_run_id ON shipments(audit_run_id);
CREATE INDEX idx_shipments_origin ON shipments(origin_postal);
CREATE INDEX idx_shipments_destination ON shipments(destination_postal);
CREATE INDEX idx_tariffs_carrier_service ON tariffs(carrier, service_level);
```

### Query Optimization

**Use EXPLAIN ANALYZE:**
```sql
EXPLAIN ANALYZE
SELECT * FROM shipments WHERE audit_run_id = 123;
```

**Avoid N+1 queries** (use joins or eager loading):
```python
# Bad: N+1 query
audits = session.query(AuditRun).all()
for audit in audits:
    shipments = audit.shipments  # Separate query each time

# Good: Eager loading
audits = session.query(AuditRun).options(
    joinedload(AuditRun.shipments)
).all()
```

### Caching

**Add Redis for frequently accessed data:**
```python
import redis
r = redis.Redis(host='localhost', port=6379, db=0)

# Cache tariff lookups
def get_tariff_rate(carrier, service, weight):
    cache_key = f"tariff:{carrier}:{service}:{weight}"
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    rate = calculate_rate(carrier, service, weight)
    r.setex(cache_key, 3600, json.dumps(rate))  # 1 hour TTL
    return rate
```

### Frontend Optimization

- **Code splitting**: Lazy load pages
- **Image optimization**: Compress logos, use SVG when possible
- **Bundle analysis**: Use `npm run build -- --report`
- **CDN**: Serve static assets from CDN

---

## Troubleshooting

### Backend Won't Start

**Error: "ModuleNotFoundError"**
```bash
# Activate virtual environment
source backend/venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

**Error: "Database connection failed"**
- Check PostgreSQL is running: `pg_isready`
- Verify DATABASE_URL in `.env`
- Check firewall/network settings

### Frontend Build Errors

**TypeScript errors:**
```bash
cd frontend
npm run lint
# Fix errors manually or:
npm run build -- --mode development
```

**Missing dependencies:**
```bash
rm -rf node_modules package-lock.json
npm install
```

### Slow Queries

**Identify slow queries:**
```sql
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Add missing indexes** (see [Performance Optimization](#performance-optimization))

### Upload Failures

**File too large:**
- Check `MAX_UPLOAD_SIZE_MB` in `.env`
- Nginx: Increase `client_max_body_size`

**Invalid CSV format:**
- Verify column names match exactly
- Check for special characters, encoding issues (should be UTF-8)

### Memory Issues

**Backend consuming too much memory:**
- Check for memory leaks (unclosed DB sessions)
- Add pagination for large queries
- Increase server RAM or add swap space

---

## Advanced Topics

### Horizontal Scaling

**Load Balancing with Nginx:**
```nginx
upstream backend {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    location / {
        proxy_pass http://backend;
    }
}
```

**Run multiple backend instances:**
```bash
uvicorn app.main:app --port 8001 &
uvicorn app.main:app --port 8002 &
uvicorn app.main:app --port 8003 &
```

### Docker Deployment

See `docker-compose.yml` (if available) or create:

```yaml
version: '3.8'
services:
  db:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_DB: freight_audit
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secure-password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://admin:secure-password@db:5432/freight_audit

  frontend:
    build: ./frontend
    ports:
      - "80:80"

volumes:
  postgres_data:
```

---

## Support & Resources

- **Documentation**: See `README.md`, `SETUP.md`, `TARIFF_RATING.md`
- **Sample Data**: `sample-data/` folder
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Technical Support**: admin@3pllinks.com

For user-facing documentation, see `USER_GUIDE.md`.
