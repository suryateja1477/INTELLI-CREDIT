"""
=============================================================
MODULE: pdf_reader.py
PURPOSE: Extract financial data from uploaded PDF documents
         (Annual Reports, Financial Statements, Legal Notices,
          Bank Statements) using pdfplumber for text extraction
          and Google Gemini for intelligent data parsing.
HANDLES: Scanned Indian PDFs, messy formatting, Hindi text,
         tables in image-based PDFs.
RETURNS: Clean JSON with key financial data.
=============================================================
"""

import json
import re
import pdfplumber
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
        # ATTEMPT 3: Find first { to last }
        # (ignores any text before/after JSON)
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start != -1 and end > start:
            json_str = response_text[start:end]
            return json.loads(json_str)
    except:
        pass

    try:
        # ATTEMPT 4: Find [ to ] for JSON arrays
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


CONFIDENCE_LABELS = {"HIGH", "MEDIUM", "LOW", "NOT AVAILABLE"}


def extract_text_from_pdf(pdf_file):
    """
    Reads a PDF file and extracts all text from every page.
    """
    try:
        pdf = pdfplumber.open(pdf_file)
        full_text = ""

        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text() or ""
            tables = page.extract_tables()
            table_text = ""

            for table in tables:
                for row in table:
                    row_text = "\t".join([str(cell) if cell else "" for cell in row])
                    table_text += row_text + "\n"

            full_text += f"\n\n--- PAGE {page_num + 1} ---\n\n"
            full_text += page_text
            if table_text:
                full_text += f"\n[TABLE DATA]\n{table_text}"

        pdf.close()

        if len(full_text.strip()) < 50:
            return "[WARNING] Very little text extracted. This PDF may be a scanned image. The AI will try its best to work with whatever text is available."

        return full_text

    except Exception as e:
        return f"[ERROR] Could not read PDF: {str(e)}"


def extract_financial_data(pdf_text, document_type="Annual Report"):
    """
    Sends extracted PDF text to Gemini and asks for structured financial data.
    """
    try:
        prompt = f"""
You are an expert Indian credit analyst AI. You have been given the text
extracted from a company's {document_type} (an Indian company).

Your job is to extract ALL key financial data from this document.
Be thorough - Indian financial documents often have data scattered
across multiple pages in different formats.

IMPORTANT INSTRUCTIONS:
1. If a value is not found in the document, use "Not Available" as the value.
2. All monetary values should be in Indian format (Lakhs or Crores as found).
3. Keep the original units mentioned in the document (Lakhs/Crores/Rs).
4. Look for data in tables, footnotes, schedules, and director reports.
5. If the document is in Hindi or mixed language, still extract the numbers.
6. Pay special attention to auditor qualifications and related party notes.
7. For each confidence field, estimate how reliable the extraction is:
   - HIGH = explicitly stated in the document
   - MEDIUM = likely correct but inferred from nearby context
   - LOW = weak evidence or ambiguous wording
   - NOT AVAILABLE = field could not be found

EXTRACT THE FOLLOWING AND RETURN AS JSON:

{{
  "company_name": "Full legal name of the company",
  "financial_year": "FY mentioned in the document (e.g., 2023-24)",
  "document_type": "{document_type}",

  "revenue": {{
    "value": "Total Revenue / Turnover amount",
    "unit": "Lakhs or Crores",
    "trend": "Increasing / Decreasing / Stable / Not Available",
    "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
  }},

  "net_profit": {{
    "value": "Profit After Tax (PAT) amount",
    "unit": "Lakhs or Crores",
    "trend": "Increasing / Decreasing / Stable / Not Available",
    "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
  }},

  "total_debt": {{
    "value": "Total borrowings (long term + short term)",
    "unit": "Lakhs or Crores",
    "breakdown": "Brief breakdown if available (term loan, working capital, etc.)",
    "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
  }},

  "net_worth": {{
    "value": "Total equity / net worth amount",
    "unit": "Lakhs or Crores",
    "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
  }},

  "total_assets": {{
    "value": "Total assets amount",
    "unit": "Lakhs or Crores",
    "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
  }},

  "cash_flow_from_operations": {{
    "value": "Operating cash flow amount",
    "unit": "Lakhs or Crores",
    "positive": true or false,
    "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
  }},

  "key_ratios": {{
    "debt_to_equity": {{
      "value": "Debt/Equity ratio if found",
      "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
    }},
    "current_ratio": {{
      "value": "Current ratio if found",
      "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
    }},
    "dscr": {{
      "value": "Debt Service Coverage Ratio if found",
      "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
    }},
    "interest_coverage": {{
      "value": "Interest Coverage Ratio if found",
      "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
    }},
    "return_on_equity": {{
      "value": "ROE if found",
      "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
    }},
    "return_on_assets": {{
      "value": "ROA if found",
      "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
    }}
  }},

  "auditor_details": {{
    "auditor_name": "Name of the audit firm",
    "audit_opinion": "Unqualified / Qualified / Adverse / Disclaimer",
    "auditor_changed": true or false,
    "key_qualifications": "Any qualifications or emphasis of matter noted",
    "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
  }},

  "related_party_transactions": {{
    "found": true or false,
    "total_value": "Total RPT value if mentioned",
    "key_parties": "List of major related parties and nature of transactions",
    "red_flags": "Any suspicious patterns noted",
    "confidence": "HIGH / MEDIUM / LOW / NOT AVAILABLE"
  }},

  "key_risks": [
    "Risk 1 found in the document",
    "Risk 2 found in the document",
    "Risk 3 found in the document"
  ],

  "management_details": {{
    "promoter_names": "Names of key promoters/directors",
    "promoter_holding": "Promoter shareholding percentage",
    "key_management_changes": "Any recent changes in directors/KMPs"
  }},

  "contingent_liabilities": {{
    "value": "Total contingent liabilities amount",
    "details": "Brief breakdown of contingent liabilities"
  }},

  "additional_observations": [
    "Any other important finding 1",
    "Any other important finding 2"
  ]
}}

HERE IS THE DOCUMENT TEXT:
===========================
{pdf_text[:15000]}
===========================

Return ONLY the JSON object. No extra text, no markdown formatting.

CRITICAL INSTRUCTION: Return ONLY the raw JSON object. Do NOT wrap it in markdown code fences. Do NOT include ```json or ``` in your response. Start your response directly with {{ and end with }}. No explanatory text before or after.
"""

        raw_response = generate_content(prompt, response_mime_type="application/json")
        financial_data = safe_parse_json(raw_response)

        if financial_data is None:
            return {
                "company_name": "Unknown",
                "revenue": "Not extracted",
                "net_profit": "Not extracted",
                "total_debt": "Not extracted",
                "net_worth": "Not extracted",
                "key_risks": ["Manual review required"],
                "auditor_name": "Not extracted",
                "auditor_changed": "Unknown",
                "red_flags": []
            }

        return normalize_confidence_fields(financial_data)

    except Exception as e:
        return {
            "error": f"Financial data extraction failed: {str(e)}"
        }




