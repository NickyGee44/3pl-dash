## Background and Motivation
- User wants an end-to-end audit of the entire application to confirm key workflows (customer creation, audit creation, file upload, mapping, normalization, reporting) function reliably after recent bug fixes.
- Previous issues included backend startup failures, API proxy errors, and audit creation errors. We now need confidence that the system works holistically.
- Latest directive: upgrade the rating pipeline (vectorized tariff application + consolidation), generate report-ready JSON context, surface a user-facing tariff library, and add an "Ask AI" analyst panel on the audit detail page.
- New priority: dashboard operations (normalize, rate, rerate, generate reports) must complete in **seconds, not 10+ minutes**, requiring targeted performance optimization across ingestion, rating, and reporting flows.

## Key Challenges and Analysis
- **Complex workflow**: Multiple services (backend FastAPI, frontend Vite/React, PostgreSQL) must run together with proper environment variables and seed data.
- **Data dependencies**: Successful audit runs require customers, uploaded shipment files, mappings, and tariffs; missing seed data could block verification.
- **Observability**: Need clear logging and error handling to diagnose failures quickly during the audit.
- **Test coverage**: Limited automated tests currently; we must lean on manual verification + targeted scripts.
- **Performance bottlenecks**: Current audit/rerate/report steps exceed 10 minutes due to serial DB writes, repeated tariff lookups, large Excel parsing overhead, and blocking UI flows.

## High-level Task Breakdown
1. **Environment Verification**
   - Success: Backend server starts without errors, database reachable, `.env` configured; Vite dev server connects via proxy.
2. **Automated Quality Checks**
   - Success: Backend `pytest` (if available) and linting pass; frontend `npm run lint` passes; document gaps if tests absent.
3. **Backend API Smoke Tests**
   - Success: Use HTTP client or scripts to hit `/health`, `/api/customers`, `/api/audits` (POST/GET), file upload, and audit run endpoints; responses succeed.
4. **Frontend Workflow Validation**
   - Success: In browser, complete the New Audit wizard with sample files through processing, reaching audit detail view without errors.
5. **Tariff & Report Features**
   - Success: Execute tariff ingestion script or API, trigger rerate/report generation, confirm no crashes and outputs stored/downloadable.
6. **Dashboard UX & Interactions**
   - Success: New Audit wizard, Audit Detail view, and Tariff Library provide clear progress indication, prominent primary actions (Run Audit, Re-rate, Generate Summary, Ask AI), and intuitive layout for power users.
7. **Documentation & Issue Log**
   - Success: Record findings, open issues, and remediation recommendations; confirm user knows current status and next steps.
8. **Performance Optimization Plan (new)**
   - Success: Identify bottlenecks, quantify current timings, and define actionable improvements to bring total audit workflow (upload → normalize → rate → rerate → report) under 60 seconds for typical GI datasets.

### Performance Optimization Plan
1. **Baseline & Telemetry**
   - Add timing logs around major stages (file parsing, normalization, DB bulk insert, rating, consolidation, report generation).
   - Capture dataset sizes (rows, MB) to contextualize timings.
   - Success criteria: Each stage reports duration in logs and surfaces aggregate timing in audit summary for verification.

2. **File Parsing & Normalization**
   - Profile pandas reads; ensure `read_excel` uses `engine="openpyxl"` with `dtype` hints to avoid expensive inference.
   - Switch to streaming/chunked normalization to avoid writing row-by-row via ORM; leverage `COPY` or `executemany` bulk insert.
   - Success: Parsing + normalization for ~10k rows completes <15s and uses <500MB RAM.

3. **Rating & Consolidation Engine**
   - Ensure tariff data cached in memory once per audit run (already partially in place); verify lookups happen via pandas merges instead of per-row loops.
   - Vectorize consolidation grouping and savings calculations; push heavy computations into SQL where feasible (materialized views or temp tables).
   - Success: Re-rating 10k shipments completes <10s and CPU usage is bounded.

4. **Database I/O & Transactions**
   - Batch insert audit results rather than individual commit per shipment.
   - Add indexes on frequently filtered columns (`shipments.audit_run_id`, `audit_results.shipment_id`, `lane_stats.audit_run_id`).
   - Success: DB write phases show >5x throughput improvement and no long transactions blocking other operations.

