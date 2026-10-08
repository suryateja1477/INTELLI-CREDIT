"""
=============================================================
MODULE: gst_checker.py
PURPOSE: Detect GST fraud signals by cross-checking GSTR-3B
         (self-declared by the company) against GSTR-2A
         (confirmed by buyers). Also detects circular trading,
         fake invoice patterns, and revenue inflation.

INDIA-SPECIFIC CONTEXT:
  - GSTR-3B = What the company SAYS it earned (self-reported)
  - GSTR-2A = What buyers ACTUALLY confirmed they paid
  - If 3B >> 2A → company may be inflating revenue
  - If same parties appear as both buyer and seller →
    possible circular trading (fake transactions)
  - Frequent small invoices just below threshold →
    possible invoice splitting to avoid scrutiny
=============================================================
"""

import os
import json
import re
# Use our custom REST API client
from modules.gemini_api import generate_content


def safe_parse_json(response_text):
    """
    Safely parses JSON from Gemini AI response.
    Handles markdown code fences, extra text, 
    and other common Gemini formatting issues.
    """
    try:
        # ATTEMPT 1: Direct parse (cleanest case)
        return json.loads(response_text)
    except:
        pass
    
    try:
        # ATTEMPT 2: Strip ```json ... ``` fences
        cleaned = re.sub(r'```(?:json)?\s*', '', response_text)
        cleaned = cleaned.replace('```', '').strip()
        return json.loads(cleaned)
    except:
        pass
    
    try:
        # ATTEMPT 3: Find the first complete JSON value in wrapped text.
        object_start = response_text.find('{')
        array_start = response_text.find('[')
        if array_start != -1 and (object_start == -1 or array_start < object_start):
            end = response_text.rfind(']') + 1
            if end > array_start:
                return json.loads(response_text[array_start:end])
        if object_start != -1:
            end = response_text.rfind('}') + 1
            if end > object_start:
                return json.loads(response_text[object_start:end])
    except:
        pass

    try:
        # ATTEMPT 4: Find an array when an object appeared first but was invalid
        start = response_text.find('[')
        end = response_text.rfind(']') + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except:
        pass
    
    # ALL ATTEMPTS FAILED — return safe default
    print(f"JSON Parse failed. Raw response was:\n{response_text[:500]}")
    return None


