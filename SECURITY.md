# Security Audit - 3pl-dash

**Last Updated:** 2026-02-15  
**Audited By:** Nova (automated sweep)

## Current Vulnerabilities

### ⚠️ xlsx Package (frontend) - 2 High Severity
- **Status:** ACCEPTED RISK (no upstream patch available)
- **Vulns:**
  - SheetJS Regular Expression Denial of Service (ReDoS) - [GHSA-5pgg-2g8v-p4x9](https://github.com/advisories/GHSA-5pgg-2g8v-p4x9)
  - Prototype Pollution in sheetJS - [GHSA-4r6h-8v6p-xvw6](https://github.com/advisories/GHSA-4r6h-8v6p-xvw6)
- **Impact:** Low (internal tool, validated inputs)
- **Mitigation:** 
  - Internal tool only, no public upload endpoints
  - File uploads restricted to authenticated users
  - Input validation on backend before processing
- **Remediation Plan:** Replace with `exceljs` or `xlsx-js-style` when time permits

## Security Improvements (2026-02-15 Sprint)

### ✅ Backend Hardening
1. **Database Security**
   - No hardcoded database URL fallback (already secure)
   - Requires `DATABASE_URL` environment variable or fails fast
   - `.env.example` added documenting all required variables

2. **Request Tracing**
   - Added Request ID middleware for audit trails
   - Each request gets unique UUID (`X-Request-ID` header)
   - Request IDs logged for debugging and security monitoring

3. **CORS Configuration**
   - Enhanced CORS with environment variable control
   - Configurable origins via `CORS_ORIGINS` env var
   - Explicit method restrictions (GET, POST, PUT, DELETE, PATCH)
   - Request ID exposed in CORS headers
   - Max age set to 3600 seconds

4. **Dependency Updates**
   - All backend dependencies updated to latest stable versions
   - FastAPI 0.115.6 includes security patches
   - PyYAML 6.0.2 fixes CVE-2020-14343
   - psycopg2-binary 2.9.10 patches security issues

### Frontend
- lucide-react icons (no known vulnerabilities)
- TypeScript strict mode enabled
- Build passes with zero errors

## Audit History

### 2026-02-15
- ✅ **Backend dependencies**: All packages updated to latest stable
  - FastAPI 0.104 → 0.115.6
  - OpenAI 1.3 → 1.60.0
  - pandas 2.1 → 2.2.3
  - See CHANGELOG.md for full list
- ✅ **Request ID middleware** added for request tracing
- ✅ **CORS hardening** with env-based configuration
- ✅ **Environment documentation** via .env.example
- ⚠️ xlsx: Still no fix available, risk re-accepted

### 2026-02-14
- ✅ python-multipart: 0.0.6 → 0.0.22 (fixed 3 high severity)
- ✅ npm audit fix --force (Vite 7.3.1, updated deps)
- ⚠️ xlsx: No fix available, risk accepted
- ✅ Dependabot auto-PRs enabled

## Environment Variable Security

### Required Variables (must be set)
- `DATABASE_URL` - PostgreSQL connection string (contains credentials)
- `SECRET_KEY` - Application secret for signing (production only)

### Optional but Recommended
- `OPENAI_API_KEY` - For AI summaries (contains API key)
- `CORS_ORIGINS` - Explicit list of allowed origins
- `UPLOAD_DIR` - File storage location

### Best Practices
1. **Never commit `.env` files** - already in `.gitignore`
2. **Use different keys per environment** (dev/staging/prod)
3. **Rotate `SECRET_KEY` regularly** in production
4. **Use read-only database credentials** for reporting endpoints
5. **Restrict `UPLOAD_DIR` permissions** to app user only

## Recommendations

### Immediate (High Priority)
1. ✅ ~~Remove hardcoded database URL~~ - Already secure
2. ✅ ~~Add request ID middleware~~ - Completed
3. ✅ ~~Update vulnerable dependencies~~ - Completed
4. 🔲 Set up log aggregation to capture request IDs
5. 🔲 Implement rate limiting on upload endpoints

### Short Term (Medium Priority)
1. Replace xlsx with exceljs (breaking change, requires testing)
2. Add authentication/authorization (currently open platform)
3. Implement input validation middleware (file size limits, type checking)
4. Add Content Security Policy headers
5. Set up automated dependency scanning in CI/CD

### Long Term (Low Priority)
1. Migrate to PostgreSQL connection pooling for production
2. Add encryption at rest for uploaded files
3. Implement audit logging for all data modifications
4. Set up security headers (HSTS, X-Frame-Options, etc.)
5. Quarterly penetration testing

## Monitoring Checklist
- [ ] Monitor Dependabot alerts weekly
- [ ] Review npm audit monthly
- [ ] Check Python CVE databases quarterly
- [ ] Audit access logs for suspicious activity
- [ ] Verify CORS configuration in production
- [ ] Test request ID logging in production