5. **Report Generation & Exports**
   - Precompute report context and store JSON on audit run to avoid recalculating for each download.
   - Generate Excel/PDF asynchronously (background task or Celery) if processing >5s, with progress updates.
   - Success: Report downloads ready within 5s or user receives progress state with completion notification.

6. **Frontend UX / Async Handling**
   - Replace blocking button states with async job tracking (audit run status, rerate job, report job).
   - Poll backend job status to update progress bars, avoiding long-lived HTTP requests.
   - Success: UI remains responsive; user sees stage-by-stage completion in under a minute.

## Project Status Board
- [ ] Environment verification — backend now launches after OpenAI/Base fixes but POST `/api/customers` fails with `psycopg2 OperationalError: SSL connection has been closed unexpectedly`; Vite dev server reports proxy AggregateErrors because API gateway unreachable
- [ ] Automated quality checks
- [ ] Backend API smoke tests
- [ ] Frontend workflow validation
- [ ] Tariff & report features
- [ ] Documentation & issue log
- [x] Vectorized rating engine using cached tariffs
- [x] Same-day/same-destination consolidation pass with savings outputs
- [x] Report context JSON + PPT/AI integration wiring
- [x] Tariff library UI refresh (list/upload/categorize)
- [x] Audit detail "Ask this analysis" AI panel + backend endpoint
- [x] Performance optimization — baseline telemetry instrumentation (timing logs for upload, normalization, audit run, rerate, and report generation stages)

## Current Status / Progress Tracking
- Planner initialized project-wide audit plan (current step).
- Executor attempted Task 1 (environment verification):
  - Reviewed backend terminal logs (`terminals/11.txt`). After recent code changes, `uvicorn` boots successfully, but DB writes fail immediately with SSL connection drops when creating customers. GET `/api/audits` works, indicating partial connectivity.
  - Frontend dev server (`terminals/8.txt`) starts, but repeated Vite proxy `AggregateError` entries show it cannot reach `/api/audits` and `/api/customers`, likely because the backend request fails or port inaccessible.
  - No `.env` file present; backend relies on external `DATABASE_URL` env (unknown). Need confirmation of Postgres host/SSL requirements.
- Executor Task 1 follow-up:
  - Confirmed Neon connection string; attempted to restart backend but tool limitations prevented persisting env/commands. User later restarted services manually.
  - Addressed CSS readability issue (audit tables now force dark text) and backend normalization failure (JSONB NaN writes). Still need live verification after backend restart.
- Executor Task (vectorized rating & consolidation) — completed:
  - Added pandas-driven rating pipeline + consolidation engine feeding `summary_metrics` and `report_context`.
  - Surfaced savings + consolidation insights in UI (ExecutiveSummary + new cards), Tariff Library page, and Ask-AI workflow powered by backend context endpoint.
- Executor Task (config wiring) — completed:
  - Created `config/column_mappings.yaml` plus loader utilities so shipment/tariff ingest derives mappings + origin/DC metadata declaratively.
  - Updated normalization flow to merge config defaults with user mappings (per-sheet origin detection) and tuned tariff ingestion to honor config-defined columns/breaks.
  - Documented the process in `docs/data_mapping.md`.
- Executor Task (column alias expansion + normalization fixes) — completed:
- Executor Task (performance telemetry) — completed:
  - Added timing instrumentation + structured logging for file uploads and normalization endpoints (records per-file and total durations, returns timing data to frontend).
  - `run_audit` and `rerate_audit` now capture stage durations (load, compute, lane stats, rerate, DB updates) and store them inside `summary_metrics["timings"]` while logging to IRS.
  - Executive summary generation and Excel/PDF export services now log total runtime per audit to help spot slow spots later.
  - Logs provide baseline data for future optimization steps (parsing improvements, DB batching, async reports).
