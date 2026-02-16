# 3PL Links Platform - Testing Checklist

## Pre-Launch Validation Checklist for Wally Grossi

This checklist guides you through validating the 3PL Links Freight Audit Platform before using it with live production data.

---

## Phase 1: Initial Setup Validation

### Environment Check
- [ ] Backend server starts without errors: `uvicorn app.main:app`
- [ ] Frontend loads successfully: `npm run dev` or visit production URL
- [ ] Database connection established (check server logs)
- [ ] No TypeScript/build errors when running `npm run build`

**Expected Result:** Clean startup with no error messages in console or logs.

---

## Phase 2: Sample Data Upload Test

### Test with Provided Sample Data

**File:** `sample-data/test-shipments.csv` (20 sample shipments)

1. [ ] **Navigate to Dashboard**
   - Confirm page loads with hero section and metric cards
   - Verify "Create New Audit" button is visible

2. [ ] **Start New Audit Wizard**
   - Click "Create New Audit" button
   - Wizard should display with 4 steps indicated

3. [ ] **Step 1: Basic Info**
   - Enter Audit Name: "Test Audit - Sample Data"
   - Enter Customer Name: "3PL Links Test"
   - Enter Label: "February 2024 Test"
   - Click "Next"
   - [ ] Form validation works (try leaving fields blank)

4. [ ] **Step 2: Upload Data**
   - Drag-and-drop `sample-data/test-shipments.csv` OR browse and select
   - [ ] File upload indicator shows progress
   - [ ] Success message appears after upload
   - Click "Next"

5. [ ] **Step 3: Review**
   - [ ] Audit details displayed correctly
   - [ ] Shipment count shows 20 shipments
   - [ ] Date range visible (Jan 15-24, 2024)
   - Click "Create Audit"

6. [ ] **Step 4: Processing**
   - [ ] Processing animation/spinner appears
   - [ ] Auto-redirects to audit detail page when complete (10-30 seconds)

**Expected Result:** Audit successfully created, no errors, redirected to detail view.

---

## Phase 3: Audit Detail View Validation

### Executive Summary Check

1. [ ] **Banner Metrics Displayed**
   - Total Spend shown (should be ~$1,800 for sample data)
   - Potential Savings shown (will be $0.00 until re-rating)
   - Shipments count: 20
   - Lanes count: 10

2. [ ] **Tabs Functional**
   - [ ] "Overview" tab displays by default
   - [ ] "Top Lanes" tab clickable and shows table
   - [ ] "Savings Opportunities" tab clickable (empty until re-rating)

3. [ ] **Overview Tab - Charts Visible**
   - [ ] Pie chart: "Spend by Distribution Center" renders
   - [ ] Bar chart: "Top 10 Lanes by Spend" renders
   - [ ] Key Insights section populated with bullet points

### Detailed Statistics

4. [ ] **Lane-by-Lane Breakdown**
   - [ ] "Detailed Lane Statistics" section expandable/collapsible
   - [ ] Table shows all 10 unique lanes (origin → destination pairs)
   - [ ] Columns: Lane, Shipments, Total Spend, Avg Charge, Theoretical Savings
   - [ ] Sorting works (click column headers)
   - [ ] Search/filter functional (try searching "M5H")

5. [ ] **Exceptions Section**
   - [ ] "Exceptions" section visible
   - [ ] If any exceptions found, they display with severity badges
   - [ ] "No exceptions found" message if data is clean

---

## Phase 4: Re-Rating Functionality

### Prerequisites: Tariff Data Loaded

**Note:** Re-rating requires tariff data. See `QUICK_START_TARIFFS.md` for loading test tariffs.

1. [ ] **Upload Test Tariff Data** (if not already done)
   - Use sample tariff CSV or create basic test tariff
   - Verify tariff shows in Tariff Library page

2. [ ] **Run Re-Rating**
   - [ ] Navigate to audit detail page
   - [ ] Scroll to "Re-Rating Section" (blue gradient box)
   - [ ] Click "Re-Rate Shipments" button
   - [ ] Processing indicator appears
   - [ ] Success message appears when complete

3. [ ] **Verify Savings Calculated**
   - [ ] Banner metrics update: "Potential Savings" now >$0.00
   - [ ] Lane table shows "Theoretical Savings" column populated
   - [ ] "Savings Opportunities" tab now shows data

