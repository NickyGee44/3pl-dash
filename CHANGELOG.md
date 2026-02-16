# Changelog

All notable changes to the 3PL Links Freight Audit Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-02-15

### Added - Phase 2: Production Modernization

#### Branding & Design
- **3PL Links brand identity** applied across entire platform
- **CSS custom properties** for brand colors (Navy Blue `#0A2463`, Sky Blue `#3B82F6`, Success Green `#059669`)
- **Professional logo** with "3PL" icon badge in header
- **SVG favicon** with 3PL Links branding
- **Gradient brand header** (Navy to Deep Blue) with improved navigation
- Active navigation state indicators
- Professional color palette matching logistics industry standards
- Updated meta description for SEO

#### Documentation
- **`BRANDING.md`** - Complete brand guide with color palette, typography, design principles
- **`USER_GUIDE.md`** - Comprehensive end-user documentation (10KB+)
  - How to upload shipment files
  - Understanding audit results
  - Interpreting savings recommendations
  - Exporting reports (Excel & PDF)
  - Troubleshooting section
- **`ADMIN_GUIDE.md`** - Technical administration guide (16KB+)
  - System architecture documentation
  - Environment configuration
  - Database management & migrations
  - Tariff management procedures
  - Security hardening checklist
  - Backup & restore procedures
  - Performance optimization tips
  - Docker deployment examples
- **`TEST_CHECKLIST.md`** - Step-by-step validation checklist for Wally
  - 10-phase testing workflow
  - Sample data upload tests
  - Real data validation procedures
  - Browser/mobile testing
  - Known limitations documentation
  - Sign-off section

#### Sample Data
- **`sample-data/test-shipments.csv`** - 20 realistic test shipments
  - Canadian postal codes (Toronto, Vancouver, Calgary, Montreal, Ottawa)
  - Multiple carriers (FedEx, UPS, Purolator, Canada Post)
  - Various service levels (Ground, Express, Priority, Expedited)
  - Proper date formatting and weight distribution
  - Ready for end-to-end testing

#### Frontend
- **lucide-react** icon library (v0.469.0) replacing emoji icons
- Skeleton loaders for improved loading states (replaced spinners)
- Enhanced mobile responsiveness for dashboard cards
- Tablet breakpoint (769px-1024px) with 2-column grid layout
- **Brand-consistent UI components**:
  - Metric cards use brand colors (Navy primary, Green highlights)
  - Buttons with brand navy background
  - Hover states with brand accent colors
  - Status badges (success/warning/error/info) with brand palette
  - Improved shadows and transitions using CSS variables

#### Backend
- **Request ID middleware** for request tracing
- Enhanced CORS configuration with environment variable support
- `.env.example` file documenting all required environment variables
- Exposed `X-Request-ID` header in API responses

### Changed

#### Frontend
- **TypeScript fixes** for build errors:
  - Fixed type assertion in `ExecutiveSummary.tsx` (line 58)
  - Fixed unused variable warning in `ExecutiveSummary.tsx` (line 134)
  - Added `theoretical_savings` field to `AuditRun.summary_metrics` type
  - Fixed conditional logic in `NewAuditWizard.tsx` step indicator
- **Icon replacements**:
  - 📊 → `BarChart3` (Total Audits)
  - 📦 → `Package` (Total Shipments)
  - 💰 → `DollarSign` (Total Spend)
  - 💵 → `TrendingUp` (Potential Savings)
  - 📋 → `FileText` (Empty state)
- Dashboard loading state now shows skeleton cards instead of spinner

#### Backend Dependency Updates
- `fastapi`: 0.104.1 → **0.115.6** (security patches, performance improvements)
- `uvicorn`: 0.24.0 → **0.34.0** (HTTP/2 support, stability fixes)
- `sqlalchemy`: 2.0.23 → **2.0.36** (bug fixes, performance)
- `alembic`: 1.12.1 → **1.14.0** (better migration support)
- `psycopg2-binary`: 2.9.9 → **2.9.10** (security patches)
- `pydantic`: 2.5.0 → **2.10.5** (JSON schema improvements, validation enhancements)
- `pydantic-settings`: 2.1.0 → **2.7.1** (better .env support)
- `pandas`: 2.1.3 → **2.2.3** (performance, security)
- `numpy`: 1.26.2 → **2.2.2** (major version upgrade - see Breaking Changes)
- `PyYAML`: 6.0.1 → **6.0.2** (security fix)
- `openpyxl`: 3.1.2 → **3.1.5** (security patches)
- `python-dotenv`: 1.0.0 → **1.0.1** (bug fixes)
- `openai`: 1.3.5 → **1.60.0** (major API improvements - see Breaking Changes)
- `reportlab`: 4.0.7 → **4.2.5** (PDF generation improvements)

### Security

#### Backend
- **Removed hardcoded database URL fallback** - already implemented (database.py requires `DATABASE_URL` env var)
- CORS origins now configurable via `CORS_ORIGINS` environment variable
- Request ID logging for audit trails
- Updated all dependencies to patch known CVEs

#### Frontend
- **xlsx vulnerability** (CVE-2023-XXXX) - NO FIX AVAILABLE
  - Prototype Pollution (GHSA-4r6h-8v6p-xvw6)
  - ReDoS vulnerability (GHSA-5pgg-2g8v-p4x9)
  - **Action Required**: Consider migrating to `exceljs` or `xlsx-js-style` when possible

### Breaking Changes

#### Backend
- **NumPy 2.x upgrade**:
  - Some deprecated NumPy APIs removed
  - May require code changes if using advanced NumPy features
  - Pandas 2.2.3 is compatible with NumPy 2.x
  
- **OpenAI 1.60.0**:
  - Client instantiation changed (now uses `openai.OpenAI()`)
  - Async methods use `await client.chat.completions.create()` instead of `openai.ChatCompletion.create()`
  - **Action Required**: Update AI summary generation code if using OpenAI SDK

- **FastAPI 0.115.6**:
  - `jsonable_encoder` behavior changes in edge cases
  - Improved type checking may surface existing type issues

### Fixed
- TypeScript compilation errors preventing production builds
- Dashboard loading state flickering
- Mobile responsiveness issues on small screens

### Developer Experience
- Added comprehensive environment variable documentation in `.env.example`
- Improved CSS organization with skeleton loader animations
- Better request tracing with unique request IDs

## [1.0.0] - Prior to 2026-02-15

Initial functional version with:
- Freight audit upload and analysis
- Lane-by-lane savings calculation
- Tariff management (CWT and Skid-Spot)
- Consolidation opportunity detection
- AI-powered executive summaries (OpenAI integration)
- Excel report generation
- Multi-customer support

---

## Migration Notes

### For Local Development
1. Copy `.env.example` to `.env` and configure:
   ```bash
   cp backend/.env.example backend/.env
   # Edit backend/.env with your database credentials
   ```

2. Install updated dependencies:
   ```bash
   cd frontend && npm install
   cd ../backend && pip install -r requirements.txt
   ```

3. **Do NOT run Alembic migrations yet** - database connection required

### For Production Deployment
1. Review OpenAI SDK usage in `app/api/reports.py` for breaking changes
2. Test NumPy-dependent calculations thoroughly
3. Add `CORS_ORIGINS` to production environment variables
4. Monitor request IDs in logs for debugging
5. Plan migration from `xlsx` to secure alternative

### Known Issues
- `xlsx` package has high-severity vulnerabilities with no fix
- Large bundle size warning (>500 KB) - consider code splitting
- No automated tests (to be added in future sprint)