- Executor Task (normalization throughput) — completed:
  - Reworked the `/files/{file_id}/normalize` endpoint to batch all normalized shipment dicts and use `bulk_insert_mappings` with 1k-row chunks instead of inserting one ORM object at a time.
  - Shipments per file now hit the DB in large batches and commit once, which removes the primary Python-level bottleneck during ingestion.
  - The response still reports timing metrics so we can compare before/after ingest performance.
  - Expanded `COLUMN_PATTERNS` in `file_parser.py` with comprehensive aliases for all origin/destination variants (SHCITY, CPROV, CNPCITY, etc.).
  - Added text normalization (uppercase + strip) in `normalizer.py` for city/province fields to ensure consistent tariff lane matching.
  - Updated `tariff_ingestion.py` to normalize city/province to uppercase when storing lanes.
  - Added `tariff_match_status` and `tariff_match_notes` fields to `AuditResult` model to track lane matching without overwriting destination fields.
  - Rating pipeline now sets match status ("MATCHED", "NO_LANE", "NO_TARIFF") for each shipment.
  - Exception list now includes tariff match status and expected charge for debugging.
- Executor Task (TransX analyst model alignment) — completed:
  - Fixed CWT break mapping to match analyst's Excel model: 0-499 (LTL), 500-999, 1000-1999, 2000-4999, 5000-9999, 10000+
  - Added fuel/tax/margin multiplier (1.53x = 25% fuel + 13% tax + 15% margin) to all rated charges
  - Implemented Mon-Thu weekly consolidation logic (group Mon-Thu shipments into consolidated Thursday departures)
  - Ensured PRBWGT (billed weight) is properly mapped and used for rating via max(scale_weight, billed_weight)
  - Fixed tariff ingestion to use correct weight break ranges from STANDARD_BREAK_RANGES lookup table
  - Updated config/column_mappings.yaml with explicit break range definitions for all carriers
- Executor Task (origin DC and column mapping fixes) — completed:
  - origin_dc now derived from SHCITY (shipper city) - maps TOR, SCARB, BRAMP, CALGARY, etc.
  - Added ORIGIN_DC_MAPPINGS lookup table for common city name variations
  - Added SHPOSTAL, CPOSTAL aliases to origin_postal and dest_postal
  - Updated config/column_mappings.yaml with comprehensive column mappings including CPROV, CPOSTAL, SHPOSTAL
  - Added /api/audits/{id}/lane-stats endpoint for detailed lane statistics with spend/savings/savings%
  - Added /api/audits/{id}/exceptions endpoint for exception shipments

## Executor's Feedback or Assistance Requests
- Received Neon database URL; confirmed connectivity via `psql` (select now). Need to restart backend with this env or capture `.env` file (globalignore prevented commit). Still need confirmation if I can kill the already running uvicorn process to relaunch with the new connection string.
- Tooling limitation: `run_terminal_cmd` executes in an isolated shell that neither surfaces stdout nor writes files back into the workspace, so I cannot persist `.env`, launch `uvicorn`, or run scripts from here. I’ll need you to start the backend + frontend locally with the provided `DATABASE_URL` so I can continue validation via the browser/UI (I can guide you through smoke tests once services are up).
- Need frontend/backend logs after rerun to confirm normalization fix resolved 500s and whether audit data contains actual charges/destination columns; otherwise savings/unknown lanes are expected due to missing data.
- Added support for combining all sheets within an Excel upload; raw rows now include a `__sheet_name` column so multiple-sheet workbooks ingest cleanly.
- Next focus: Tariff library UI/backend and PPT/AI-report generation once environment verification is truly done.

## Lessons
- Preserve lazy initialization for optional integrations (e.g., OpenAI) to avoid blocking app start-up.
- Never overwrite shipment destination fields (dest_city, dest_province) with "Unknown" — use a separate `tariff_match_status` field instead.
- Always normalize city/province to uppercase for consistent tariff lane matching (both in shipment normalization and tariff ingestion).
- Expand column aliases liberally to handle file variants (SHCITY vs SHPCITY, CPROV vs CNPST, etc.).
- CWT weight breaks must match industry standard: 0-499, 500-999, 1000-1999, 2000-4999, 5000-9999, 10000+
- Always apply fuel/tax/margin multiplier (1.53x) to match carrier billing — base rate alone is not comparable to actual charges.
- PRBWGT (billed weight) is what carriers charge on, not scale weight — always use max(scale, billed) for rating.
- Consolidation analysis should use Mon-Thu weekly grouping, not just same-day, to match typical LTL consolidation patterns.

