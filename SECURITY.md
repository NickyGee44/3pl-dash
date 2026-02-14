# Security Audit - 3pl-dash

**Last Updated:** 2026-02-14  
**Audited By:** Nova (automated sweep)

## Current Vulnerabilities

### ⚠️ xlsx Package (frontend) - 2 High Severity
- **Status:** ACCEPTED RISK (no upstream patch available)
- **Vulns:**
  - SheetJS Regular Expression Denial of Service (ReDoS)
  - Prototype Pollution in sheetJS
- **Mitigation:** Internal tool only, no public upload endpoints
- **Remediation Plan:** Replace with `exceljs` when time permits

## Audit History

### 2026-02-14
- ✅ python-multipart: 0.0.6 → 0.0.22 (fixed 3 high severity)
- ✅ npm audit fix --force (Vite 7.3.1, updated deps)
- ⚠️ xlsx: No fix available, risk accepted
- ✅ Dependabot auto-PRs enabled

## Recommendations
1. Replace xlsx with exceljs (breaking change, requires testing)
2. Monitor Dependabot alerts weekly
3. Run manual audits quarterly
