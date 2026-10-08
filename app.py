import html
import os
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from modules.gst_checker import analyze_gst_data, analyze_gst_from_financial_data
from modules.pdf_reader import process_uploaded_pdf
from modules.research_agent import run_full_research
from modules.report_generator import generate_cam_report
from modules.scoring_engine import calculate_credit_score

load_dotenv()

st.set_page_config(page_title="Intelli-Credit", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

GLOSSARY = {
    "DSCR": "Debt Service Coverage Ratio shows whether cash flow is enough to repay debt.",
    "GSTR-3B": "Monthly GST return where the company self-declares sales and tax liability.",
    "GSTR-2A": "Auto-generated GST statement showing purchases reported by counterparties.",
    "DRT": "Debt Recovery Tribunal handles serious bank recovery and default matters.",
    "NCLT": "National Company Law Tribunal handles insolvency and major corporate disputes.",
    "MCA": "Ministry of Corporate Affairs stores key company filings and compliance records.",
    "ROC": "Registrar of Companies stores annual filings and director data.",
    "CAM": "Credit Appraisal Memorandum is the formal lending note submitted for sanction.",
    "PAT": "Profit After Tax is the company profit left after taxes are paid.",
    "RPT": "Related Party Transactions are deals with promoters or connected entities.",
    "Debt-to-Equity": "This ratio compares total debt with the company's own net worth.",
    "Current Ratio": "Current Ratio compares short-term assets with short-term liabilities.",
    "Promoter": "Promoter refers to the controlling founder or key owner behind the company.",
    "Circular Trading": "Suspicious back-and-forth transactions used to inflate turnover.",
    "Fund Diversion": "Using money for a purpose other than the declared business use.",
    "Auditor Qualification": "A formal warning that the accounts may have issues."
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&display=swap');
html, body, [class*='css'] { font-family: 'Manrope', sans-serif; }
.stApp { background: linear-gradient(180deg,#07111f 0%,#0b1627 100%); color:#edf4ff; }
#MainMenu, footer, header, .stDeployButton { visibility:hidden; }
.block-container { padding-top:1.3rem; }
[data-testid='stVerticalBlockBorderWrapper'] { background:rgba(18,32,53,.92); border:1px solid rgba(149,174,210,.16); border-radius:18px; }
.stTabs [data-baseweb='tab'] { font-weight:700; }
.stTabs [aria-selected='true'] { color:#edf4ff !important; border-bottom:3px solid #66a3ff !important; }
.stButton button, .stDownloadButton button { border-radius:14px !important; min-height:50px !important; font-weight:800 !important; }
.stButton button[kind='primary'], .stDownloadButton button { background:linear-gradient(135deg,#66a3ff,#2f7df6) !important; color:white !important; }
.stButton button[kind='secondary'] { background:rgba(255,255,255,.04) !important; color:#edf4ff !important; }
.stTextInput input, .stTextArea textarea, .stFileUploader > div { background:rgba(8,16,29,.88)!important; color:#edf4ff!important; border:1px solid rgba(149,174,210,.18)!important; border-radius:14px!important; }
.stRadio label { color:#edf4ff !important; }
.side, .card, .preview, .tile { background:rgba(18,32,53,.92); border:1px solid rgba(149,174,210,.14); border-radius:18px; padding:18px; }
.hero { background:linear-gradient(135deg,rgba(18,32,53,.98),rgba(8,16,29,.98)); border:1px solid rgba(149,174,210,.14); border-radius:24px; padding:28px; margin-bottom:18px; }
.hero-title { font-size:42px; font-weight:800; line-height:1; }
.hero-title span { color:#7eb3ff; }
.hero-sub { color:#9fb0c9; font-size:16px; margin-top:10px; }
.kicker { color:#9fc2ff; text-transform:uppercase; letter-spacing:.12em; font-size:12px; font-weight:800; }
.tip { display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; margin-left:6px; border-radius:50%; font-size:12px; font-weight:800; color:#dcebff; background:rgba(102,163,255,.18); border:1px solid rgba(102,163,255,.3); cursor:help; }
.grid4 { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; }
.grid5 { display:grid; grid-template-columns:repeat(5,1fr); gap:14px; }
.step { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin:8px 0 22px 0; }
.step-card { background:rgba(255,255,255,.03); border:1px solid rgba(149,174,210,.14); border-radius:16px; padding:14px; }
.badge { display:inline-block; border-radius:999px; padding:5px 10px; font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:.08em; }
.memo { background:linear-gradient(180deg,#f7f9fc,#eef3f9); color:#17212f; border-radius:18px; padding:26px; border:1px solid rgba(0,0,0,.08); }
.memo * { color:#17212f; }
.memo h1 { font-size:28px; margin:0 0 4px 0; }
.memo table { width:100%; border-collapse:collapse; margin:10px 0 18px 0; }
.memo th,.memo td { border:1px solid #d8e0ea; padding:10px 12px; text-align:left; font-size:13px; }
.memo th { background:#e8eef5; font-size:11px; text-transform:uppercase; letter-spacing:.06em; }
.memo .section { margin-top:20px; padding-top:12px; border-top:2px solid #d8e0ea; font-weight:800; color:#24446f; }
.item { padding:12px 14px; border-radius:14px; margin-bottom:10px; border:1px solid rgba(149,174,210,.14); }
.reason { background:rgba(102,163,255,.06); }
.warn { background:rgba(244,91,105,.08); }
.note { background:rgba(24,195,126,.06); }
.intro { background:linear-gradient(145deg,rgba(11,20,34,.98),rgba(16,30,51,.98)); border:1px solid rgba(149,174,210,.16); border-radius:28px; padding:36px; margin-top:24px; }
.intro-grid { display:grid; grid-template-columns:1.2fr 1fr 1fr; gap:18px; margin-top:20px; }
.intro-card { background:rgba(255,255,255,.03); border:1px solid rgba(149,174,210,.14); border-radius:18px; padding:18px; }
@media (max-width: 1100px) { .grid4,.grid5,.step,.intro-grid { grid-template-columns:1fr 1fr; } }
@media (max-width: 800px) { .grid4,.grid5,.step,.intro-grid { grid-template-columns:1fr; } .hero-title { font-size:34px; } }
</style>
""", unsafe_allow_html=True)

def init_state():
    for key, value in {
        'financial_data': None, 'gst_analysis': None, 'research_summary': None, 'officer_assessment': None,
        'credit_decision': None, 'report_path': None, 'raw_pdf_text': None, 'company_name': '', 'loan_amount': '',
        'analysis_complete': False, 'officer_notes_saved': False, 'officer_notes_raw': None,
        'impression_choice': 'NEUTRAL', 'intro_seen': False
    }.items():
        if key not in st.session_state:
            st.session_state[key] = value

def sget(data, key, default='Not Available'):
    return data.get(key, default) if isinstance(data, dict) else default

def term(label):
    return f"{html.escape(label)}<span class='tip' title='{html.escape(GLOSSARY.get(label, 'Definition not available.'), quote=True)}'>i</span>"

def conf(v):
    text = str(v or 'NOT AVAILABLE').upper().strip()
    return text if text in {'HIGH','MEDIUM','LOW','NOT AVAILABLE'} else 'NOT AVAILABLE'

def conf_badge(v):
    value = conf(v)
    bg, fg = ('rgba(24,195,126,.14)', '#18c37e') if value == 'HIGH' else ('rgba(245,185,66,.16)', '#f5b942') if value == 'MEDIUM' else ('rgba(244,91,105,.14)', '#f45b69') if value == 'LOW' else ('rgba(149,174,210,.12)', '#99abc6')
    return f"<span class='badge' style='background:{bg};color:{fg};border:1px solid {fg}33;'>{html.escape(value)}</span>"

def sev_badge(v):
    text = str(v or 'UNKNOWN').upper()
    bg, fg = ('rgba(24,195,126,.14)', '#18c37e') if text in {'APPROVE','GOOD','LOW','EXCELLENT'} else ('rgba(245,185,66,.16)', '#f5b942') if text in {'PARTIAL APPROVE','MEDIUM','FAIR'} else ('rgba(244,91,105,.14)', '#f45b69') if text in {'REJECT','HIGH','CRITICAL','POOR'} else ('rgba(149,174,210,.12)', '#99abc6')
    return f"<span class='badge' style='background:{bg};color:{fg};border:1px solid {fg}33;'>{html.escape(text)}</span>"

def score_color(score):
    try: score = int(score)
    except Exception: return '#99abc6'
    return '#18c37e' if score >= 75 else '#66a3ff' if score >= 60 else '#f5b942' if score >= 45 else '#f45b69'

def val(item):
    return str(item.get('value', 'Not Available')) if isinstance(item, dict) else str(item or 'Not Available')

def ratio(ratios, key):
    raw = sget(ratios, key, 'Not Available')
    return (raw.get('value', 'Not Available'), conf(raw.get('confidence'))) if isinstance(raw, dict) else (raw, 'NOT AVAILABLE')

def intro_screen():
    st.markdown(f"""
<div class='intro'>
  <div class='kicker'>10-second explainer</div>
  <div class='hero-title' style='margin-top:8px;'>What is <span>Intelli-Credit</span>?</div>
  <div class='hero-sub'>It is an AI credit appraisal workspace for Indian corporate lending. It reads uploaded files, checks GST risk, runs web research, scores the Five Cs, and drafts a formal {term('CAM')}.</div>
  <div class='intro-grid'>
    <div class='intro-card'><div class='kicker'>Who is it for?</div><div style='font-size:20px;font-weight:800;margin:10px 0 8px 0;'>Credit managers and hackathon judges</div><div style='color:#9fb0c9;'>Built for users who need a fast, explainable recommendation without reading hundreds of pages manually.</div></div>
    <div class='intro-card'><div class='kicker'>What problem does it solve?</div><div style='font-size:20px;font-weight:800;margin:10px 0 8px 0;'>2-4 week appraisal compressed into minutes</div><div style='color:#9fb0c9;'>The system combines extraction, GST checks, research, scoring, and memo drafting into one flow.</div></div>
    <div class='intro-card'><div class='kicker'>Why it works live</div><div style='font-size:20px;font-weight:800;margin:10px 0 8px 0;'>Explainable and demo-ready</div><div style='color:#9fb0c9;'>Key numbers show confidence labels, technical terms have hover help, and the CAM is previewed before export.</div></div>
  </div>
</div>
""", unsafe_allow_html=True)
    if st.button('Enter Intelli-Credit Workspace', type='primary', use_container_width=True):
        st.session_state.intro_seen = True
        st.rerun()
    st.stop()

def sidebar():
    with st.sidebar:
        st.markdown('## Intelli-Credit')
        st.caption('Prototype control panel')
        st.markdown(f"- {term('GSTR-3B')} vs {term('GSTR-2A')}\n- {term('DSCR')} drives repayment comfort\n- {term('DRT')} and {term('NCLT')} are major red flags\n- Final output is a formal {term('CAM')}", unsafe_allow_html=True)
        st.markdown('---')
        st.write('Gemini API: configured')
        st.write('Tavily research: configured')
        st.write('Word export: enabled')

def header():
    now = datetime.now().strftime('%d %b %Y, %H:%M IST')
    st.markdown(f"""
<div class='hero'>
  <div class='kicker'>AI credit appraisal engine for Indian corporate lending</div>
  <div style='display:flex;justify-content:space-between;gap:12px;align-items:flex-start;'>
    <div><div class='hero-title'><span>INTELLI</span>-CREDIT</div><div class='hero-sub'>Upload borrower documents, add field intelligence, run AI-backed appraisal, and review a formal CAM in the browser before export.</div></div>
    <div style='color:#9fb0c9;font-size:12px;text-transform:uppercase;letter-spacing:.12em;'>{now}</div>
  </div>
</div>
""", unsafe_allow_html=True)

def stepper(active):
    done1 = bool(st.session_state.company_name) and bool(st.session_state.financial_data or st.session_state.gst_analysis)
    done2 = bool(st.session_state.officer_notes_saved)
    items = [(1,'Upload & Extract',done1),(2,'Officer Assessment',done2),(3,'Analysis & CAM',bool(st.session_state.analysis_complete))]
    blocks = []
    for idx, label, done in items:
        mark = '✓' if done and active != idx else str(idx)
        bg = '#2f7df6' if active == idx else '#18c37e' if done else 'rgba(149,174,210,.18)'
        fg = '#fff' if active == idx or done else '#99abc6'
        status = 'Current stage' if active == idx else 'Completed' if done else 'Pending'
        blocks.append(f"<div class='step-card'><div style='width:30px;height:30px;border-radius:50%;background:{bg};color:{fg};display:flex;align-items:center;justify-content:center;font-weight:800;margin-bottom:10px;'>{mark}</div><div style='font-size:15px;font-weight:800;'>{label}</div><div style='color:#9fb0c9;font-size:13px;margin-top:4px;'>{status}</div></div>")
    st.markdown("<div class='step'>" + ''.join(blocks) + "</div>", unsafe_allow_html=True)

def extraction_summary(data):
    if not isinstance(data, dict) or 'error' in data:
        return
    ratios = sget(data, 'key_ratios', {})
    dscr_val, dscr_conf = ratio(ratios, 'dscr')
    cards = [
        ('Revenue', val(sget(data,'revenue',{})), conf(sget(sget(data,'revenue',{}),'confidence','NOT AVAILABLE'))),
        ('PAT', val(sget(data,'net_profit',{})), conf(sget(sget(data,'net_profit',{}),'confidence','NOT AVAILABLE'))),
        ('Total Debt', val(sget(data,'total_debt',{})), conf(sget(sget(data,'total_debt',{}),'confidence','NOT AVAILABLE'))),
        ('DSCR', str(dscr_val), dscr_conf),
    ]
    html_cards = []
    for label, value, confidence in cards:
        html_cards.append(f"<div class='tile'><div style='color:#9fb0c9;font-size:12px;text-transform:uppercase;letter-spacing:.1em;'>{term(label)}</div><div style='font-size:28px;font-weight:800;margin:6px 0 8px 0;'>{html.escape(str(value))}</div>{conf_badge(confidence)}</div>")
    st.markdown('### Extraction Snapshot')
    st.markdown("<div class='grid4'>" + ''.join(html_cards) + "</div>", unsafe_allow_html=True)

def quick_guide():
    terms = ['DSCR','GSTR-3B','GSTR-2A','DRT','NCLT','RPT','Debt-to-Equity','Auditor Qualification']
    cards = [f"<div class='tile'><div style='font-weight:800;'>{term(t)}</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>{html.escape(GLOSSARY[t])}</div></div>" for t in terms]
    st.markdown('### Quick term guide')
    st.markdown("<div class='grid4'>" + ''.join(cards) + "</div>", unsafe_allow_html=True)

def run_pipeline():
    st.session_state.analysis_complete = False
    st.session_state.credit_decision = None
    st.session_state.report_path = None
    with st.status('Running Intelli-Credit analysis pipeline', expanded=True) as status:
        st.write('Document extraction: complete')
        st.write('GST analysis: complete')
        try:
            res = run_full_research(st.session_state.company_name, st.session_state.officer_notes_raw)
            st.session_state.research_summary = res.get('research_summary', {})
            st.session_state.officer_assessment = res.get('officer_assessment', {})
            st.write('External research: complete')
        except Exception as exc:
            st.session_state.research_summary = {'error': str(exc)}
            st.session_state.officer_assessment = {}
            st.write('External research: warning')
        try:
            st.session_state.credit_decision = calculate_credit_score(st.session_state.financial_data, st.session_state.gst_analysis, st.session_state.research_summary, st.session_state.officer_assessment, st.session_state.loan_amount or None)
            st.write('Credit scoring: complete' if 'error' not in st.session_state.credit_decision else 'Credit scoring: failed')
        except Exception as exc:
            st.session_state.credit_decision = {'error': str(exc)}
            st.write('Credit scoring: failed')
        if st.session_state.credit_decision and 'error' not in st.session_state.credit_decision:
            try:
                st.session_state.report_path = generate_cam_report(st.session_state.credit_decision, st.session_state.financial_data or {}, st.session_state.gst_analysis or {}, st.session_state.research_summary or {}, st.session_state.officer_assessment or {}, st.session_state.company_name)
                st.write('CAM generation: complete')
            except Exception as exc:
                st.write(f'CAM generation: failed ({exc})')
        status.update(label='Analysis pipeline finished', state='complete', expanded=False)
    st.session_state.analysis_complete = True

def memo_preview():
    d = st.session_state.credit_decision or {}
    f = st.session_state.financial_data or {}
    g = st.session_state.gst_analysis or {}
    r = st.session_state.research_summary or {}
    o = st.session_state.officer_assessment or {}
    ratios = sget(f, 'key_ratios', {})
    dscr_val, dscr_conf = ratio(ratios, 'dscr')
    de_val, _ = ratio(ratios, 'debt_to_equity')
    cur_val, _ = ratio(ratios, 'current_ratio')
    reasons = ''.join([f"<li>{html.escape(str(x))}</li>" for x in sget(d,'top_reasons',[])]) or '<li>No reasons recorded.</li>'
    warnings = ''.join([f"<li>{html.escape(str(x))}</li>" for x in sget(d,'early_warning_signals',[])]) or '<li>No major early warning signals detected.</li>'
    conds = ''.join([f"<li>{html.escape(str(x))}</li>" for x in sget(d,'recommended_conditions',[])]) or '<li>No additional conditions recorded.</li>'
    gst_concerns = ''.join([f"<li>{html.escape(str(x))}</li>" for x in sget(sget(g,'overall_gst_risk',{}),'top_concerns',[])]) or '<li>No major GST concerns available.</li>'
    ext_items = []
    for item in sget(r, 'top_3_external_risks', []):
        if isinstance(item, dict):
            ext_items.append(f"<li><strong>{html.escape(str(item.get('risk','Risk found')))}</strong> ({html.escape(str(item.get('severity','Unknown')))}): {html.escape(str(item.get('source','Source not available')))}</li>")
    ext = ''.join(ext_items) or '<li>No material external risk summary available.</li>'
    decision = str(sget(d,'decision','PENDING')).upper()
    bg = '#e8f7ef' if decision == 'APPROVE' else '#fff3df' if decision == 'PARTIAL APPROVE' else '#fdecee'
    fg = '#157347' if decision == 'APPROVE' else '#9a6700' if decision == 'PARTIAL APPROVE' else '#b42318'
    st.markdown(f"""
<div class='memo'>
  <div style='color:#56708f;font-size:12px;text-transform:uppercase;letter-spacing:.16em;'>Credit Appraisal Memorandum | Internal Banking Note</div>
  <h1>{html.escape(st.session_state.company_name or 'Company')}</h1>
  <p>Date of appraisal: {datetime.now().strftime('%d %B %Y')}</p>
  <div style='margin:18px 0 22px 0;border-radius:16px;padding:16px 18px;font-weight:800;font-size:20px;background:{bg};color:{fg};'>FINAL RECOMMENDATION: {html.escape(decision)} | SCORE: {html.escape(str(sget(d,'overall_score','N/A')))} / 100</div>
  <table>
    <tr><th>Recommended Loan Amount</th><td>{html.escape(str(sget(d,'recommended_loan_amount','N/A')))}</td><th>Interest Rate</th><td>{html.escape(str(sget(d,'recommended_interest_rate','N/A')))}</td></tr>
    <tr><th>Recommended Tenure</th><td>{html.escape(str(sget(d,'recommended_tenure','N/A')))}</td><th>Decision Confidence</th><td>{html.escape(str(sget(d,'decision_confidence','N/A')))}</td></tr>
  </table>
  <div class='section'>1. Company Overview</div>
  <table>
    <tr><th>Financial Year</th><td>{html.escape(str(sget(f,'financial_year','Not Available')))}</td><th>Document Type</th><td>{html.escape(str(sget(f,'document_type','Not Available')))}</td></tr>
    <tr><th>Revenue</th><td>{html.escape(val(sget(f,'revenue',{})))}</td><th>Revenue Confidence</th><td>{html.escape(conf(sget(sget(f,'revenue',{}),'confidence','NOT AVAILABLE')))}</td></tr>
    <tr><th>PAT</th><td>{html.escape(val(sget(f,'net_profit',{})))}</td><th>Total Debt</th><td>{html.escape(val(sget(f,'total_debt',{})))}</td></tr>
    <tr><th>Net Worth</th><td>{html.escape(val(sget(f,'net_worth',{})))}</td><th>Total Assets</th><td>{html.escape(val(sget(f,'total_assets',{})))}</td></tr>
    <tr><th>DSCR</th><td>{html.escape(str(dscr_val))}</td><th>DSCR Confidence</th><td>{html.escape(dscr_conf)}</td></tr>
    <tr><th>Debt-to-Equity</th><td>{html.escape(str(de_val))}</td><th>Current Ratio</th><td>{html.escape(str(cur_val))}</td></tr>
  </table>
  <div class='section'>2. Character Assessment</div><p>{html.escape(str(sget(sget(d,'character_assessment',{}),'explanation','No explanation available.')))}</p>
  <div class='section'>3. Capacity Assessment</div><p>{html.escape(str(sget(sget(d,'capacity_assessment',{}),'explanation','No explanation available.')))}</p>
  <div class='section'>4. Capital Assessment</div><p>{html.escape(str(sget(sget(d,'capital_assessment',{}),'explanation','No explanation available.')))}</p>
  <div class='section'>5. Collateral Assessment</div><p>{html.escape(str(sget(sget(d,'collateral_assessment',{}),'explanation','No explanation available.')))}</p>
  <div class='section'>6. Conditions Assessment</div><p>{html.escape(str(sget(sget(d,'conditions_assessment',{}),'explanation','No explanation available.')))}</p>
  <div class='section'>7. GST and Fraud Risk Analysis</div><ul>{gst_concerns}</ul>
  <div class='section'>8. Early Warning Signals</div><ul>{warnings}</ul>
  <div class='section'>9. Final Recommendation</div><p><strong>Top reasons</strong></p><ul>{reasons}</ul><p><strong>Recommended conditions</strong></p><ul>{conds}</ul><p><strong>External research highlights</strong></p><ul>{ext}</ul>
  <div style='margin-top:24px;font-size:12px;color:#60758f;border-top:1px solid #d8e0ea;padding-top:12px;'>This browser preview mirrors the CAM structure for demo review before export. Final sanction still requires human credit officer validation.</div>
</div>
""", unsafe_allow_html=True)

def results():
    d = st.session_state.credit_decision
    if not d or 'error' in d:
        if d and 'error' in d: st.error(f"Analysis failed: {d['error']}")
        return
    decision = str(sget(d,'decision','PENDING')).upper()
    bg = 'linear-gradient(135deg,rgba(24,195,126,.16),rgba(24,195,126,.08))' if decision == 'APPROVE' else 'linear-gradient(135deg,rgba(245,185,66,.18),rgba(245,185,66,.08))' if decision == 'PARTIAL APPROVE' else 'linear-gradient(135deg,rgba(244,91,105,.18),rgba(244,91,105,.08))'
    border = '#18c37e' if decision == 'APPROVE' else '#f5b942' if decision == 'PARTIAL APPROVE' else '#f45b69'
    st.markdown(f"<div class='card' style='background:{bg};border-color:{border};'><div class='kicker'>Recommendation</div><div style='font-size:34px;font-weight:800;margin:8px 0 8px 0;'>{html.escape(decision)}</div><div style='color:#9fb0c9;'>Overall score: {html.escape(str(sget(d,'overall_score','N/A')))} / 100 | Decision confidence: {html.escape(str(sget(d,'decision_confidence','N/A')))}</div></div>", unsafe_allow_html=True)
    score_cards = []
    for label, key in [('Character','character_assessment'),('Capacity','capacity_assessment'),('Capital','capital_assessment'),('Collateral','collateral_assessment'),('Conditions','conditions_assessment')]:
        a = sget(d, key, {})
        score = sget(a, 'score', 0)
        score_cards.append(f"<div class='tile'><div style='color:#9fb0c9;font-size:12px;text-transform:uppercase;letter-spacing:.1em;'>{term(label)}</div><div style='font-size:28px;font-weight:800;margin:6px 0 8px 0;color:{score_color(score)};'>{html.escape(str(score))}</div>{sev_badge(sget(a,'rating','N/A'))}<div style='color:#9fb0c9;font-size:13px;margin-top:10px;'>{html.escape(str(sget(a,'explanation','')))}</div></div>")
    st.markdown('### Five Cs dashboard')
    st.markdown("<div class='grid5'>" + ''.join(score_cards) + "</div>", unsafe_allow_html=True)
    left, right = st.columns([1.45, 1])
    with left:
        st.markdown('### Live CAM preview')
        st.caption('Review the memo in the browser before downloading the Word file.')
        memo_preview()
    with right:
        st.markdown('### Decision rationale')
        for reason in sget(d, 'top_reasons', []): st.markdown(f"<div class='item reason'>{html.escape(str(reason))}</div>", unsafe_allow_html=True)
        for warning in sget(d, 'early_warning_signals', []): st.markdown(f"<div class='item warn'>{html.escape(str(warning))}</div>", unsafe_allow_html=True)
        for note in sget(d, 'monitoring_recommendations', []): st.markdown(f"<div class='item note'>{html.escape(str(note))}</div>", unsafe_allow_html=True)
        st.markdown('### Export')
        if st.session_state.report_path and os.path.exists(st.session_state.report_path):
            with open(st.session_state.report_path, 'rb') as f: report_bytes = f.read()
            st.download_button('Download formal CAM (.docx)', data=report_bytes, file_name=os.path.basename(st.session_state.report_path), mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document', type='primary', use_container_width=True)
        else:
            st.button('CAM export unavailable', disabled=True, use_container_width=True)

def main():
    init_state(); sidebar()
    if not st.session_state.intro_seen: intro_screen()
    header()
    tab1, tab2, tab3 = st.tabs(['1. Upload Documents', '2. Officer Notes', '3. Analysis & Report'])
    with tab1:
        stepper(1)
        c1, c2 = st.columns(2)
        with c1:
            st.session_state.company_name = st.text_input('Company Name', value=st.session_state.company_name, placeholder='e.g., Sharma Textiles Pvt Ltd')
        with c2:
            st.session_state.loan_amount = st.text_input('Loan Amount Requested (Crores)', value=st.session_state.loan_amount, placeholder='e.g., 40')
        u1, u2 = st.columns(2)
        with u1:
            with st.container(border=True):
                st.markdown(f"#### Annual Report and Financial Statement {term('PAT')}", unsafe_allow_html=True)
                annual_report = st.file_uploader('Upload Annual Report', type=['pdf'], key='annual_report')
        with u2:
            with st.container(border=True):
                st.markdown(f"#### GST Returns {term('GSTR-3B')} / {term('GSTR-2A')}", unsafe_allow_html=True)
                gst_file = st.file_uploader('Upload GST PDF', type=['pdf'], key='gst_file')
        with st.container(border=True):
            st.markdown(f"#### Optional bank statement support {term('Current Ratio')}", unsafe_allow_html=True)
            mode = st.radio('Bank statement mode', ['Upload PDF', 'Paste Text Summary'], horizontal=True)
            bank_text = st.text_area('Bank Statement Summary', height=120, placeholder='Average balance, monthly credits, EMI bounces, OD utilization.') if mode == 'Paste Text Summary' else ''
            if mode == 'Upload PDF': st.file_uploader('Upload Bank Statement PDF', type=['pdf'], key='bank_file')
        if st.button('Process documents', type='primary', use_container_width=True):
            if not st.session_state.company_name: st.error('Enter the company name before processing documents.')
            elif not annual_report and not gst_file and not bank_text: st.error('Upload at least one document or paste a bank statement summary.')
            else:
                with st.status('Processing uploaded files', expanded=True) as status:
                    if annual_report:
                        res = process_uploaded_pdf(annual_report, 'Annual Report')
                        st.session_state.financial_data = res.get('financial_data')
                        st.session_state.raw_pdf_text = res.get('raw_text')
                        st.write('Annual report extraction complete' if 'error' not in (st.session_state.financial_data or {}) else 'Annual report extraction failed')
                    if gst_file:
                        gst_res = process_uploaded_pdf(gst_file, 'GST Returns')
                        st.session_state.gst_analysis = analyze_gst_data(gst_res.get('raw_text', ''))
                        st.write('GST analysis complete' if 'error' not in (st.session_state.gst_analysis or {}) else 'GST analysis returned warning')
                    elif st.session_state.financial_data and 'error' not in st.session_state.financial_data:
                        st.session_state.gst_analysis = analyze_gst_from_financial_data(st.session_state.financial_data)
                        st.write('GST proxy assessment complete')
                    if bank_text: st.write('Bank statement summary noted for officer review')
                    status.update(label='Document processing complete', state='complete', expanded=False)
                st.success('Documents processed. Review the confidence labels below and continue.')
        extraction_summary(st.session_state.financial_data)
        quick_guide()
    with tab2:
        stepper(2)
        n1, n2, n3 = st.columns(3)
        with n1: factory = st.text_area('Factory and Site Visit', height=220, placeholder='Capacity utilisation, inventory observations, workforce visibility, asset condition.')
        with n2: mgmt = st.text_area('Management Interview', height=220, placeholder='Promoter openness, debt discussion quality, response consistency, repayment stance.')
        with n3: other = st.text_area('Other Concerns', height=220, placeholder='Market intelligence, related party concerns, auditor issues, fund diversion suspicion.')
        st.markdown(f"#### Overall impression {term('Promoter')}", unsafe_allow_html=True)
        st.session_state.impression_choice = st.radio('Overall impression', ['POSITIVE', 'NEUTRAL', 'NEGATIVE'], horizontal=True, index=['POSITIVE', 'NEUTRAL', 'NEGATIVE'].index(st.session_state.impression_choice), label_visibility='collapsed')
        if st.button('Save officer assessment', type='primary', use_container_width=True):
            st.session_state.officer_notes_raw = {'factory_observations': factory, 'management_notes': mgmt, 'other_concerns': other, 'overall_impression': st.session_state.impression_choice}
            st.session_state.officer_notes_saved = True
            st.success('Officer assessment saved.')
        st.markdown(f"<div class='grid4'><div class='tile'><div style='font-weight:800;'>{term('Fund Diversion')}</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>Use this if the borrower appears to use money for unrelated purposes.</div></div><div class='tile'><div style='font-weight:800;'>{term('Circular Trading')}</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>Use when turnover seems inflated through connected entities.</div></div><div class='tile'><div style='font-weight:800;'>{term('Auditor Qualification')}</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>Important when the accounts are not fully clean.</div></div><div class='tile'><div style='font-weight:800;'>{term('RPT')}</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>Flag if connected-party dealing looks material or suspicious.</div></div></div>", unsafe_allow_html=True)
    with tab3:
        stepper(3)
        for label, ok, detail in [('Company name entered', bool(st.session_state.company_name), st.session_state.company_name or 'Pending'), ('Financial extraction available', bool(st.session_state.financial_data), 'Financial data ready' if st.session_state.financial_data else 'Pending'), ('GST review available', bool(st.session_state.gst_analysis), 'GST analysis ready' if st.session_state.gst_analysis else 'Pending'), ('Officer notes saved', bool(st.session_state.officer_notes_saved), 'Officer context captured' if st.session_state.officer_notes_saved else 'Optional but recommended')]:
            color = '#18c37e' if ok else '#99abc6'
            st.markdown(f"<div class='card' style='margin-bottom:10px;border-left:4px solid {color};'><strong>{html.escape(label)}</strong><div style='color:#9fb0c9;font-size:13px;margin-top:4px;'>{html.escape(detail)}</div></div>", unsafe_allow_html=True)
        can_run = bool(st.session_state.company_name) and bool(st.session_state.financial_data or st.session_state.gst_analysis)
        if st.button('Run full credit analysis', type='primary', use_container_width=True, disabled=not can_run): run_pipeline()
        if not st.session_state.analysis_complete:
            st.markdown(f"<div class='grid4'><div class='tile'><div style='font-weight:800;'>Document extraction</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>Reads annual reports and turns them into structured data with confidence labels.</div></div><div class='tile'><div style='font-weight:800;'>{term('GSTR-3B')} vs {term('GSTR-2A')}</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>Looks for mismatch, invoice issues, and signs of inflated turnover.</div></div><div class='tile'><div style='font-weight:800;'>{term('MCA')} / {term('ROC')} / {term('DRT')}</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>Adds external credit intelligence and legal risk before scoring.</div></div><div class='tile'><div style='font-weight:800;'>Formal {term('CAM')}</div><div style='color:#9fb0c9;font-size:13px;margin-top:8px;'>Previews the memo in-browser before the exported Word report is downloaded.</div></div></div>", unsafe_allow_html=True)
        else:
            results()

if __name__ == '__main__':
    main()