def analyze_gst_data(gst_text):
    """
    MAIN FUNCTION — Call this from app.py

    Takes the raw text extracted from a GST Returns PDF
    (or pasted GST data) and sends it to Gemini AI to:

    1. Parse GSTR-3B (self-declared) and GSTR-2A (buyer-confirmed) figures
    2. Calculate the mismatch between them
    3. Detect circular trading patterns
    4. Identify fake invoice signals
    5. Flag revenue inflation risks

    Args:
        gst_text: Raw text from the GST returns PDF or pasted data.
                  This could contain GSTR-3B data, GSTR-2A data, or both.

    Returns:
        A Python dictionary with GST fraud analysis results.
        Returns a dict with "error" key if something goes wrong.

    Example usage in app.py:
        gst_result = analyze_gst_data(gst_text)
        if "error" not in gst_result:
            st.json(gst_result)
    """
    try:
        # Build a detailed prompt for Gemini that understands Indian GST
        prompt = f"""
You are an expert Indian GST fraud detection analyst working for a bank's
credit appraisal team. You have been given GST return data for a company
that has applied for a loan.

Your job is to analyze this data for fraud signals that banks look for
during credit appraisal in India.

IMPORTANT BACKGROUND (Indian GST System):
- GSTR-3B: Monthly return filed by the company (SELF-DECLARED sales & tax)
- GSTR-2A: Auto-generated from SELLERS' GSTR-1 filings (BUYER-CONFIRMED purchases)
- If GSTR-3B reported sales >> GSTR-2A confirmed purchases, the company
  may be INFLATING revenue to look stronger for the loan
- Circular trading: Company A sells to Company B, B sells to C, C sells
  back to A — all fake transactions to inflate turnover
- Invoice splitting: Breaking large invoices into many small ones
  (below ₹50,000 or ₹2,00,000 thresholds) to avoid scrutiny

ANALYZE THE DATA AND RETURN THE FOLLOWING JSON:

{{
  "gstr_3b_summary": {{
    "total_taxable_turnover": "Total turnover declared in GSTR-3B",
    "total_tax_paid": "Total GST paid as per GSTR-3B",
    "months_covered": "Number of months of data available",
    "average_monthly_turnover": "Average monthly turnover"
  }},

  "gstr_2a_summary": {{
    "total_confirmed_turnover": "Total turnover confirmed by buyers in GSTR-2A",
    "total_tax_confirmed": "Total GST confirmed by buyers",
    "months_covered": "Number of months of data available",
    "average_monthly_confirmed": "Average monthly confirmed turnover"
  }},

  "mismatch_analysis": {{
    "turnover_mismatch_amount": "Difference between 3B and 2A (in ₹)",
    "mismatch_percentage": "Percentage mismatch ((3B - 2A) / 3B * 100)",
    "severity": "LOW (< 10%) / MEDIUM (10-25%) / HIGH (> 25%)",
    "interpretation": "Plain English explanation of what this mismatch means for the bank"
  }},

  "circular_trading_detection": {{
    "detected": true or false,
    "confidence": "LOW / MEDIUM / HIGH",
    "signals_found": [
      "Signal 1 — describe the suspicious pattern",
      "Signal 2 — describe the suspicious pattern"
    ],
    "suspicious_parties": [
      {{
        "party_name": "Name of the suspicious party",
        "relationship": "How they relate to the applicant company",
        "concern": "Why this is suspicious"
      }}
    ]
  }},

  "fake_invoice_detection": {{
    "detected": true or false,
    "confidence": "LOW / MEDIUM / HIGH",
    "signals_found": [
      "Signal 1 — describe the pattern",
      "Signal 2 — describe the pattern"
    ],
    "invoice_splitting_risk": "YES / NO — are there many invoices just below threshold amounts?"
  }},

  "revenue_inflation_risk": {{
    "risk_level": "LOW / MEDIUM / HIGH",
    "estimated_inflated_amount": "Estimated amount of inflated revenue (in ₹)",
    "explanation": "Clear explanation of why revenue may be inflated"
  }},

  "itc_fraud_check": {{
    "excess_itc_claimed": true or false,
    "itc_mismatch_amount": "Difference in Input Tax Credit claimed vs confirmed",
    "risk_level": "LOW / MEDIUM / HIGH",
    "explanation": "What this means for the bank"
  }},

  "monthly_pattern_analysis": {{
    "seasonal_spikes": "Are there unusual spikes in certain months?",
    "year_end_loading": "Is there suspicious revenue loading in March (year-end)?",
    "consistent_growth": "Is the monthly pattern consistent or erratic?",
    "red_flags": [
      "Any unusual monthly pattern found"
    ]
  }},

  "overall_gst_risk": {{
    "risk_level": "LOW / MEDIUM / HIGH",
    "risk_score": 0 to 100 (0 = no risk, 100 = extreme risk),
    "top_concerns": [
      "Concern 1 — most critical finding",
      "Concern 2 — second most critical finding",
      "Concern 3 — third finding"
    ],
    "recommendation_for_bank": "Clear recommendation for the credit officer"
  }},

  "early_warning_signals": [
    "EWS 1 — specific warning signal found",
    "EWS 2 — specific warning signal found",
    "EWS 3 — specific warning signal found"
  ]
}}

HERE IS THE GST DATA TO ANALYZE:
===========================
{gst_text[:15000]}
===========================

Return ONLY the JSON object. No extra text, no markdown formatting.

CRITICAL INSTRUCTION: Return ONLY the raw JSON object. Do NOT wrap it in markdown code fences. Do NOT include ```json or ``` in your response. Start your response directly with {{ and end with }}. No explanatory text before or after.
"""

        # Use our custom REST API client
        from modules.gemini_api import generate_content
        
        # Send to Gemini for analysis
        raw_response = generate_content(prompt, response_mime_type="application/json")
        gst_analysis = safe_parse_json(raw_response)

        if gst_analysis is None:
            return {
                "mismatch_detected": "unknown",
                "mismatch_amount": "0",
                "circular_trading_risk": "low",
                "explanation": "GST analysis could not be completed — manual review needed"
            }

        return gst_analysis

    except Exception as e:
        return {
            "error": f"GST analysis failed: {str(e)}"
        }


