"""
Transaction Comparison AI
Streamlit main entry point.

Run with:
    streamlit run main.py
"""

import os
import sys
import io
import pandas as pd
import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Transaction Comparison AI",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Header ── */
.app-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #0066ff22 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    border: 1px solid #1e40af33;
    position: relative;
    overflow: hidden;
}
.app-header::after {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, #0066ff18 0%, transparent 70%);
    pointer-events: none;
}
.app-title {
    font-size: 1.9rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0;
    letter-spacing: -0.5px;
}
.app-subtitle {
    color: #94a3b8;
    font-size: 0.92rem;
    margin-top: 0.3rem;
    font-weight: 400;
}
.badge {
    display: inline-block;
    background: #0066ff22;
    color: #60a5fa;
    border: 1px solid #0066ff44;
    border-radius: 99px;
    padding: 2px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-top: 0.6rem;
}

/* ── KPI Cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1rem 0; }
.kpi-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    transition: transform 0.2s, border-color 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); border-color: #0066ff55; }
.kpi-label { font-size: 0.72rem; color: #64748b; font-weight: 600; letter-spacing: 0.8px; text-transform: uppercase; }
.kpi-value { font-size: 1.9rem; font-weight: 700; margin-top: 4px; font-family: 'JetBrains Mono', monospace; }
.kpi-sub { font-size: 0.78rem; color: #64748b; margin-top: 2px; }
.kpi-exact .kpi-value { color: #00b386; }
.kpi-fuzzy .kpi-value { color: #f5a623; }
.kpi-unmatch .kpi-value { color: #e63946; }
.kpi-total .kpi-value { color: #60a5fa; }

/* ── Status badge ── */
.status-exact  { background: #d1fae522; color: #00b386; border: 1px solid #00b38633; padding: 2px 10px; border-radius: 99px; font-size: 0.78rem; font-weight: 600; }
.status-fuzzy  { background: #fef3c722; color: #f5a623; border: 1px solid #f5a62333; padding: 2px 10px; border-radius: 99px; font-size: 0.78rem; font-weight: 600; }
.status-unmatched { background: #fee2e222; color: #e63946; border: 1px solid #e6394633; padding: 2px 10px; border-radius: 99px; font-size: 0.78rem; font-weight: 600; }

/* ── Section header ── */
.section-header {
    font-size: 0.8rem;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin: 1.2rem 0 0.5rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid #1e293b;
}

/* ── Sidebar ── */
.sidebar-brand {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f8fafc;
    padding: 0.5rem 0;
}
.sidebar-note {
    background: #0f172a;
    border-left: 3px solid #0066ff;
    border-radius: 4px;
    padding: 0.7rem 1rem;
    font-size: 0.82rem;
    color: #94a3b8;
    margin: 0.8rem 0;
}
.api-warning {
    background: #fff3cd22;
    border: 1px solid #f5a62355;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-size: 0.82rem;
    color: #f5a623;
}
.api-ok {
    background: #d1fae522;
    border: 1px solid #00b38633;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    font-size: 0.82rem;
    color: #00b386;
}

/* ── Step cards ── */
.step-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.step-num {
    display: inline-block;
    background: #0066ff;
    color: white;
    border-radius: 99px;
    width: 22px;
    height: 22px;
    text-align: center;
    line-height: 22px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 8px;
}

/* ── Progress bar override ── */
.stProgress > div > div { background: #0066ff !important; }

/* ── Button styling ── */
.stButton > button {
    background: linear-gradient(135deg, #0066ff, #0052cc);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.9rem;
    padding: 0.55rem 1.5rem;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #0052cc, #003d99);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px #0066ff44;
}

/* ── Download buttons ── */
.stDownloadButton > button {
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.85rem;
}

/* ── DataFrame ── */
.dataframe th { background: #0f172a !important; color: #94a3b8 !important; }

/* ── Dark overall ── */
.stApp { background: #080d1a; }
.block-container { padding-top: 1.5rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-brand">🔍 TxnCompare AI</div>', unsafe_allow_html=True)
    st.markdown("---")

    # API Key input
    st.markdown('<div class="section-header">🔑 API Configuration</div>', unsafe_allow_html=True)

    api_key_input = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="AIza...",
        help="Get your key at https://aistudio.google.com/app/apikey",
        value=os.getenv("GEMINI_API_KEY", "")
    )

    if api_key_input and api_key_input != "your_gemini_api_key_here":
        os.environ["GEMINI_API_KEY"] = api_key_input
        st.markdown('<div class="api-ok">✅ API key configured</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="api-warning">⚠️ Enter your Gemini API key above or set it in <code>.env</code></div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown('<div class="section-header">⚙️ Match Settings</div>', unsafe_allow_html=True)
    fuzzy_threshold = st.slider("Fuzzy Description Threshold", 50, 100, 85,
                                 help="Minimum similarity score for fuzzy description matching")
    amount_tolerance = st.slider("Amount Tolerance (%)", 0.0, 10.0, 2.0, 0.5,
                                  help="Allowed % difference for fuzzy amount matching")
    date_tolerance = st.slider("Date Tolerance (days)", 0, 7, 3,
                                help="Allowed day difference for fuzzy date matching")

    st.markdown("---")
    st.markdown("""
    <div class="sidebar-note">
    <b>How it works:</b><br>
    1. Upload bank mutation (PDF/Excel)<br>
    2. Upload finance record (Excel)<br>
    3. Run comparison<br>
    4. Download reports
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.72rem;color:#475569;text-align:center">v1.0.0 · Confidential</div>', unsafe_allow_html=True)


# ── Main Content ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="app-title">Transaction Comparison AI</div>
    <div class="app-subtitle">Automated reconciliation between bank mutations and internal finance records</div>
    <div class="badge">DEMO · BCA MUTASI REKENING</div>
</div>
""", unsafe_allow_html=True)

# ── File Upload ────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="section-header">🏦 Bank Document</div>', unsafe_allow_html=True)
    bank_file = st.file_uploader(
        "Upload bank mutation (PDF or Excel)",
        type=["pdf", "xlsx", "xls"],
        key="bank_upload",
        help="BCA/Mandiri/BRI mutasi rekening in PDF or Excel format"
    )
    if bank_file:
        st.success(f"✓ {bank_file.name} ({bank_file.size / 1024:.1f} KB)")

with col2:
    st.markdown('<div class="section-header">📊 Finance Record</div>', unsafe_allow_html=True)
    finance_file = st.file_uploader(
        "Upload finance record (Excel)",
        type=["xlsx", "xls"],
        key="finance_upload",
        help="Internal finance spreadsheet with transaction records"
    )
    if finance_file:
        st.success(f"✓ {finance_file.name} ({finance_file.size / 1024:.1f} KB)")

# ── Run Button ─────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
run_col, _ = st.columns([2, 6])
with run_col:
    run_btn = st.button("🚀 Run Comparison", use_container_width=True, type="primary")

# ── Processing ─────────────────────────────────────────────────────────────────
if run_btn:
    if not bank_file or not finance_file:
        st.error("Please upload both documents before running the comparison.")
        st.stop()

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        st.error("Please enter your Gemini API key in the sidebar first.")
        st.stop()

    # Import here so API key is set
    from app.parser.gemini_parser import parse_document
    from app.matcher.match_engine import match_transactions, get_summary_stats
    from app.report.generate_report import generate_excel_report, generate_pdf_report

    progress = st.progress(0, text="Starting...")
    status_box = st.empty()

    try:
        # ── Step 1: Parse bank document ────────────────────────────────────
        status_box.info("📄 Step 1/4 — Parsing bank document with Gemini AI...")
        progress.progress(10, text="Parsing bank document...")
        bank_bytes = bank_file.read()
        bank_df = parse_document(bank_bytes, bank_file.name, doc_type='bank')
        progress.progress(35, text="Bank document parsed ✓")
        status_box.success(f"✅ Parsed {len(bank_df)} transactions from bank document")

        # ── Step 2: Parse finance document ────────────────────────────────
        status_box.info("📊 Step 2/4 — Parsing finance record...")
        progress.progress(40, text="Parsing finance record...")
        finance_bytes = finance_file.read()
        finance_df = parse_document(finance_bytes, finance_file.name, doc_type='finance')
        progress.progress(60, text="Finance record parsed ✓")
        status_box.success(f"✅ Parsed {len(finance_df)} records from finance document")

        # ── Step 3: Match transactions ─────────────────────────────────────
        status_box.info("🔄 Step 3/4 — Running matching engine...")
        progress.progress(65, text="Matching transactions...")

        # Override tolerances from sidebar
        from app.utils import config as cfg
        cfg.FUZZY_THRESHOLD = fuzzy_threshold
        cfg.AMOUNT_TOLERANCE_PCT = amount_tolerance

        # Patch date tolerance
        import app.matcher.match_engine as me
        me.DATE_TOLERANCE_DAYS = date_tolerance

        result_df = match_transactions(bank_df, finance_df, fuzzy_threshold, amount_tolerance)
        stats = get_summary_stats(result_df)
        progress.progress(85, text="Generating reports...")

        # ── Step 4: Generate reports ───────────────────────────────────────
        status_box.info("📝 Step 4/4 — Generating reports...")
        excel_bytes = generate_excel_report(result_df, stats)
        pdf_bytes = generate_pdf_report(result_df, stats)
        progress.progress(100, text="Done!")
        status_box.empty()
        progress.empty()

        # ── Store in session ───────────────────────────────────────────────
        st.session_state['result_df'] = result_df
        st.session_state['stats'] = stats
        st.session_state['bank_df'] = bank_df
        st.session_state['finance_df'] = finance_df
        st.session_state['excel_bytes'] = excel_bytes
        st.session_state['pdf_bytes'] = pdf_bytes

        st.success("✅ Comparison complete!")

    except ValueError as e:
        progress.empty()
        status_box.empty()
        st.error(f"❌ Error: {e}")
        if "GEMINI_API_KEY" in str(e):
            st.info("💡 Enter your Gemini API key in the left sidebar.")
        st.stop()
    except Exception as e:
        progress.empty()
        status_box.empty()
        st.error(f"❌ Unexpected error: {e}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        st.stop()


# ── Results Display ────────────────────────────────────────────────────────────
if 'result_df' in st.session_state:
    result_df = st.session_state['result_df']
    stats = st.session_state['stats']

    st.markdown("---")

    # ── KPI Cards ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card kpi-total">
            <div class="kpi-label">Total Records</div>
            <div class="kpi-value">{stats['total_records']}</div>
            <div class="kpi-sub">processed</div>
        </div>
        <div class="kpi-card kpi-exact">
            <div class="kpi-label">Exact Matches</div>
            <div class="kpi-value">{stats['exact_matches']}</div>
            <div class="kpi-sub">{stats['exact_rate_pct']}% of total</div>
        </div>
        <div class="kpi-card kpi-fuzzy">
            <div class="kpi-label">Fuzzy Matches</div>
            <div class="kpi-value">{stats['fuzzy_matches']}</div>
            <div class="kpi-sub">partial matches</div>
        </div>
        <div class="kpi-card kpi-unmatch">
            <div class="kpi-label">Unmatched</div>
            <div class="kpi-value">{stats['unmatched_bank'] + stats['unmatched_finance']}</div>
            <div class="kpi-sub">need review</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Amount summary ─────────────────────────────────────────────────────
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.metric("Bank Total", f"Rp {stats['total_bank_amount']:,.0f}")
    with ac2:
        st.metric("Finance Total", f"Rp {stats['total_finance_amount']:,.0f}")
    with ac3:
        delta_color = "off" if stats['amount_discrepancy'] == 0 else "inverse"
        st.metric("Discrepancy", f"Rp {stats['amount_discrepancy']:,.0f}", delta="0" if stats['amount_discrepancy'] == 0 else f"Rp {stats['amount_discrepancy']:,.0f}")

    # ── Match rate progress ────────────────────────────────────────────────
    st.markdown(f'<div class="section-header">Overall Match Rate: {stats["match_rate_pct"]}%</div>', unsafe_allow_html=True)
    st.progress(stats['match_rate_pct'] / 100)

    # ── Tabs ──────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 All Results",
        "✅ Exact Matches",
        "⚠️ Fuzzy Matches",
        "❌ Unmatched",
        "📄 Source Data"
    ])

    def _format_df_display(df: pd.DataFrame) -> pd.DataFrame:
        """Prepare DataFrame for display."""
        d = df.copy()
        for col in ['bank_date', 'finance_date']:
            if col in d.columns:
                d[col] = pd.to_datetime(d[col]).dt.strftime('%d/%m/%Y').fillna('')
        for col in ['bank_amount', 'finance_amount']:
            if col in d.columns:
                d[col] = d[col].apply(lambda x: f"Rp {x:,.0f}" if x > 0 else '-')
        if 'match_confidence' in d.columns:
            d['match_confidence'] = d['match_confidence'].apply(lambda x: f"{x:.1%}" if x > 0 else '-')
        return d

    DISPLAY_COLS = [
        'bank_date', 'bank_description', 'bank_amount',
        'finance_date', 'finance_description', 'finance_amount',
        'finance_invoice', 'match_status', 'match_confidence', 'notes'
    ]

    with tab1:
        st.markdown(f'<div class="section-header">All {len(result_df)} records</div>', unsafe_allow_html=True)
        disp = _format_df_display(result_df[[c for c in DISPLAY_COLS if c in result_df.columns]])
        st.dataframe(disp, use_container_width=True, height=420)

    with tab2:
        exact = result_df[result_df['match_status'] == 'exact']
        st.markdown(f'<div class="section-header">{len(exact)} exact matches</div>', unsafe_allow_html=True)
        if len(exact) > 0:
            st.dataframe(_format_df_display(exact[[c for c in DISPLAY_COLS if c in exact.columns]]), use_container_width=True, height=420)
        else:
            st.info("No exact matches found.")

    with tab3:
        fuzzy = result_df[result_df['match_status'] == 'fuzzy']
        st.markdown(f'<div class="section-header">{len(fuzzy)} fuzzy matches — review recommended</div>', unsafe_allow_html=True)
        if len(fuzzy) > 0:
            st.dataframe(_format_df_display(fuzzy[[c for c in DISPLAY_COLS if c in fuzzy.columns]]), use_container_width=True, height=420)
        else:
            st.info("No fuzzy matches found.")

    with tab4:
        unmatch = result_df[result_df['match_status'].isin(['unmatched', 'unmatched_finance'])]
        st.markdown(f'<div class="section-header">{len(unmatch)} unmatched transactions</div>', unsafe_allow_html=True)
        if len(unmatch) > 0:
            st.warning(f"⚠️ {len(unmatch)} transactions need manual review")
            st.dataframe(_format_df_display(unmatch[[c for c in DISPLAY_COLS if c in unmatch.columns]]), use_container_width=True, height=420)
        else:
            st.success("🎉 All transactions matched!")

    with tab5:
        sc1, sc2 = st.columns(2)
        bank_df = st.session_state['bank_df']
        finance_df = st.session_state['finance_df']
        with sc1:
            st.markdown(f'<div class="section-header">Bank ({len(bank_df)} rows)</div>', unsafe_allow_html=True)
            bd = bank_df.copy()
            bd['date'] = pd.to_datetime(bd['date']).dt.strftime('%d/%m/%Y')
            bd['amount'] = bd['amount'].apply(lambda x: f"Rp {x:,.0f}")
            st.dataframe(bd, use_container_width=True, height=350)
        with sc2:
            st.markdown(f'<div class="section-header">Finance ({len(finance_df)} rows)</div>', unsafe_allow_html=True)
            fd = finance_df.copy()
            fd['date'] = pd.to_datetime(fd['date']).dt.strftime('%d/%m/%Y')
            fd['amount'] = fd['amount'].apply(lambda x: f"Rp {x:,.0f}")
            st.dataframe(fd, use_container_width=True, height=350)

    # ── Download Buttons ───────────────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-header">📥 Download Reports</div>', unsafe_allow_html=True)
    dl1, dl2, _ = st.columns([2, 2, 4])

    from datetime import datetime
    ts = datetime.now().strftime('%Y%m%d_%H%M')

    with dl1:
        st.download_button(
            label="📊 Download Excel Report",
            data=st.session_state['excel_bytes'],
            file_name=f"txn_comparison_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            label="📄 Download PDF Summary",
            data=st.session_state['pdf_bytes'],
            file_name=f"txn_summary_{ts}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

# ── Empty state ────────────────────────────────────────────────────────────────
else:
    st.markdown("""
    <div style="text-align:center; padding: 3rem; color: #475569;">
        <div style="font-size:3rem; margin-bottom:1rem">📁</div>
        <div style="font-size:1.1rem; font-weight:600; color:#94a3b8">Upload your documents to get started</div>
        <div style="font-size:0.85rem; margin-top:0.5rem">
            1. Upload the bank mutation PDF or Excel<br>
            2. Upload the finance record Excel<br>
            3. Enter your Gemini API key in the sidebar<br>
            4. Click <b>Run Comparison</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