def normalize_confidence_fields(financial_data):
    """
    Ensures the main extracted values always carry a confidence label.
    """
    try:
        if not isinstance(financial_data, dict):
            return financial_data

        main_sections = [
            "revenue",
            "net_profit",
            "total_debt",
            "net_worth",
            "total_assets",
            "cash_flow_from_operations",
            "auditor_details",
            "related_party_transactions",
        ]

        for section in main_sections:
            value = financial_data.get(section)
            if isinstance(value, dict):
                value["confidence"] = clean_confidence_label(value.get("confidence"))

        ratios = financial_data.get("key_ratios")
        if isinstance(ratios, dict):
            for ratio_key, ratio_value in list(ratios.items()):
                if isinstance(ratio_value, dict):
                    ratio_value["value"] = ratio_value.get("value", "Not Available")
                    ratio_value["confidence"] = clean_confidence_label(ratio_value.get("confidence"))
                else:
                    ratios[ratio_key] = {
                        "value": ratio_value if ratio_value not in [None, ""] else "Not Available",
                        "confidence": "NOT AVAILABLE" if ratio_value in [None, "", "Not Available"] else "MEDIUM"
                    }

        return financial_data
    except Exception:
        return financial_data


def clean_confidence_label(value):
    """
    Normalizes AI confidence labels into a fixed display set.
    """
    text = str(value or "").strip().upper()
    if text in CONFIDENCE_LABELS:
        return text
    if text in {"VERY HIGH", "STRONG"}:
        return "HIGH"
    if text in {"MODERATE", "AVERAGE"}:
        return "MEDIUM"
    if text in {"WEAK", "VERY LOW"}:
        return "LOW"
    return "NOT AVAILABLE"


def process_uploaded_pdf(pdf_file, document_type="Annual Report"):
    """
    Main entry point for PDF processing.
    """
    try:
        raw_text = extract_text_from_pdf(pdf_file)

        if raw_text.startswith("[ERROR]"):
            return {
                "raw_text": raw_text,
                "financial_data": {"error": raw_text}
            }

        financial_data = extract_financial_data(raw_text, document_type)
        return {
            "raw_text": raw_text,
            "financial_data": financial_data
        }

    except Exception as e:
        return {
            "raw_text": "",
            "financial_data": {"error": f"PDF processing failed: {str(e)}"}
        }
