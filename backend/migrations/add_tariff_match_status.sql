-- Migration: Add tariff_match_status and tariff_match_notes to audit_results
-- Run this against your PostgreSQL database after updating the code

ALTER TABLE audit_results 
ADD COLUMN IF NOT EXISTS tariff_match_status VARCHAR(50);

ALTER TABLE audit_results 
ADD COLUMN IF NOT EXISTS tariff_match_notes VARCHAR(255);

-- Optional: Add index for filtering by match status
CREATE INDEX IF NOT EXISTS idx_audit_results_tariff_match_status 
ON audit_results(tariff_match_status);

