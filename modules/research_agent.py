"""
=============================================================
MODULE: research_agent.py
PURPOSE: Automatically researches a company using Tavily web
         search API, running 5 targeted searches to uncover:
         - Fraud news
         - Court cases & litigation
         - Promoter background & controversies
         - RBI regulatory actions & penalties
         - MCA filing defaults
         Then summarizes ALL findings using Gemini into a
         structured JSON risk profile.

INDIA-SPECIFIC PORTALS THIS AGENT SEARCHES:
  - MCA21 (Ministry of Corporate Affairs) filings
  - e-Courts portal for litigation history
  - DRT (Debt Recovery Tribunal) — serious default signal
  - NCLT/IBC cases — company may be insolvent
  - ROC (Registrar of Companies) — annual return filings
=============================================================
"""

import os
import json
import re
from tavily import TavilyClient
from dotenv import load_dotenv


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

# Load API keys from the .env file
load_dotenv()

# Use our custom REST API client
from modules.gemini_api import generate_content
# Initialize Tavily client for web search
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def run_web_searches(company_name):
    """
    Runs 5 targeted web searches about the company using Tavily API.

    Each search is designed to find a SPECIFIC type of risk signal
    that Indian bank credit officers look for during loan appraisal.

    Args:
        company_name: Name of the company (e.g., "Sharma Textiles Pvt Ltd")

    Returns:
        A dictionary with 5 keys, one per search category.
        Each key contains the raw search results from Tavily.
        Returns partial results if some searches fail (does not
        stop on individual search errors).
    """
    # Define the 5 targeted search queries
    search_queries = {
        "fraud_news": f"{company_name} fraud news India 2024",
        "litigation": f"{company_name} court case litigation India",
        "promoter_background": f"{company_name} promoter background controversy",
        "rbi_regulatory": f"{company_name} RBI regulatory action penalty",
        "mca_filings": f"{company_name} MCA filing default India"
    }

    # Store results for all 5 searches
    all_results = {}

    for search_key, query in search_queries.items():
        try:
            # Run the Tavily search
            # search_depth="advanced" gives more detailed results
            # max_results=5 keeps it focused on the top findings
            response = tavily_client.search(
                query=query,
                search_depth="advanced",
                max_results=5,
                include_answer=True  # Tavily gives a quick summary too
            )

            # Store the results — both the quick answer and detailed results
            all_results[search_key] = {
                "query": query,
                "answer": response.get("answer", "No summary available"),
                "results": []
            }

            # Extract the important parts from each search result
            for result in response.get("results", []):
                all_results[search_key]["results"].append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0)
                })

        except Exception as e:
            # If one search fails, don't stop — continue with the others
            # This ensures we get as much data as possible
            all_results[search_key] = {
                "query": query,
                "answer": f"Search failed: {str(e)}",
                "results": []
            }

    return all_results


