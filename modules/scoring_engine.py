"""
=============================================================
MODULE: scoring_engine.py
PURPOSE: The BRAIN of Intelli-Credit — takes ALL data from
         the 3 previous modules (pdf_reader, gst_checker,
         research_agent) and produces the final credit decision.

SCORES THE COMPANY ON THE FIVE Cs OF CREDIT:
  1. Character (0-100) — Promoter trustworthiness, governance
  2. Capacity  (0-100) — Ability to repay, cash flows, DSCR
  3. Capital   (0-100) — Net worth, leverage, skin in the game
  4. Collateral(0-100) — Assets pledged against the loan
  5. Conditions(0-100) — Industry health, macro environment

FINAL OUTPUT:
  - Overall credit score (0-100)
  - Decision: APPROVE / REJECT / PARTIAL APPROVE
  - Recommended loan amount (₹ Crores)
  - Recommended interest rate (%)
  - Top 3 explainable reasons for the decision
  - Early warning signals (red flags list)
=============================================================
"""

import os
import json
import re
# Use our custom REST API client instead of the google.generativeai package
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


def calculate_credit_score(financial_data, gst_analysis, research_summary, officer_assessment=None, loan_amount_requested=None):
    """
    MAIN FUNCTION — Call this from app.py

    Takes ALL inputs from every module and sends them to Gemini
    to produce the final credit decision with full explainability.

    Args:
        financial_data:       Dict from pdf_reader.py — extracted financials
        gst_analysis:         Dict from gst_checker.py — GST fraud analysis
        research_summary:     Dict from research_agent.py — web research findings
        officer_assessment:   Dict from research_agent.py — Credit Officer notes
                              (optional, can be None)
        loan_amount_requested: The loan amount the company is asking for
                               (e.g., "40 Crores"). Optional.

    Returns:
        A Python dictionary with the complete credit decision:
        - Five C scores (0-100 each with reasons)
        - Overall score
        - Decision (APPROVE / REJECT / PARTIAL APPROVE)
        - Recommended loan amount and interest rate
        - Top 3 reasons for the decision
        - Early warning signals

    Example usage in app.py:
        result = calculate_credit_score(
            financial_data, gst_analysis,
            research_summary, officer_assessment,
            loan_amount_requested="40 Crores"
        )
        if "error" not in result:
            st.metric("Overall Score", result["overall_score"])
    """
    try:
        # Convert all input data to text strings for the prompt
        financial_text = json.dumps(financial_data, indent=2, default=str)
        gst_text = json.dumps(gst_analysis, indent=2, default=str)
        research_text = json.dumps(research_summary, indent=2, default=str)
        officer_text = json.dumps(officer_assessment, indent=2, default=str) if officer_assessment else "No officer assessment provided"

        loan_info = loan_amount_requested if loan_amount_requested else "Not specified"

        # Build the comprehensive scoring prompt
        prompt = f"""
You are the CHIEF CREDIT OFFICER AI of a major Indian bank. You are making
the FINAL credit decision for a corporate loan application. This decision
must be EXPLAINABLE — every score needs a clear reason.

You have been given ALL available data about the company from multiple sources:
1. FINANCIAL DATA — extracted from the company's uploaded documents
2. GST ANALYSIS — fraud detection results from GST return cross-checks
3. EXTERNAL RESEARCH — web research findings about the company
4. CREDIT OFFICER NOTES — qualitative observations from field visits

LOAN AMOUNT REQUESTED: {loan_info}

===== DATA SOURCE 1: FINANCIAL DATA =====
{financial_text[:8000]}

===== DATA SOURCE 2: GST ANALYSIS =====
{gst_text[:6000]}

===== DATA SOURCE 3: EXTERNAL RESEARCH =====
{research_text[:8000]}

===== DATA SOURCE 4: CREDIT OFFICER NOTES =====
{officer_text[:4000]}

===========================================

NOW SCORE THE COMPANY ON THE FIVE Cs OF CREDIT.

SCORING GUIDELINES (Indian Banking Context):
- Scores 80-100: Excellent — very low risk
- Scores 60-79:  Good — acceptable risk with conditions
- Scores 40-59:  Fair — significant concerns, partial approval at best
- Scores 20-39:  Poor — high risk, likely rejection
- Scores 0-19:   Very Poor — definite rejection

DECISION RULES:
- Overall Score >= 65 → APPROVE (with conditions if 65–74)
- Overall Score 45-64 → PARTIAL APPROVE (reduced loan amount)
- Overall Score < 45  → REJECT
- ANY single C score below 20 → automatic REJECT regardless of overall
- DRT/NCLT case found → cap overall score at 40 (likely REJECT)
- GST mismatch > 30% → reduce Character score by at least 20 points

RETURN THE FOLLOWING JSON:

{{
  "company_name": "Name of the company being scored",

  "character_assessment": {{
    "score": 0 to 100,
    "rating": "Excellent / Good / Fair / Poor / Very Poor",
    "key_factors": [
      "Factor 1 that influenced this score — with data point",
      "Factor 2 that influenced this score — with data point",
      "Factor 3 that influenced this score — with data point"
    ],
    "promoter_trust_level": "High / Medium / Low",
    "governance_quality": "Strong / Adequate / Weak",
    "explanation": "2-3 sentence plain English explanation of why this score"
  }},

  "capacity_assessment": {{
    "score": 0 to 100,
    "rating": "Excellent / Good / Fair / Poor / Very Poor",
    "key_factors": [
      "Factor 1 — e.g., Revenue trend, DSCR value",
      "Factor 2 — e.g., Cash flow status",
      "Factor 3 — e.g., Repayment track record"
    ],
    "dscr_assessment": "DSCR value and what it means",
    "cash_flow_health": "Positive / Negative / Uncertain",
    "explanation": "2-3 sentence plain English explanation"
  }},

  "capital_assessment": {{
    "score": 0 to 100,
    "rating": "Excellent / Good / Fair / Poor / Very Poor",
    "key_factors": [
      "Factor 1 — e.g., Net worth, Debt-to-Equity ratio",
      "Factor 2 — e.g., Promoter's own stake",
      "Factor 3 — e.g., Capital adequacy"
    ],
    "debt_to_equity": "Actual ratio and assessment",
    "net_worth_adequacy": "Adequate / Marginal / Inadequate",
    "explanation": "2-3 sentence plain English explanation"
  }},

  "collateral_assessment": {{
    "score": 0 to 100,
    "rating": "Excellent / Good / Fair / Poor / Very Poor",
    "key_factors": [
      "Factor 1 — e.g., Asset cover ratio",
      "Factor 2 — e.g., Quality of assets",
      "Factor 3 — e.g., Collateral enforceability"
    ],
    "collateral_cover_ratio": "Assets / Loan amount ratio",
    "asset_quality": "Good / Average / Poor",
    "explanation": "2-3 sentence plain English explanation"
  }},

  "conditions_assessment": {{
    "score": 0 to 100,
    "rating": "Excellent / Good / Fair / Poor / Very Poor",
    "key_factors": [
      "Factor 1 — e.g., Industry outlook",
      "Factor 2 — e.g., Regulatory environment",
      "Factor 3 — e.g., Economic conditions"
    ],
    "industry_outlook": "Positive / Stable / Negative",
    "regulatory_risk": "Low / Medium / High",
    "explanation": "2-3 sentence plain English explanation"
  }},

  "overall_score": 0 to 100,
  "overall_rating": "Excellent / Good / Fair / Poor / Very Poor",

  "decision": "APPROVE / REJECT / PARTIAL APPROVE",
  "decision_confidence": "HIGH / MEDIUM / LOW",

  "recommended_loan_amount": "Amount in Crores INR (may be less than requested)",
  "recommended_interest_rate": "Percentage (higher risk = higher rate)",
  "recommended_tenure": "Suggested loan tenure in years",
  "recommended_conditions": [
    "Condition 1 for loan approval (e.g., personal guarantee required)",
    "Condition 2 (e.g., quarterly financial reporting mandated)",
    "Condition 3 (e.g., collateral margin of 25% required)"
  ],

  "top_reasons": [
    "Reason 1 — THE most important reason for this decision, with specific data",
    "Reason 2 — Second most important reason with specific data",
    "Reason 3 — Third reason with specific data"
  ],

  "early_warning_signals": [
    "EWS 1 — specific red flag the bank should monitor",
    "EWS 2 — specific red flag",
    "EWS 3 — specific red flag"
  ],

  "monitoring_recommendations": [
    "What the bank should monitor post-disbursement 1",
    "What the bank should monitor post-disbursement 2"
  ],

  "score_summary_table": {{
    "character": {{"score": 0, "weight": "20%"}},
    "capacity": {{"score": 0, "weight": "25%"}},
    "capital": {{"score": 0, "weight": "20%"}},
    "collateral": {{"score": 0, "weight": "15%"}},
    "conditions": {{"score": 0, "weight": "20%"}}
  }}
}}

CRITICAL REMINDERS:
1. Every score MUST have a clear, data-backed reason — NO BLACK BOX
2. The decision must reference SPECIFIC data points from the inputs
3. If data is missing, say so and explain the impact on scoring
4. Use Indian banking terminology (Crores, Lakhs, DSCR, NPA, etc.)
5. Be conservative — when in doubt, err on the side of caution
6. The top_reasons must be crystal clear to a bank branch manager

Return ONLY the JSON. No extra text, no markdown formatting.

CRITICAL INSTRUCTION: Return ONLY the raw JSON object. Do NOT wrap it in markdown code fences. Do NOT include ```json or ``` in your response. Start your response directly with {{ and end with }}. No explanatory text before or after.
"""

        # Use our custom REST API client instead of the google.generativeai package
        from modules.gemini_api import generate_content
        
        # Call the REST API with JSON enforcement
        raw_response = generate_content(prompt, response_mime_type="application/json")
        credit_decision = safe_parse_json(raw_response)

        if credit_decision is None:
            return {
                "character_score": 50,
                "capacity_score": 50,
                "capital_score": 50,
                "collateral_score": 50,
                "conditions_score": 50,
                "overall_score": 50,
                "decision": "REVIEW REQUIRED",
                "recommended_loan_amount": "Unable to determine",
                "recommended_interest_rate": "Unable to determine",
                "top_reasons": [
                    "AI response parsing failed — please retry the analysis",
                    "Ensure documents are clear and readable",
                    "Try with a different PDF format"
                ],
                "early_warning_signals": [
                    "Manual review required"
                ]
            }

        # Validate the decision has all required fields
        credit_decision = validate_decision(credit_decision)

        return credit_decision

    except Exception as e:
        return {
            "error": f"Credit scoring failed: {str(e)}"
        }


