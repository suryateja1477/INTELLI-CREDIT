# Intelli-Credit

Intelli-Credit is a Streamlit-based AI credit appraisal workspace for Indian
corporate lending. It combines document extraction, GST risk analysis,
external company research, explainable Five Cs scoring, and Credit Appraisal
Memorandum (CAM) generation in one workflow.

> **Important:** Intelli-Credit is a decision-support prototype. Its output
> must be reviewed and validated by a qualified credit officer before any
> lending decision is made.

## Features

- Extracts financial information from uploaded PDF documents with Gemini.
- Analyzes GST-related risks, including:
  - GSTR-3B versus GSTR-2A mismatches
  - Circular-trading indicators
  - Fake-invoice and invoice-splitting signals
  - Revenue-inflation risk
- Performs external research using Tavily for fraud, litigation, promoter,
  regulatory, and MCA-related risk signals.
- Structures credit officer notes with AI-assisted analysis.
- Scores the borrower across the Five Cs of Credit:
  - Character
  - Capacity
  - Capital
  - Collateral
  - Conditions
- Produces an explainable recommendation:
  `APPROVE`, `PARTIAL APPROVE`, or `REJECT`.
- Generates a downloadable Word-format CAM report.
- Displays confidence labels and a browser-based CAM preview.

## Workflow

1. Upload an annual report or financial statement PDF.
2. Upload GST return data and, optionally, a bank statement PDF.
3. Enter the company name, requested loan amount, and credit officer notes.
4. Run the analysis pipeline.
5. Review extracted financials, risk findings, Five Cs scores, and the CAM
   preview.
6. Download the generated Word report.

## Requirements

- Python 3.10 or newer
- Gemini API access
- Tavily API access
- The Python packages listed in [requirements.txt](./requirements.txt)

## Local setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a local environment file from the template:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set:

```text
GEMINI_API_KEY=your_gemini_api_key
TAVILY_API_KEY=your_tavily_api_key
```

Never commit `.env` or paste API keys into source files. The repository
`.gitignore` excludes credentials, virtual environments, caches, and generated
reports.

## Run the application

From the project root:

```powershell
streamlit run app.py
```

Streamlit will display a local URL, normally:

```text
http://localhost:8501
```

## Run verification

The JSON parsing verification script can be run with:

```powershell
python verify_json_fix.py
```

It checks clean JSON, markdown-wrapped JSON, prose-wrapped JSON, arrays, and
invalid JSON handling.

To compile-check the Python source files:

```powershell
python -m compileall -q .
```

## Project structure

```text
.
├── app.py                         # Streamlit user interface and workflow
├── modules/
│   ├── gemini_api.py              # Gemini REST API wrapper
│   ├── gst_checker.py             # GST risk analysis
│   ├── pdf_reader.py              # PDF extraction and financial parsing
│   ├── report_generator.py        # Word CAM report generation
│   ├── research_agent.py          # Tavily research and officer-note analysis
│   └── scoring_engine.py          # Five Cs scoring and recommendations
├── requirements.txt               # Python dependencies
├── verify_json_fix.py             # JSON parsing verification
├── test_gemini_3.py               # Gemini connectivity test
├── .env.example                   # Safe environment-variable template
└── .gitignore                     # Sensitive/generated-file exclusions
```

Generated CAM reports are written to `outputs/` locally and are intentionally
excluded from GitHub.

## Data and privacy considerations

Uploaded financial documents, GST information, officer notes, and company
research may contain confidential information. Use approved credentials and
data-handling procedures in any real deployment. Do not upload borrower
documents, generated reports, API keys, or other confidential material to the
repository.

External research and AI-generated analysis can be incomplete or inaccurate.
Verify source information and apply the institution's credit policy before
using any recommendation.

## License

No license has been specified yet. Until a license is added, repository
contents should be treated as all-rights-reserved by the copyright holder.
