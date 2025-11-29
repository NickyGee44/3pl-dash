"""
LLM integration for report generation.
"""
import json
import os
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from openai import OpenAI
import time
import logging
from app.models import AuditRun, LaneStat, AuditResult, Shipment
from app.services.audit_engine import get_exceptions
from app.services.report_context import build_report_context

# Lazy initialization of OpenAI client
_openai_client = None
logger = logging.getLogger(__name__)

def get_openai_client():
    """Get or initialize OpenAI client lazily."""
    global _openai_client
    if _openai_client is None:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            try:
                _openai_client = OpenAI(api_key=openai_api_key)
            except Exception as e:
                # Log error but don't crash the app
                print(f"Warning: Failed to initialize OpenAI client: {e}")
                _openai_client = False  # Use False to indicate initialization failed
    return _openai_client if _openai_client is not False else None


def generate_executive_summary(db: Session, audit_run_id: UUID) -> str:
    """
    Generate executive summary using ChatGPT.
    Returns markdown-formatted summary.
    """
    client = get_openai_client()
    if not client:
        return "OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
    
    start_time = time.perf_counter()
    # Load audit run and related data
    audit_run = db.query(AuditRun).filter(AuditRun.id == audit_run_id).first()
    if not audit_run:
        raise ValueError(f"Audit run {audit_run_id} not found")
    
    summary_metrics = audit_run.summary_metrics or {}
    
    # Get lane stats
    lane_stats = db.query(LaneStat).filter(
        LaneStat.audit_run_id == audit_run_id
    ).order_by(LaneStat.theoretical_savings.desc()).limit(10).all()
    
    # Get exception counts
    exceptions = get_exceptions(db, audit_run_id, "all")
    zero_charge_count = sum(1 for e in exceptions if "ZERO_CHARGE" in e.get("flags", []))
    outlier_count = len(get_exceptions(db, audit_run_id, "outliers"))
    
    # Get tariff-based savings if available
    total_tariff_savings = db.query(func.sum(AuditResult.savings_vs_actual)).join(
        Shipment, AuditResult.shipment_id == Shipment.id
    ).filter(
        Shipment.audit_run_id == audit_run_id,
        AuditResult.savings_vs_actual.isnot(None)
    ).scalar() or 0
    
    rerated_count = db.query(func.count(AuditResult.id)).join(
        Shipment, AuditResult.shipment_id == Shipment.id
    ).filter(
        Shipment.audit_run_id == audit_run_id,
        AuditResult.best_carrier.isnot(None)
    ).scalar() or 0
    
    # Build prompt
    prompt = f"""You are a freight audit analyst for 3PL Links, a logistics company providing freight audit services.

Generate a professional executive summary (1-2 pages) for a freight audit report.

AUDIT DETAILS:
- Customer: {audit_run.customer.name}
- Audit Name: {audit_run.name}
- Period: {audit_run.label or 'Not specified'}

KEY METRICS:
- Total Shipments: {summary_metrics.get('shipment_count', 0):,}
- Total Spend: ${summary_metrics.get('total_spend', 0):,.2f}
- Average Cost per Shipment: ${summary_metrics.get('avg_cost_per_shipment', 0):,.2f}
- Average Cost per Pound: ${summary_metrics.get('avg_cost_per_lb', 0):,.4f} (if applicable)
- Average Cost per Pallet: ${summary_metrics.get('avg_cost_per_pallet', 0):,.2f} (if applicable)

TOP SAVINGS OPPORTUNITIES BY LANE:
"""
    
    for i, lane in enumerate(lane_stats[:5], 1):
        if lane.theoretical_savings and lane.theoretical_savings > 0:
            prompt += f"""
{i}. {lane.origin_dc} → {lane.dest_province or lane.dest_region or 'Unknown'}:
   - Current Spend: ${float(lane.total_spend):,.2f}
   - Theoretical Best: ${float(lane.theoretical_best_spend):,.2f}
   - Potential Savings: ${float(lane.theoretical_savings):,.2f} ({float(lane.savings_pct):.1f}%)
   - Shipments: {lane.shipment_count}
"""
    
    prompt += f"""

BILLING ANOMALIES:
- Zero/Negative Charges: {zero_charge_count}
- High Cost Outliers: {outlier_count}

TARIFF-BASED RE-RATING:
- Re-rated Shipments: {rerated_count}
- Total Potential Savings (vs 3PL Links FAK rates): ${float(total_tariff_savings):,.2f}

Please generate a concise executive summary that:
1. Summarizes the audit scope and key findings
2. Highlights the top savings opportunities by distribution center and lane
3. Identifies billing anomalies that require attention
4. Provides clear, actionable recommendations for cost reduction
5. Uses professional business language suitable for C-level executives

Format the response in markdown with clear sections and bullet points."""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional freight audit analyst. Generate clear, actionable executive summaries."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        
        content = response.choices[0].message.content
        duration = round(time.perf_counter() - start_time, 3)
        logger.info("Generated executive summary for audit %s in %.2fs", audit_run_id, duration)
        return content
    except Exception as e:
        return f"Error generating summary: {str(e)}"


def generate_detailed_audit_report(db: Session, audit_run_id: UUID) -> str:
    """
    Generate detailed technical audit report.
    """
    client = get_openai_client()
    if not client:
        return "OpenAI API key not configured."
    
    # Similar structure but more detailed
    # Implementation similar to generate_executive_summary but with more technical details
    # For now, return a placeholder
    return "Detailed audit report generation - to be implemented"


def answer_audit_question(db: Session, audit_run_id: UUID, question: str) -> str:
    """
    Answer ad-hoc questions about a specific audit run using report context.
    """
    client = get_openai_client()
    if not client:
        return "OpenAI API key not configured. Please set OPENAI_API_KEY."
    
    context = build_report_context(db, audit_run_id)
    payload = json.dumps(context, indent=2)
    
    prompt = f"""You are a freight optimization analyst at 3PL Links.
Use the following JSON context about an audit to answer the user's question.
Quote numbers directly from the context and specify units (USD, shipments, CWT) where helpful.
If the answer is not present in the context, explicitly state what additional data would be required.

JSON_CONTEXT:
{payload}

QUESTION:
{question}

Respond with 2-3 concise paragraphs or bullet points, focusing only on information grounded in the context."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior freight audit analyst who provides precise, data-backed answers using supplied context only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=800,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating AI response: {str(e)}"