def summarize_research(company_name, search_results):
    """
    Sends ALL search results to Gemini AI to produce a structured
    risk summary that the scoring engine can use.

    Gemini reads through all 5 search results and extracts:
    - Top 3 external risks
    - Litigation history
    - Promoter reputation score
    - Overall external risk level

    Args:
        company_name:   Name of the company being researched
        search_results: Dictionary from run_web_searches() with all 5 results

    Returns:
        A Python dictionary (parsed JSON) with the research summary.
        Returns a dict with "error" key if something goes wrong.
    """
    try:
        # Convert search results to text for the prompt
        search_text = json.dumps(search_results, indent=2, default=str)

        prompt = f"""
You are an expert Indian credit research analyst working for a bank.
You have been given web search results about the company "{company_name}"
that has applied for a corporate loan.

Your job is to analyze ALL the search results and produce a comprehensive
risk assessment. This will be used by the credit scoring engine to make
the final loan decision.

IMPORTANT CONTEXT:
- DRT (Debt Recovery Tribunal) cases = VERY serious, means past loan default
- NCLT/IBC cases = Company may be insolvent or undergoing insolvency
- MCA default = Company failed to file required documents with govt
- RBI penalty = Regulatory action by India's central bank
- Promoter controversies = Risk to company's character/governance
- Benami transactions = Illegal property deals using fake names
- Fund diversion = Using loan money for purposes other than declared

SEARCH RESULTS TO ANALYZE:
===========================
{search_text[:20000]}
===========================

Analyze ALL the search results and return the following JSON:

{{
  "company_researched": "{company_name}",

  "fraud_news_summary": {{
    "found": true or false,
    "severity": "NONE / LOW / MEDIUM / HIGH / CRITICAL",
    "details": "Detailed summary of any fraud-related news found",
    "sources": ["List of source URLs where fraud news was found"]
  }},

  "litigation_summary": {{
    "active_cases_found": true or false,
    "case_count": "Number of cases found or estimated",
    "drt_cases": "Any Debt Recovery Tribunal cases? YES/NO with details",
    "nclt_ibc_cases": "Any insolvency cases? YES/NO with details",
    "other_court_cases": "Any other litigation found",
    "severity": "NONE / LOW / MEDIUM / HIGH / CRITICAL"
  }},

  "promoter_assessment": {{
    "promoter_names_found": ["List of promoter/director names found"],
    "reputation_score": 0 to 10 (10 = excellent reputation, 0 = very poor),
    "controversies_found": true or false,
    "controversy_details": "Details of any controversies",
    "linked_to_other_defaulting_companies": true or false,
    "linked_companies_details": "Details of other companies with issues",
    "criminal_cases": "Any criminal cases against promoters? Details."
  }},

  "regulatory_assessment": {{
    "rbi_actions_found": true or false,
    "rbi_action_details": "Details of RBI penalties or regulatory actions",
    "mca_defaults_found": true or false,
    "mca_default_details": "Details of MCA filing defaults",
    "sebi_actions": "Any SEBI actions if publicly listed",
    "other_regulatory_issues": "Any other regulatory red flags"
  }},

  "top_3_external_risks": [
    {{
      "risk": "Description of Risk 1 (most critical)",
      "severity": "HIGH / MEDIUM / LOW",
      "source": "Where this information was found"
    }},
    {{
      "risk": "Description of Risk 2",
      "severity": "HIGH / MEDIUM / LOW",
      "source": "Where this information was found"
    }},
    {{
      "risk": "Description of Risk 3",
      "severity": "HIGH / MEDIUM / LOW",
      "source": "Where this information was found"
    }}
  ],

  "overall_external_risk": {{
    "risk_level": "LOW / MEDIUM / HIGH / CRITICAL",
    "risk_score": 0 to 100 (0 = no external risk, 100 = extreme risk),
    "confidence": "How confident are you in this assessment (LOW/MEDIUM/HIGH)?",
    "summary": "2-3 sentence plain English summary of the external risk profile",
    "recommendation": "What should the credit officer do based on these findings?"
  }},

  "early_warning_signals": [
    "EWS 1 — specific warning from external research",
    "EWS 2 — specific warning from external research",
    "EWS 3 — specific warning from external research"
  ],

  "positive_findings": [
    "Any positive news or findings about the company",
    "Awards, recognitions, strong market position, etc."
  ]
}}

Return ONLY the JSON object. No extra text, no markdown formatting.

CRITICAL INSTRUCTION: Return ONLY the raw JSON object. Do NOT wrap it in markdown code fences. Do NOT include ```json or ``` in your response. Start your response directly with {{ and end with }}. No explanatory text before or after.
"""

        # Use our custom REST API client
        from modules.gemini_api import generate_content
        
        # Send to Gemini for analysis
        raw_response = generate_content(prompt, response_mime_type="application/json")
        research_summary = safe_parse_json(raw_response)

        if research_summary is None:
            return {
                "top_risks": ["Web research parsing failed"],
                "litigation_found": "unknown",
                "litigation_details": "Manual check required",
                "promoter_score": 5,
                "external_risk_level": "Medium"
            }

        return research_summary

    except Exception as e:
        return {
            "error": f"Research summarization failed: {str(e)}"
        }