def analyze_gst_from_financial_data(financial_data):
    """
    Alternative entry point — when we don't have a separate GST PDF
    but have financial data already extracted by pdf_reader.py.

    This takes the financial data dictionary (from pdf_reader) and
    asks Gemini to assess GST-related risks based on whatever
    revenue, tax, and transaction data is available.

    Args:
        financial_data: Dictionary from pdf_reader.py's extract_financial_data()

    Returns:
        GST risk analysis dictionary (same structure as analyze_gst_data)
    """
    try:
        # Convert financial data to a text summary for Gemini
        financial_summary = json.dumps(financial_data, indent=2, default=str)

        prompt = f"""
You are an expert Indian GST fraud detection analyst. You have been given
the financial data extracted from a company's Annual Report / Financial
Statement. A separate GST return document was NOT provided.

Based on the available financial data, assess the GST-related risks.
Look for:
1. Revenue figures that seem inconsistent or inflated
2. Related party transactions that could indicate circular trading
3. Any mentions of GST disputes, demands, or penalties
4. Contingent liabilities related to GST/tax
5. Auditor qualifications mentioning GST issues

If specific GSTR-3B / GSTR-2A data is not available, make reasonable
assessments based on the financial data provided and clearly state
what data was not available.

FINANCIAL DATA:
===========================
{financial_summary[:12000]}
===========================

Return ONLY a JSON object with this structure:
{{
  "gstr_3b_summary": {{
    "total_taxable_turnover": "Estimated from revenue figures or Not Available",
    "total_tax_paid": "Not Available — no separate GST return provided",
    "months_covered": "Not Available",
    "average_monthly_turnover": "Estimated or Not Available"
  }},
  "gstr_2a_summary": {{
    "total_confirmed_turnover": "Not Available — no GSTR-2A data",
    "total_tax_confirmed": "Not Available",
    "months_covered": "Not Available",
    "average_monthly_confirmed": "Not Available"
  }},
  "mismatch_analysis": {{
    "turnover_mismatch_amount": "Cannot calculate without GSTR-2A",
    "mismatch_percentage": "Not Available",
    "severity": "UNKNOWN — separate GST returns needed for accurate check",
    "interpretation": "Explain what can and cannot be determined"
  }},
  "circular_trading_detection": {{
    "detected": true or false,
    "confidence": "LOW / MEDIUM / HIGH",
    "signals_found": ["Signals based on related party transactions"],
    "suspicious_parties": []
  }},
  "fake_invoice_detection": {{
    "detected": true or false,
    "confidence": "LOW",
    "signals_found": ["Any signals from financial statements"],
    "invoice_splitting_risk": "Cannot determine without invoice-level data"
  }},
  "revenue_inflation_risk": {{
    "risk_level": "LOW / MEDIUM / HIGH",
    "estimated_inflated_amount": "Estimate if possible",
    "explanation": "Assessment based on available financial data"
  }},
  "itc_fraud_check": {{
    "excess_itc_claimed": false,
    "itc_mismatch_amount": "Not Available",
    "risk_level": "UNKNOWN",
    "explanation": "Need GSTR-2A data for accurate ITC verification"
  }},
  "monthly_pattern_analysis": {{
    "seasonal_spikes": "Cannot determine from annual data",
    "year_end_loading": "Cannot determine from annual data",
    "consistent_growth": "Assessment based on year-over-year data",
    "red_flags": []
  }},
  "overall_gst_risk": {{
    "risk_level": "LOW / MEDIUM / HIGH",
    "risk_score": 0 to 100,
    "top_concerns": ["Based on available data"],
    "recommendation_for_bank": "Recommend obtaining GSTR-2A/3B for complete check"
  }},
  "early_warning_signals": []
}}

Return ONLY the JSON. No extra text.

CRITICAL INSTRUCTION: Return ONLY the raw JSON object. Do NOT wrap it in markdown code fences. Do NOT include ```json or ``` in your response. Start your response directly with {{ and end with }}. No explanatory text before or after.
"""

        # Use custom REST client
        from modules.gemini_api import generate_content
        
        raw_response = generate_content(prompt, response_mime_type="application/json")
        gst_analysis = safe_parse_json(raw_response)

        if gst_analysis is None:
            return {
                "mismatch_detected": "unknown",
                "mismatch_amount": "0",
                "circular_trading_risk": "low",
                "explanation": "GST analysis could not be completed — manual review needed"
            }

        return gst_analysis

    except Exception as e:
        return {
            "error": f"GST analysis from financial data failed: {str(e)}"
        }