**Expected Result:** Savings calculated and displayed across all views.

**If no tariffs loaded:** "Potential Savings" remains $0.00 - this is expected behavior.

---

## Phase 5: Export Functionality

### Excel Report

1. [ ] **Download Excel Report**
   - [ ] Scroll to "Reports" section on audit detail page
   - [ ] Click "Download Excel Report" button
   - [ ] File downloads: `audit_report_{id}.xlsx`

2. [ ] **Open Excel File**
   - [ ] File opens without errors
   - [ ] Contains multiple sheets: Lanes, Exceptions, Shipments
   - [ ] Data matches what's shown in the UI
   - [ ] Formulas/formatting intact

### PDF Report

3. [ ] **Download PDF Summary**
   - [ ] Click "Download PDF Summary" button
   - [ ] File downloads: `audit_summary_{id}.pdf`

4. [ ] **Open PDF File**
   - [ ] File opens without errors
   - [ ] Contains executive summary, charts, key metrics
   - [ ] Professional formatting, suitable for presentation

**Expected Result:** Both exports download successfully and contain correct data.

---

## Phase 6: Navigation & UI Polish

### Dashboard

1. [ ] **Return to Dashboard**
   - [ ] Click "Dashboard" in navigation
   - [ ] Metric cards update with new audit data
   - [ ] Total Audits: 1
   - [ ] Total Shipments: 20
   - [ ] Total Spend: ~$1,800

2. [ ] **Recent Audits Card**
   - [ ] Test audit appears in "Recent Audits" section
   - [ ] Card shows status badge (green "Completed")
   - [ ] Click card → navigates back to detail view

### All Audits Page

3. [ ] **Navigate to "All Audits"**
   - [ ] Click "All Audits" in navigation
   - [ ] List view shows all audits
   - [ ] Filtering/sorting works (if multiple audits)

### Tariff Library

4. [ ] **Navigate to "Tariff Library"**
   - [ ] Page loads showing loaded tariffs
   - [ ] Can browse tariff details
   - [ ] Zone mappings visible

---

## Phase 7: Real Data Test (Wally's Shipment Data)

### Prepare Your Data

**Before testing with real data:**

1. [ ] **Export shipment data from your system** as CSV
2. [ ] **Ensure required columns present:**
   - `shipment_id`, `origin_postal`, `destination_postal`, `weight`, `declared_charge`
   - Optional: `carrier`, `service_level`, `ship_date`, `delivery_date`

3. [ ] **Data validation:**
   - [ ] Postal codes in standard format (US: 12345, CA: M5H 2N2)
   - [ ] Weight values numeric (no units in the field)
   - [ ] Declared charges numeric (no currency symbols)
   - [ ] Dates in YYYY-MM-DD format or blank

### Upload Real Data

4. [ ] **Create New Audit with Real Data**
   - Follow same wizard steps as sample data test
   - Name it clearly (e.g., "January 2024 FedEx Actual")

5. [ ] **Monitor Processing**
   - [ ] No errors during upload
   - [ ] Processing completes within reasonable time (<2 min for <10k shipments)
   - [ ] All shipments imported (check count matches your CSV)

6. [ ] **Validate Results**
   - [ ] Executive summary shows realistic metrics
   - [ ] Lanes match expected origin/destination pairs
   - [ ] Spend totals match your expected freight costs
   - [ ] Charts render correctly

### Re-Rate with Real Tariffs

7. [ ] **Upload Real Carrier Tariffs** (if available)
   - See `INGEST_TARIFFS.md` for formatting
   - Test with one carrier first (e.g., FedEx Ground)

8. [ ] **Run Re-Rating on Real Data**
   - [ ] Re-rate completes successfully
   - [ ] Savings opportunities identified make sense
   - [ ] High-savings lanes align with known pricing issues
   - [ ] Exception flags legitimate data quality issues

**Expected Result:** Platform accurately analyzes real shipment data and identifies legitimate savings.

---

## Phase 8: Responsive Design & Browser Testing

### Desktop Testing

1. [ ] **Chrome/Edge** (Chromium browsers)
   - [ ] All pages load correctly
   - [ ] Charts render properly
   - [ ] Uploads work

