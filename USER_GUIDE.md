# 3PL Links Freight Audit Platform - User Guide

## Welcome to the 3PL Links Freight Audit Platform

This platform helps you analyze freight shipment data, identify cost savings opportunities, and optimize your logistics expenses. This guide will walk you through the key features and workflows.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating a New Audit](#creating-a-new-audit)
3. [Understanding Audit Results](#understanding-audit-results)
4. [Interpreting Savings Recommendations](#interpreting-savings-recommendations)
5. [Exporting Reports](#exporting-reports)
6. [Managing Tariffs](#managing-tariffs)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Accessing the Platform

1. Open your web browser and navigate to the platform URL
2. You'll land on the **Dashboard** - your central hub for all freight audits

### Dashboard Overview

The dashboard displays:

- **Total Audits**: Number of freight audits you've completed
- **Total Shipments**: Aggregate shipment count across all audits
- **Total Spend**: Total freight costs analyzed
- **Potential Savings**: Highlighted in green - your optimization opportunities

---

## Creating a New Audit

### Step 1: Prepare Your Data

Before creating an audit, ensure you have a CSV file with the following columns:

**Required Columns:**
- `shipment_id` - Unique identifier for each shipment
- `origin_postal` - Origin postal/ZIP code
- `destination_postal` - Destination postal/ZIP code
- `weight` - Shipment weight (in pounds or kg - be consistent)
- `declared_charge` - Amount you were charged by the carrier

**Optional but Recommended:**
- `carrier` - Carrier name (FedEx, UPS, Purolator, etc.)
- `service_level` - Service type (Ground, Express, Priority, etc.)
- `ship_date` - Shipment date (YYYY-MM-DD format)
- `delivery_date` - Delivery date (YYYY-MM-DD format)

**Sample Data:**
See `sample-data/test-shipments.csv` for a properly formatted example.

### Step 2: Launch the Wizard

1. Click **"Create New Audit"** from the Dashboard or navigation menu
2. You'll enter a 4-step wizard:

### Step 3: Basic Information

- **Audit Name**: Give your audit a descriptive name (e.g., "Q1 2024 FedEx Analysis")
- **Customer Name**: Your company or division name
- **Label/Period**: Optional - describe the time period (e.g., "January 2024")

Click **Next** to proceed.

### Step 4: Upload Data

1. **Drag-and-drop** your CSV file into the upload zone, or **click to browse**
2. The platform will validate your file structure
3. If errors are found, you'll see specific feedback (missing columns, format issues, etc.)
4. Once validated, click **Next**

### Step 5: Review

- Review your audit details and file information
- Verify the shipment count and date range
- Click **Create Audit** to process

### Step 6: Processing

- The platform normalizes postal codes, cleans data, and prepares for analysis
- This typically takes 10-30 seconds depending on file size
- You'll be automatically redirected to the audit detail page when complete

---

## Understanding Audit Results

### Executive Summary

The audit detail page starts with an **Executive Summary** featuring:

#### Banner Metrics
- **Total Spend**: Total freight costs in the dataset
- **Potential Savings**: Estimated savings if you switched to optimal tariffs (highlighted in green)
- **Shipments Analyzed**: Total shipment count
- **Lanes Analyzed**: Unique origin-destination pairs

#### Tabs

**1. Overview Tab**
- **Spend by Distribution Center**: Pie chart showing cost breakdown by origin
- **Top 10 Lanes by Spend**: Bar chart of highest-cost routes
- **Key Insights**: Bullet points highlighting important findings

**2. Top Lanes Tab**
- Detailed table of highest-spend origin-destination pairs
- Sortable by shipments, spend, or savings potential
- Shows average charge per shipment

**3. Savings Opportunities Tab**
- Horizontal bar chart of top savings opportunities
- Summary statistics (total potential savings, affected shipments, etc.)

### Lane-by-Lane Breakdown

Scroll down to see the **Detailed Lane Statistics** (collapsible section):

- **Lane**: Origin → Destination postal codes
- **Shipments**: Number of shipments on this route
- **Total Spend**: Total freight costs for this lane
- **Avg Charge**: Average cost per shipment
- **Theoretical Savings**: Potential savings if re-rated with optimal tariffs

**Sorting & Filtering:**
- Click column headers to sort
- Use the search box to filter by postal code

### Exception Highlights

The **Exceptions** section flags issues found during analysis:

- **High variance charges**: Shipments with unusual pricing
- **Missing data**: Records with incomplete information
- **Outlier weights**: Shipments with unexpected weight values

Each exception includes:
- Severity (Warning, Error, Info)
- Affected shipment ID
- Description of the issue
- Suggested resolution

---

## Interpreting Savings Recommendations

### What Do Savings Mean?

**Potential Savings** = `Declared Charge - Theoretical Tariff Rate`

- The platform compares what you **actually paid** vs. what you **should pay** based on loaded tariff tables
- Positive savings indicate you're being overcharged
- High savings on specific lanes suggest contract renegotiation opportunities

### When Are Savings Calculated?

Savings are only calculated **after re-rating**:

1. Navigate to the audit detail page
2. Scroll to the **Re-Rating Section** (blue gradient box)
3. Click **"Re-Rate Shipments"**
4. The platform matches shipments to tariff rates and calculates savings

**Note:** You must have tariff data loaded (see [Managing Tariffs](#managing-tariffs))

### Key Metrics to Watch

- **High Savings % Lanes**: Routes with >10% savings opportunity - prioritize these for carrier negotiations
- **High Volume Lanes**: Even small per-shipment savings add up on high-frequency routes
- **Outlier Charges**: Single shipments with very high declared charges may indicate billing errors

### Actionable Insights

Use savings data to:

1. **Renegotiate Contracts**: Present lane-specific data to carriers
2. **Switch Carriers**: Identify routes where competitors offer better rates
3. **Dispute Charges**: Flag shipments with abnormally high charges for billing review
4. **Optimize Service Levels**: Check if Ground vs. Express truly justifies price differences

---

## Exporting Reports

### Excel Report (Detailed)

**What's Included:**
- Lane summary with all shipment counts and savings
- Exceptions list with full details
- Raw shipment data with theoretical rates

**How to Export:**
1. Navigate to the audit detail page
2. Scroll to the **Reports** section
3. Click **"Download Excel Report"**
4. File downloads as `audit_report_{id}.xlsx`

**Best For:**
- Deep-dive analysis in Excel/Google Sheets
- Sharing with finance teams
- Building pivot tables and custom reports

### PDF Report (Executive Summary)

**What's Included:**
- High-level metrics and charts
- Key insights and recommendations
- Visual savings summary

**How to Export:**
1. Scroll to the **Reports** section
2. Click **"Download PDF Summary"**
3. File downloads as `audit_summary_{id}.pdf`

**Best For:**
- Presenting to executives
- Sharing with non-technical stakeholders
- Quick reference/printing

---

## Managing Tariffs

### What Are Tariffs?

Tariff tables define carrier rates based on:
- Origin and destination zones
- Weight breaks
- Service level
- Accessorial charges

### Viewing Tariffs

1. Click **"Tariff Library"** in the navigation menu
2. Browse loaded tariffs by carrier and service level
3. View zone mappings and rate tables

### Uploading Tariffs

**See:** `INGEST_TARIFFS.md` and `QUICK_START_TARIFFS.md` for detailed instructions

**Quick Steps:**
1. Prepare tariff CSV with proper structure
2. Use the `/tariffs/upload` API endpoint or admin interface
3. Map postal codes to zones
4. Define weight breaks and rates

**Required for:**
- Re-rating shipments
- Calculating theoretical savings

---

## Troubleshooting

### Upload Errors

**"Missing required columns"**
- Ensure CSV has: `shipment_id`, `origin_postal`, `destination_postal`, `weight`, `declared_charge`
- Column names must match exactly (case-sensitive)

**"Invalid date format"**
- Use `YYYY-MM-DD` format (e.g., 2024-01-15)
- Or leave date columns blank if unavailable

**"File too large"**
- Split large files into batches (recommended: <50,000 rows per file)
- Contact admin for bulk upload support

### Re-Rating Issues

**"No tariffs found for this carrier"**
- You need to upload tariff data first (see [Managing Tariffs](#managing-tariffs))
- Check that carrier names in your CSV match loaded tariff names

**"Savings are $0.00"**
- Tariffs may not cover all zones in your shipment data
- Check exceptions for "No matching tariff" errors

### Performance Issues

**Dashboard loading slowly**
- Large number of audits (>100) may slow initial load
- Use filters or archive old audits

**Excel export timing out**
- Very large shipment files (>100k rows) may take 30+ seconds
- Be patient, download will complete

### Getting Help

**Technical Issues:**
- Check `SETUP.md` for environment configuration
- Review backend logs: `backend/logs/`
- Contact your platform administrator

**Data Questions:**
- See `TARIFF_RATING.md` for rating methodology
- Review sample data in `sample-data/` folder

---

## Tips & Best Practices

### Data Quality

- **Clean your CSV before upload**: Remove special characters, ensure consistent formatting
- **Use standard postal codes**: US ZIP codes, Canadian postal codes (e.g., M5H 2N2)
- **Consistent weight units**: Pick pounds or kg and stick with it across all shipments

### Audit Organization

- **Descriptive names**: Use clear audit names (carrier + time period)
- **Regular cadence**: Run monthly or quarterly audits to track trends
- **Archive old audits**: Keep the platform fast by removing outdated data

### Savings Analysis

- **Start with high-volume lanes**: Greatest ROI on frequently used routes
- **Compare carriers**: Run separate audits for each carrier to benchmark
- **Track over time**: Re-run audits periodically to measure improvement

---

## Next Steps

Now that you understand the basics:

1. **Create your first audit** with the sample data file
2. **Upload tariff data** to enable savings calculations
3. **Explore the executive summary** charts and insights
4. **Export reports** to share with your team

For advanced administration, see `ADMIN_GUIDE.md`.

Questions? Contact 3PL Links support at support@3pllinks.com