def process_officer_notes(officer_notes):
    """
    Takes the qualitative notes entered by the Credit Officer
    in Tab 2 of the Streamlit UI and structures them for the
    scoring engine.

    These human insights (factory visits, management interviews)
    add crucial context that web searches cannot provide.

    Args:
        officer_notes: Dictionary with the following keys:
            - "factory_observations": Text from factory/site visit
            - "management_notes": Text from management interview
            - "other_concerns": Any other concerns
            - "overall_impression": "Positive" / "Neutral" / "Negative"

    Returns:
        A structured dictionary ready for the scoring engine.
    """
    try:
        # Combine all notes into one text block for Gemini
        notes_text = f"""
FACTORY/SITE VISIT OBSERVATIONS:
{officer_notes.get('factory_observations', 'No observations provided')}

MANAGEMENT INTERVIEW NOTES:
{officer_notes.get('management_notes', 'No notes provided')}

OTHER CONCERNS:
{officer_notes.get('other_concerns', 'No additional concerns')}

OVERALL IMPRESSION: {officer_notes.get('overall_impression', 'Not specified')}
"""

        prompt = f"""
You are a senior credit analyst at an Indian bank. A credit officer
has visited the company and provided the following qualitative notes.
Your job is to structure these notes for the credit scoring engine.

CREDIT OFFICER'S NOTES:
===========================
{notes_text}
===========================

Analyze these notes and return the following JSON:

{{
  "site_visit_assessment": {{
    "factory_operational": true or false or "Not Assessed",
    "capacity_utilization": "Estimated % or observation",
    "infrastructure_quality": "Good / Average / Poor / Not Assessed",
    "key_observations": ["Key finding 1", "Key finding 2"]
  }},

  "management_assessment": {{
    "transparency": "Transparent / Evasive / Mixed / Not Assessed",
    "competence": "High / Medium / Low / Not Assessed",
    "willingness_to_repay": "Willing / Unwilling / Uncertain / Not Assessed",
    "key_concerns": ["Concern 1", "Concern 2"]
  }},

  "red_flags_from_visit": [
    "Red flag 1 from officer's notes",
    "Red flag 2 from officer's notes"
  ],

  "positive_signals_from_visit": [
    "Positive signal 1",
    "Positive signal 2"
  ],

  "overall_officer_impression": {{
    "sentiment": "Positive / Neutral / Negative",
    "confidence_in_borrower": "High / Medium / Low",
    "recommended_action": "What the officer implicitly suggests"
  }},

  "impact_on_scoring": {{
    "character_adjustment": "Positive / Negative / Neutral — how this affects Character score",
    "capacity_adjustment": "Positive / Negative / Neutral — how this affects Capacity score",
    "overall_adjustment": "Should the AI raise or lower the overall credit score based on these notes?"
  }}
}}

Return ONLY the JSON. No extra text.

CRITICAL INSTRUCTION: Return ONLY the raw JSON object. Do NOT wrap it in markdown code fences. Do NOT include ```json or ``` in your response. Start your response directly with {{ and end with }}. No explanatory text before or after.
"""

        # Configure strict JSON
        from modules.gemini_api import generate_content

        raw_response = generate_content(prompt, response_mime_type="application/json")
        structured_notes = safe_parse_json(raw_response)

        if structured_notes is None:
            return {
                "site_visit_assessment": {"factory_operational": "Not Assessed", "key_observations": ["Parsing failed"]},
                "management_assessment": {"transparency": "Not Assessed", "key_concerns": ["Parsing failed"]},
                "overall_officer_impression": {"sentiment": "Neutral", "confidence_in_borrower": "Low"}
            }

        return structured_notes

    except Exception as e:
        return {
            "error": f"Officer notes processing failed: {str(e)}"
        }


def run_full_research(company_name, officer_notes=None):
    """
    MAIN FUNCTION — Call this from app.py

    Runs the complete research pipeline:
    1. Execute 5 Tavily web searches
    2. Summarize all results using Gemini
    3. Process Credit Officer notes (if provided)
    4. Return combined research output

    Args:
        company_name:   Name of the company to research
        officer_notes:  Optional dict with Credit Officer's qualitative notes
                        Keys: factory_observations, management_notes,
                              other_concerns, overall_impression

    Returns:
        Dictionary with:
        - "search_results": Raw Tavily search results (all 5 searches)
        - "research_summary": Gemini's structured risk summary
        - "officer_assessment": Structured Credit Officer notes (if provided)

    Example usage in app.py:
        research = run_full_research("Sharma Textiles Pvt Ltd", officer_notes)
        if "error" not in research["research_summary"]:
            st.json(research["research_summary"])
    """
    try:
        # Step 1: Run all 5 web searches via Tavily
        search_results = run_web_searches(company_name)

        # Step 2: Send all results to Gemini for summarization
        research_summary = summarize_research(company_name, search_results)

        # Step 3: Process Credit Officer notes if provided
        officer_assessment = None
        if officer_notes and any(officer_notes.values()):
            officer_assessment = process_officer_notes(officer_notes)

        # Step 4: Combine everything into one output
        return {
            "search_results": search_results,
            "research_summary": research_summary,
            "officer_assessment": officer_assessment
        }

    except Exception as e:
        return {
            "search_results": {},
            "research_summary": {"error": f"Research pipeline failed: {str(e)}"},
            "officer_assessment": None
        }