def validate_decision(decision):
    """
    Ensures the credit decision JSON has all required fields.
    Adds default values if any critical fields are missing.

    This prevents the app from crashing if Gemini skips a field.

    Args:
        decision: The parsed credit decision dictionary from Gemini

    Returns:
        The same dictionary with any missing fields filled in with defaults.
    """
    try:
        # Ensure overall_score exists and is a number
        if "overall_score" not in decision:
            decision["overall_score"] = 50
        else:
            # Make sure it's an integer
            decision["overall_score"] = int(decision["overall_score"])

        # Ensure decision exists
        if "decision" not in decision:
            score = decision["overall_score"]
            if score >= 65:
                decision["decision"] = "APPROVE"
            elif score >= 45:
                decision["decision"] = "PARTIAL APPROVE"
            else:
                decision["decision"] = "REJECT"

        # Ensure all 5 C scores exist
        for assessment in ["character_assessment", "capacity_assessment",
                           "capital_assessment", "collateral_assessment",
                           "conditions_assessment"]:
            if assessment not in decision:
                decision[assessment] = {
                    "score": 50,
                    "rating": "Fair",
                    "key_factors": ["Data insufficient for detailed assessment"],
                    "explanation": "Limited data available for this assessment dimension."
                }
            elif "score" not in decision[assessment]:
                decision[assessment]["score"] = 50

        # Ensure top_reasons exists
        if "top_reasons" not in decision:
            decision["top_reasons"] = [
                "Insufficient data to determine primary reason",
                "Further documentation review recommended",
                "Credit officer manual review suggested"
            ]

        # Ensure early_warning_signals exists
        if "early_warning_signals" not in decision:
            decision["early_warning_signals"] = []

        # Ensure recommended fields exist
        if "recommended_loan_amount" not in decision:
            decision["recommended_loan_amount"] = "To be determined after further review"

        if "recommended_interest_rate" not in decision:
            decision["recommended_interest_rate"] = "To be determined"

        # Ensure score_summary_table exists
        if "score_summary_table" not in decision:
            decision["score_summary_table"] = {
                "character": {"score": decision.get("character_assessment", {}).get("score", 50), "weight": "20%"},
                "capacity": {"score": decision.get("capacity_assessment", {}).get("score", 50), "weight": "25%"},
                "capital": {"score": decision.get("capital_assessment", {}).get("score", 50), "weight": "20%"},
                "collateral": {"score": decision.get("collateral_assessment", {}).get("score", 50), "weight": "15%"},
                "conditions": {"score": decision.get("conditions_assessment", {}).get("score", 50), "weight": "20%"}
            }

        return decision

    except Exception:
        # If validation itself fails, return the original decision as-is
        return decision


def get_score_color(score):
    """
    Returns a color code based on the credit score.
    Used in the Streamlit UI to color-code the score cards.

    Args:
        score: Integer score from 0- 100

    Returns:
        A color string for Streamlit display.
    """
    if score >= 75:
        return "green"     # Excellent — low risk
    elif score >= 60:
        return "blue"      # Good — acceptable
    elif score >= 45:
        return "orange"    # Fair — concerns present
    else:
        return "red"       # Poor — high risk


def get_decision_color(decision):
    """
    Returns a color for the decision banner in the UI.

    Args:
        decision: "APPROVE", "REJECT", or "PARTIAL APPROVE"

    Returns:
        Color string for the Streamlit banner.
    """
    decision_upper = decision.upper().strip()
    if decision_upper == "APPROVE":
        return "green"
    elif decision_upper == "REJECT":
        return "red"
    elif decision_upper == "PARTIAL APPROVE":
        return "orange"
    else:
        return "gray"