2. [ ] **Firefox**
   - [ ] Same functionality as Chrome
   - [ ] No visual glitches

3. [ ] **Safari** (macOS)
   - [ ] Platform functional on Safari
   - [ ] File uploads work

### Mobile/Tablet Testing

4. [ ] **Tablet View** (iPad or similar, ~768px width)
   - [ ] Navigation collapses appropriately
   - [ ] Metric cards stack vertically
   - [ ] Charts remain readable

5. [ ] **Mobile View** (Phone, ~375px width)
   - [ ] Header logo and nav adapt to small screen
   - [ ] Audit cards stack in single column
   - [ ] Tables scroll horizontally or reformat
   - [ ] Buttons/touch targets large enough (44px minimum)

**Expected Result:** Platform usable across all major browsers and screen sizes.

---

## Phase 9: Performance Validation

### Load Testing

1. [ ] **Large File Upload** (if available)
   - Test with >5,000 shipment CSV
   - [ ] Upload completes without timeout
   - [ ] Processing finishes in reasonable time (<5 min for 10k shipments)

2. [ ] **Dashboard Load Time**
   - [ ] Dashboard loads in <2 seconds (after data fetched)
   - [ ] Metric cards render without lag

3. [ ] **Chart Rendering**
   - [ ] Charts render in <1 second
   - [ ] No visual stuttering/janky animations

**Expected Result:** Smooth performance even with realistic data volumes.

---

## Phase 10: Error Handling & Edge Cases

### Invalid Data Tests

1. [ ] **Upload Invalid CSV**
   - Try CSV with missing required columns
   - [ ] Clear error message displayed
   - [ ] Specific feedback on what's missing

2. [ ] **Upload Malformed Data**
   - Try CSV with invalid postal codes, non-numeric weights
   - [ ] Validation errors shown
   - [ ] Suggestions for fixing provided

3. [ ] **Empty CSV**
   - Upload CSV with headers but no data rows
   - [ ] Handled gracefully with error message

### Network Error Handling

4. [ ] **Test Offline Behavior**
   - Disconnect network mid-upload
   - [ ] Error message appears
   - [ ] Can retry without refreshing page

**Expected Result:** Graceful error handling with helpful messages, no crashes.

---

## Known Limitations (Document Here)

Use this section to note any limitations discovered during testing:

### Data Limitations
- Maximum recommended file size: _______ rows
- Supported carriers: _______
- Postal code formats supported: US ZIP, Canadian Postal Codes

### Feature Limitations
- [ ] No user authentication (open access)
- [ ] No audit deletion feature (admin must delete via DB)
- [ ] Re-rating requires exact carrier name match
- [ ] PDF export may have limited chart support

### Browser Compatibility
- Minimum browser versions: Chrome 90+, Firefox 88+, Safari 14+
- IE11 not supported (deprecated)

---

## Sign-Off

Once all tests pass, sign off below:

**Tested By:** ________________  
**Date:** ________________  
**Version Tested:** ________________  

**Overall Status:**  
- [ ] ✅ **PASS** - Ready for production use
- [ ] ⚠️ **CONDITIONAL PASS** - Usable with noted limitations
- [ ] ❌ **FAIL** - Critical issues must be resolved

**Notes/Feedback:**

```
[Your notes here]
```

---

## Next Steps After Testing

### If Tests Pass:
1. **Train users** on platform using `USER_GUIDE.md`
2. **Upload production tariff data** (see `ADMIN_GUIDE.md`)
3. **Schedule regular audit runs** (monthly/quarterly)
4. **Integrate with carrier billing systems** (if applicable)

### If Issues Found:
1. **Document issues** in the Notes section above
2. **Contact development team** with specific error messages/screenshots
3. **Provide sample data** that reproduces the issue
4. **Re-test after fixes deployed**

---

## Support Resources

- **User Guide:** `USER_GUIDE.md` - End-user instructions
- **Admin Guide:** `ADMIN_GUIDE.md` - Technical setup/configuration
- **Tariff Setup:** `INGEST_TARIFFS.md`, `QUICK_START_TARIFFS.md`
- **API Documentation:** http://localhost:8000/docs (when server running)

**Questions?** Contact: support@3pllinks.com
