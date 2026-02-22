"""
KSERC Truing-Up Analysis Tool
==============================
Streamlit UI for automated analysis of KSEB truing-up petitions.
Upload PDF → Instant traffic light analysis.
"""

import streamlit as st
import tempfile
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="KSERC Truing-Up Analysis Tool",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────────────────
# STYLING
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Overall background */
    .main { background-color: #f8f9fa; }

    /* Header */
    .kserc-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2e6da4 100%);
        padding: 1.5rem 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .kserc-header h1 { color: white; font-size: 1.8rem; margin: 0; }
    .kserc-header p  { color: #cce0f5; margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    /* Traffic light cards */
    .card-green  { background:#d4edda; border-left:5px solid #28a745;
                   border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
    .card-yellow { background:#fff3cd; border-left:5px solid #ffc107;
                   border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
    .card-red    { background:#f8d7da; border-left:5px solid #dc3545;
                   border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
    .card-grey   { background:#e9ecef; border-left:5px solid #6c757d;
                   border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem; }

    /* Flag badges */
    .badge-green  { background:#28a745; color:white; padding:2px 10px;
                    border-radius:12px; font-size:0.78rem; font-weight:600; }
    .badge-yellow { background:#ffc107; color:#333; padding:2px 10px;
                    border-radius:12px; font-size:0.78rem; font-weight:600; }
    .badge-red    { background:#dc3545; color:white; padding:2px 10px;
                    border-radius:12px; font-size:0.78rem; font-weight:600; }

    /* Summary metrics */
    .metric-box {
        background:white; border-radius:10px; padding:1rem;
        text-align:center; box-shadow:0 1px 4px rgba(0,0,0,0.08);
    }
    .metric-box .value { font-size:2rem; font-weight:700; }
    .metric-box .label { font-size:0.8rem; color:#666; margin-top:2px; }

    /* Section headers */
    .section-header {
        font-size:1rem; font-weight:600; color:#1a3a5c;
        border-bottom:2px solid #2e6da4; padding-bottom:4px;
        margin:1.2rem 0 0.8rem 0;
    }

    /* Constants panel */
    .const-source { font-size:0.75rem; color:#888; font-style:italic; }

    /* Sidebar */
    .sidebar-section { font-weight:600; color:#1a3a5c; margin-top:1rem; }

    /* Step indicators */
    .step-complete { color:#28a745; font-weight:600; }
    .step-running  { color:#ffc107; font-weight:600; }
    .step-pending  { color:#aaa; }

    /* Disclaimer */
    .disclaimer {
        background:#e8f4f8; border:1px solid #bee5eb;
        border-radius:6px; padding:0.7rem 1rem;
        font-size:0.82rem; color:#0c5460; margin-top:1rem;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="kserc-header">
    <h1>⚡ KSERC Truing-Up Analysis Tool</h1>
    <p>Automated first-cut analysis of KSEB truing-up petitions &nbsp;|&nbsp;
       Kerala State Electricity Regulatory Commission &nbsp;|&nbsp; Beta v2.0 (All SBUs)</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR — CONSTANTS PANEL
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Regulatory Constants")
    st.markdown(
        "Values from KSERC MYT Order 2022 and RBI/CSO indices. "
        "Edit if updated values are available before running analysis.",
        unsafe_allow_html=False
    )

    st.markdown("---")

    # --- Inflation ---
    st.markdown("**📊 Inflation Indices (2024-25)**")
    st.caption("Source: RBI / CSO — Table D.571")
    cpi_old  = st.number_input("CPI 2023-24 (base 2001=100)", value=397.25, step=0.01, format="%.2f")
    cpi_new  = st.number_input("CPI 2024-25 (base 2001=100)", value=410.64, step=0.01, format="%.2f")
    wpi_old  = st.number_input("WPI 2023-24 (base 2011-12)", value=151.40, step=0.01, format="%.2f")
    wpi_new  = st.number_input("WPI 2024-25 (base 2011-12)", value=154.90, step=0.01, format="%.2f")

    st.markdown("---")

    # --- Interest rates ---
    st.markdown("**💰 Interest Rates**")
    st.caption("Source: MYT Order 2022 / SBI")
    sbi_eblr = st.number_input("SBI EBLR (%)", value=7.55, step=0.01, format="%.2f")
    gpf_rate = st.number_input("GPF Interest Rate (%)", value=7.10, step=0.01, format="%.2f")

    st.markdown("---")

    # --- GPF Balances ---
    st.markdown("**🏦 GPF Balances 2024-25**")
    st.caption("Source: Table 5.27, MYT Order 2022")
    gpf_open  = st.number_input("Opening GPF Balance (Cr)", value=3364.32, step=0.01, format="%.2f")
    gpf_close = st.number_input("Closing GPF Balance (Cr)", value=3454.32, step=0.01, format="%.2f")

    st.markdown("---")

    # --- Allocation ratios ---
    st.markdown("**👥 SBU-G Allocation Ratios**")
    st.caption("Source: Table 4.51, MYT Order 2022")
    emp_ratio = st.number_input("Employee Strength Ratio (%)", value=5.40, step=0.01, format="%.2f")

    st.markdown("---")

    # --- O&M base ---
    st.markdown("**🔧 O&M Base Year**")
    st.caption("Source: TU Order 14.06.2022")
    om_base = st.number_input("O&M Base Year Amount (Cr)", value=156.16, step=0.01, format="%.2f")

    st.markdown("---")

    # --- Master Trust ---
    st.markdown("**📋 Master Trust Bond Interest**")
    st.caption("Source: Table 4.51, MYT Order 2022")
    mt_total = st.number_input("Total Company Bond Interest 2024-25 (Cr)", value=529.36, step=0.01, format="%.2f")
    mt_approved = st.number_input("MYT Approved SBU-G Share 2024-25 (Cr)", value=28.59, step=0.01, format="%.2f")

    st.markdown("---")

    # --- NTI ---
    st.markdown("**📈 Non-Tariff Income Baseline**")
    st.caption("Source: Table 4.61, MYT Order 2022")
    nti_baseline = st.number_input("MYT Approved NTI SBU-G 2024-25 (Cr)", value=11.35, step=0.01, format="%.2f")

    st.markdown("---")
    st.markdown(
        '<div class="disclaimer">⚠️ These constants are fixed for MYT period '
        '2022-27. Update only if KSERC has issued a corrigendum or revised '
        'order. Changes here override hardcoded values for this run only.</div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN — UPLOAD + RUN
# ─────────────────────────────────────────────────────────────────────────────

col_upload, col_info = st.columns([2, 1])

with col_upload:
    st.markdown('<div class="section-header">📄 Upload Petition PDF</div>',
                unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload KSEB Truing-Up Petition (PDF)",
        type=["pdf"],
        help="Upload the KSEB truing-up petition PDF. "
             "The tool will automatically extract all SBU-G line items."
    )

with col_info:
    st.markdown('<div class="section-header">ℹ️ Tool Scope (v2.0)</div>',
                unsafe_allow_html=True)
    st.markdown("""
    **Coverage:** SBU-G · SBU-T · SBU-D (All 3 SBUs)
    **Petition format:** 2024-25 standardised format
    **Line items:** 35+ across all SBUs
    
    ⚠️ *This is a first-cut analysis tool.
    All recommendations require staff review
    before regulatory orders are issued.*
    """)

# ─────────────────────────────────────────────────────────────────────────────
# RUN ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

if uploaded_file:
    run_col, _ = st.columns([1, 3])
    with run_col:
        run_button = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    if run_button:
        # Save uploaded PDF to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        # ── VALIDATION: Check this is a KSEB truing-up petition ──
        def validate_kseb_petition(pdf_path: str) -> tuple:
            """
            Returns (is_valid: bool, message: str, details: dict)
            Validates this is a KSEB truing-up petition, not MYT order or other doc.
            """
            try:
                import pdfplumber

                # Level 0: First-page identity check
                # KSEB petition: opens with petitioner name/address ("KSEB Ltd", "Vydyuthi Bhavanam")
                # KSERC order:   opens with commission identity ("Kerala State Electricity
                #                Regulatory Commission", "KSERC", "Before the Commission")
                # This is the strongest signal — check first 2 pages only.
                kserc_authority_opening = [
                    'kerala state electricity regulatory commission',
                    'before the kerala state electricity regulatory commission',
                    'the kerala state electricity regulatory commission',
                    'kserc order',
                    'regulatory commission order',
                ]
                found_commission_opening = set()

                with pdfplumber.open(pdf_path) as pdf:
                    page_count = len(pdf.pages)
                    for page in pdf.pages[:2]:
                        text = (page.extract_text() or '').lower()
                        for kw in kserc_authority_opening:
                            if kw in text:
                                found_commission_opening.add(kw)

                if found_commission_opening:
                    return False, (
                        "This appears to be a KSERC Order, not a KSEB petition. "
                        "A KSERC order opens with the Commission's name and authority. "
                        "A KSEB petition opens with KSEB Ltd's name and address. "
                        "Please upload the petition filed BY KSEB, not the order issued BY KSERC."
                    ), {'pages': page_count, 'opening_indicators': list(found_commission_opening)}

                # Level 1b: Must be specifically KSEB/KSEBL — not another utility
                kseb_entity_keywords = [
                    'kerala state electricity board',
                    'kseb ltd',
                    'kseb limited',
                    'ksebl',
                    'kseb',
                    'thiruvananthapuram',
                    'trivandrum',
                    'kerala electricity',
                    'vydyuthi bhavanam',
                    'pattom'
                ]

                # Level 2: Truing-up specific — these appear in ARR table headers
                # MYT orders will NOT have these column headers
                tu_specific = [
                    'tu sought',
                    'truing up sought',
                    'actuals',
                    'arr approval',
                    'actual expenditure'
                ]

                # Level 3: Must NOT be a KSERC order of any kind
                # (MYT order, truing-up order, tariff order etc.)
                # Key tell: KSERC orders refer to KSEB as "the petitioner"
                # and use commission-speaks language. Petitions never do this.
                order_indicators = [
                    # MYT order language
                    'it is hereby ordered',
                    'the commission hereby orders',
                    'this order shall come into force',
                    'kserc order no',
                    'the commission directs',
                    # Truing-up ORDER language (KSERC speaking about KSEB)
                    'the petitioner has claimed',
                    'the petitioner has submitted',
                    'the commission has examined',
                    'the commission has considered',
                    'the commission notes',
                    'the commission allows',
                    'the commission disallows',
                    'the commission approves',
                    'the commission observed',
                    'truing up order',
                    'order in petition',
                    'op no.',
                    'commission finds',
                    'commission is of the view',
                    'accordingly the commission',
                    'the above petition',
                ]

                found_required   = set()
                found_tu         = set()
                found_order      = set()
                found_entity     = set()
                page_count       = 0

                with pdfplumber.open(pdf_path) as pdf:
                    page_count = len(pdf.pages)
                    pages_to_check = min(40, page_count)
                    for page in pdf.pages[:pages_to_check]:
                        text = (page.extract_text() or '').lower()
                        for kw in required_keywords:
                            if kw in text:
                                found_required.add(kw)
                        for kw in tu_specific:
                            if kw in text:
                                found_tu.add(kw)
                        for kw in order_indicators:
                            if kw in text:
                                found_order.add(kw)
                        for kw in kseb_entity_keywords:
                            if kw in text:
                                found_entity.add(kw)

                # Reject KSERC orders (MYT, truing-up, tariff — any order)
                if found_order:
                    return False, (
                        "This appears to be a KSERC Order, not a KSEB truing-up petition. "
                        "This tool only accepts the petition filed BY KSEB, not the order "
                        "issued BY KSERC. Please upload the KSEB truing-up petition PDF."
                    ), {'pages': page_count, 'order_indicators': list(found_order)}

                # Must be KSEB Ltd specifically
                if not found_entity:
                    return False, (
                        "This does not appear to be a KSEB Ltd petition. "
                        "This tool is calibrated specifically for KSEB Ltd (Kerala). "
                        "Petitions from other utilities are not supported."
                    ), {'pages': page_count}

                # Must have required keywords
                missing = set(required_keywords) - found_required
                if missing:
                    return False, (
                        f"This does not appear to be a KSEB truing-up petition. "
                        f"Required identifiers not found: {', '.join(missing).upper()}."
                    ), {'pages': page_count}

                # Must have at least 1 truing-up specific term
                if not found_tu:
                    return False, (
                        "This PDF does not contain truing-up petition content "
                        "(ARR table with actuals and TU Sought columns not found). "
                        "Please upload the correct KSEB truing-up petition."
                    ), {'pages': page_count}

                return True, "Valid KSEB truing-up petition detected.", {
                    'pages': page_count,
                    'tu_keywords_found': list(found_tu),
                    'entity_confirmed': list(found_entity)
                }

            except Exception as e:
                return False, f"Could not read PDF: {e}", {}

        # Run validation
        st.markdown("---")
        with st.spinner("Validating PDF..."):
            is_valid, val_message, val_details = validate_kseb_petition(tmp_path)

        if not is_valid:
            st.error(f"❌ Invalid File: {val_message}")
            st.info("💡 This tool only accepts KSEB truing-up petition PDFs in the standard format.")
            os.unlink(tmp_path)
            st.stop()

        # Override constants from sidebar into environment
        # (pipeline reads from kserc_constants but we patch at runtime)
        try:
            import kserc_constants as KC
            KC.CPI['2023-24']            = cpi_old
            KC.CPI['2024-25']            = cpi_new
            KC.WPI['2023-24']            = wpi_old
            KC.WPI['2024-25']            = wpi_new
            KC.SBI_EBLR_RATE             = sbi_eblr
            KC.GPF_INTEREST_RATE         = gpf_rate
            KC.GPF_OPENING_BALANCE['2024-25'] = gpf_open
            KC.GPF_CLOSING_BALANCE['2024-25'] = gpf_close
            KC.SBU_G_EMPLOYEE_RATIO      = emp_ratio
            KC.SBU_G_GPF_RATIO           = emp_ratio
            KC.OM_BASE_YEAR_SBU_G        = om_base
            KC.MT_BOND_TOTAL_COMPANY['2024-25']  = mt_total
            KC.MT_BOND_APPROVED_SBU_G['2024-25'] = mt_approved
            KC.NTI_BASELINE_SBU_G['2024-25']     = nti_baseline
        except Exception as e:
            st.warning(f"Could not override constants: {e}")

        # Progress display
        st.markdown("---")
        st.markdown("### ⏳ Processing...")
        prog = st.progress(0)
        status = st.empty()

        try:
            status.markdown("**Step 1/3:** Parsing PDF and extracting tables...")
            prog.progress(10)

            from integration_pipeline import process_petition
            import io
            from contextlib import redirect_stdout

            # Capture stdout so pipeline logs don't flood the UI
            f_out = io.StringIO()
            with redirect_stdout(f_out):
                results = process_petition(tmp_path)

            prog.progress(80)
            status.markdown("**Step 2/3:** Running heuristics...")

            # ── CONFIDENCE GATE: Check extraction quality ──
            # If fewer than 6/10 line items have real claimed values,
            # the PDF is likely not a valid petition — reject results
            line_items_check = results.get('line_items', {})
            items_with_data = sum(
                1 for item in line_items_check.values()
                if (item.get('claimed_value') or
                    item.get('primary_heuristic', {}).get('claimed_value') or 0) > 0.5
            )
            if items_with_data < 6:
                st.error(
                    f"❌ Extraction failed: Only {items_with_data}/10 SBU-G line items could be "
                    f"extracted from this PDF. This may not be a valid KSEB SBU-G "
                    f"truing-up petition, or the format may differ from the expected "
                    f"2024-25 standard. Please verify the file and try again."
                )
                st.stop()

            # ── EXTRACTION QUALITY: SBU-T ──
            sbu_t_check = results.get('sbu_t', {})
            sbu_t_items_check = sbu_t_check.get('line_items', [])
            sbu_t_with_data = sum(
                1 for i in sbu_t_items_check
                if (i.get('claimed') or 0) > 0.5
            )
            if not sbu_t_items_check:
                st.error(
                    "❌ SBU-T Extraction Failed: No transmission line items could be "
                    "extracted. SBU-T results will be missing — do NOT treat the "
                    "SBU-G and SBU-D results as a complete analysis."
                )
            elif sbu_t_with_data < 4:
                st.warning(
                    f"⚠️ SBU-T Partial Extraction: Only {sbu_t_with_data} of "
                    f"{len(sbu_t_items_check)} SBU-T line items have data. "
                    f"Transmission analysis may be incomplete — verify manually "
                    f"before relying on consolidated totals."
                )

            # ── EXTRACTION QUALITY: SBU-D ──
            sbu_d_check = results.get('sbu_d', {})
            sbu_d_items_check = sbu_d_check.get('line_items', [])
            sbu_d_with_data = sum(
                1 for i in sbu_d_items_check
                if (i.get('claimed') or 0) > 0.5
            )
            if not sbu_d_items_check:
                st.error(
                    "❌ SBU-D Extraction Failed: No distribution line items could be "
                    "extracted. SBU-D holds ~89% of total ARR — do NOT treat the "
                    "consolidated totals as valid without this data."
                )
            elif sbu_d_with_data < 6:
                st.warning(
                    f"⚠️ SBU-D Partial Extraction: Only {sbu_d_with_data} of "
                    f"{len(sbu_d_items_check)} SBU-D line items have data. "
                    f"Distribution analysis may be incomplete — consolidated "
                    f"excess figures will be understated."
                )

            # ── CONSOLIDATED INTEGRITY CHECK ──
            consolidated_check = results.get('consolidated_summary', {})
            total_excess = consolidated_check.get('company_totals', {}).get('total_excess', 0) or 0
            extraction_warnings = (
                (not sbu_t_items_check) or
                (not sbu_d_items_check) or
                sbu_t_with_data < 4 or
                sbu_d_with_data < 6
            )
            if extraction_warnings and total_excess > 0:
                st.error(
                    "⛔ WARNING: Consolidated totals are unreliable due to extraction "
                    "failures above. The ₹{:,.0f} Cr excess figure shown is a "
                    "PARTIAL figure only. Manual review of unextracted sections "
                    "is mandatory before any regulatory order is drafted.".format(total_excess)
                )

            # ── FISCAL YEAR CHECK ──
            detected_fy = results.get('metadata', {}).get('fiscal_year', '')
            expected_fy = '2024-25'
            if detected_fy and detected_fy != expected_fy:
                st.error(
                    f"❌ Wrong Petition Year: This tool is calibrated for "
                    f"**{expected_fy}** but the uploaded petition appears to be for "
                    f"**{detected_fy}**. Constants (CPI, WPI, GPF balances, loan rates) "
                    f"will not match. Please upload the {expected_fy} petition."
                )
                st.stop()

            prog.progress(95)
            status.markdown("**Step 3/3:** Generating report...")
            prog.progress(100)
            status.markdown("✅ **Analysis complete!**")
            prog.progress(100)
            status.markdown("✅ **Analysis complete!**")

        except Exception as e:
            st.error(f"❌ Analysis failed: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.stop()
        finally:
            os.unlink(tmp_path)

        st.markdown("---")

        # ─────────────────────────────────────────────────────────────────────
        # RESULTS
        # ─────────────────────────────────────────────────────────────────────

        line_items = results.get('line_items', {})
        meta       = results.get('metadata', {})

        # ── Extraction status banner ──
        sbu_t_items_disp = results.get('sbu_t', {}).get('line_items', [])
        sbu_d_items_disp = results.get('sbu_d', {}).get('line_items', [])
        sbu_t_ok = len([i for i in sbu_t_items_disp if (i.get('claimed') or 0) > 0.5]) >= 4
        sbu_d_ok = len([i for i in sbu_d_items_disp if (i.get('claimed') or 0) > 0.5]) >= 6

        if sbu_t_ok and sbu_d_ok:
            st.success("✅ All three SBUs extracted successfully — results are complete.")
        else:
            missing = []
            if not sbu_t_ok: missing.append("SBU-T (Transmission)")
            if not sbu_d_ok: missing.append("SBU-D (Distribution)")
            st.error(
                f"⛔ INCOMPLETE ANALYSIS — {', '.join(missing)} data could not be fully "
                f"extracted. Consolidated totals are PARTIAL. Do not use these figures "
                f"for regulatory orders without manual verification of the missing sections."
            )

        # ── Petition metadata ──
        st.markdown(f"""
        <div style="background:white;border-radius:8px;padding:0.8rem 1.2rem;
             box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:1rem;">
        📁 <b>Petition:</b> {uploaded_file.name} &nbsp;|&nbsp;
        📅 <b>Fiscal Year:</b> {meta.get('fiscal_year','2024-25')} &nbsp;|&nbsp;
        📄 <b>Pages:</b> {meta.get('num_pages','—')} &nbsp;|&nbsp;
        🕐 <b>Analysed:</b> {datetime.now().strftime('%d %b %Y, %H:%M')}
        </div>
        """, unsafe_allow_html=True)

        # ── Summary metrics ──
        def get_flag(item):
            if item.get('flag'):
                return item['flag']
            ph = item.get('primary_heuristic', {})
            return ph.get('flag', 'UNKNOWN')

        flags = [get_flag(v) for v in line_items.values()
                 if v.get('status') not in ['skipped','error']]
        n_green  = flags.count('GREEN')
        n_yellow = flags.count('YELLOW')
        n_red    = flags.count('RED')

        # Total claimed vs allowable
        def get_claimed(item):
            return (item.get('claimed_value') or
                    item.get('primary_heuristic', {}).get('claimed_value') or 0)
        def get_allowable(item):
            return (item.get('allowable_value') or
                    item.get('primary_heuristic', {}).get('allowable_value') or 0)

        total_claimed   = sum(get_claimed(v)   for v in line_items.values())
        total_allowable = sum(get_allowable(v) for v in line_items.values())
        potential_savings = total_claimed - total_allowable

        st.markdown('<div class="section-header">📊 Summary</div>', unsafe_allow_html=True)

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        with m1:
            st.markdown(f"""<div class="metric-box">
                <div class="value" style="color:#28a745">{n_green}</div>
                <div class="label">✅ GREEN</div></div>""", unsafe_allow_html=True)
        with m2:
            st.markdown(f"""<div class="metric-box">
                <div class="value" style="color:#ffc107">{n_yellow}</div>
                <div class="label">🟡 YELLOW</div></div>""", unsafe_allow_html=True)
        with m3:
            st.markdown(f"""<div class="metric-box">
                <div class="value" style="color:#dc3545">{n_red}</div>
                <div class="label">🔴 RED</div></div>""", unsafe_allow_html=True)
        with m4:
            st.markdown(f"""<div class="metric-box">
                <div class="value">₹{total_claimed:.0f}</div>
                <div class="label">Total Claimed (Cr)</div></div>""", unsafe_allow_html=True)
        with m5:
            st.markdown(f"""<div class="metric-box">
                <div class="value">₹{total_allowable:.0f}</div>
                <div class="label">Total Allowable (Cr)</div></div>""", unsafe_allow_html=True)
        with m6:
            savings_color = "#dc3545" if potential_savings > 0 else "#28a745"
            st.markdown(f"""<div class="metric-box">
                <div class="value" style="color:{savings_color}">
                    ₹{abs(potential_savings):.0f}</div>
                <div class="label">{'Excess Claimed (Cr)' if potential_savings > 0 else 'Under-claimed (Cr)'}</div>
                </div>""", unsafe_allow_html=True)

        # ── Per line item results ──
        st.markdown('<div class="section-header">🔍 Line Item Analysis</div>',
                    unsafe_allow_html=True)

        DISPLAY_NAMES = {
            'roe':               'Return on Equity (ROE)',
            'depreciation':      'Depreciation',
            'fuel_costs':        'Fuel Costs',
            'om_expenses':       'O&M Expenses',
            'ifc':               'Interest & Finance Charges',
            'master_trust':      'Master Trust Bond Interest',
            'nti':               'Non-Tariff Income',
            'intangibles':       'Intangible Assets (Amortisation)',
            'other_expenses':    'Other Expenses',
            'exceptional_items': 'Exceptional Items',
        }

        FLAG_CARD  = {'GREEN':'card-green','YELLOW':'card-yellow','RED':'card-red'}
        FLAG_BADGE = {
            'GREEN':  '<span class="badge-green">✅ GREEN</span>',
            'YELLOW': '<span class="badge-yellow">🟡 YELLOW</span>',
            'RED':    '<span class="badge-red">🔴 RED</span>',
        }
        FLAG_EMOJI = {'GREEN':'✅','YELLOW':'🟡','RED':'🔴'}

        for key, display_name in DISPLAY_NAMES.items():
            item = line_items.get(key, {})
            if not item or item.get('status') in ['skipped','error']:
                continue

            flag      = get_flag(item)
            claimed   = get_claimed(item)
            allowable = get_allowable(item)
            variance  = ((claimed - allowable) / allowable * 100
                         if allowable else 0)
            card_cls  = FLAG_CARD.get(flag, 'card-grey')
            badge     = FLAG_BADGE.get(flag, flag)
            emoji     = FLAG_EMOJI.get(flag, '⚪')

            with st.expander(
                f"{emoji}  {display_name}  —  "
                f"Claimed: ₹{claimed:.2f} Cr  |  "
                f"Allowable: ₹{allowable:.2f} Cr  |  "
                f"Variance: {variance:+.1f}%",
                expanded=(flag == 'RED')
            ):
                # Is it a chain (O&M or IFC)?
                is_chain = (item.get('status') == 'complete' and
                            'primary_heuristic' in item)

                primary = item.get('primary_heuristic', item)
                rec_text = (primary.get('recommendation_text') or
                            primary.get('smart_recommendation', {}).get('reason', ''))

                st.markdown(
                    f'<div class="{card_cls}">'
                    f'<b>{badge}&nbsp;&nbsp;{display_name}</b><br>'
                    f'<span style="font-size:0.85rem">{rec_text[:300]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )

                # Numbers row
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Claimed (Cr)",   f"₹{claimed:.2f}")
                c2.metric("Allowable (Cr)", f"₹{allowable:.2f}")
                c3.metric("Variance",       f"{variance:+.2f}%")
                action = (primary.get('smart_recommendation', {}).get('action') or
                          ('ACCEPT' if flag == 'GREEN' else
                           'REVIEW' if flag == 'YELLOW' else 'SCRUTINIZE'))
                c4.metric("Recommended Action", action)

                # Sub-components for chains
                supporting = item.get('supporting', {})
                if supporting:
                    st.markdown("**Component Breakdown:**")
                    for sub_key, sub_data in supporting.items():
                        if not sub_data:
                            continue
                        sub_flag  = sub_data.get('flag', 'UNKNOWN')
                        sub_cl    = sub_data.get('claimed_value', 0) or 0
                        sub_al    = sub_data.get('allowable_value', 0) or 0
                        sub_hid   = sub_data.get('heuristic_id', sub_key)
                        sub_badge = FLAG_BADGE.get(sub_flag, sub_flag)
                        sub_rec   = (sub_data.get('recommendation_text') or '')[:120]

                        st.markdown(
                            f"&nbsp;&nbsp;{sub_badge}&nbsp; **{sub_hid}** — "
                            f"Claimed ₹{sub_cl:.2f} Cr → Allowable ₹{sub_al:.2f} Cr<br>"
                            f"<span style='font-size:0.82rem;color:#555'>{sub_rec}</span>",
                            unsafe_allow_html=True
                        )

                # Regulatory basis
                reg_basis = primary.get('regulatory_basis', '')
                if reg_basis:
                    st.caption(f"📜 Regulatory basis: {reg_basis}")

        # ── Next Steps ──
        st.markdown('<div class="section-header">📋 Recommended Next Steps</div>',
                    unsafe_allow_html=True)

        next_steps = []
        if line_items.get('depreciation', {}).get('flag') == 'RED':
            next_steps.append("🔴 **Depreciation**: Request detailed GFA schedule from KSEB. "
                               "Verify normative depreciation calculation per KSERC order.")
        if line_items.get('ifc', {}).get('flag') == 'RED':
            next_steps.append("🔴 **IFC**: Seek confirmation of loan balance, interest rate, "
                               "and WC computation basis from KSEB.")
        if line_items.get('nti', {}).get('flag') == 'YELLOW':
            next_steps.append("🟡 **NTI**: Verify MNRE Performance Incentive of ₹172+ Cr "
                               "against payment advice / audited accounts.")
        if line_items.get('intangibles', {}).get('flag') == 'RED':
            next_steps.append("🔴 **Intangibles**: Software amortisation precedent — "
                               "disallow per prior KSERC order unless KSEB provides "
                               "new justification.")
        if line_items.get('exceptional_items', {}).get('flag') == 'RED':
            next_steps.append("🔴 **Exceptional Items**: Request separate account code "
                               "registers and supporting documents.")
        if not next_steps:
            next_steps.append("✅ No immediate action items — proceed to order drafting.")

        for step in next_steps:
            st.markdown(f"- {step}")

        # ── Disclaimer ──
        st.markdown(
            '<div class="disclaimer">'
            '⚠️ <b>Important:</b> This tool provides an automated first-cut analysis '
            'only. All recommendations must be reviewed and approved by authorised '
            'KSERC staff before being incorporated into regulatory orders. '
            'The tool does not replace professional regulatory judgement.'
            '</div>',
            unsafe_allow_html=True
        )

        # ─────────────────────────────────────────────────────────────────────
        # CONSOLIDATED SUMMARY (All SBUs)
        # ─────────────────────────────────────────────────────────────────────

        consolidated = results.get('consolidated_summary', {})
        sbu_s = consolidated.get('sbu_summaries', {})
        ct    = consolidated.get('company_totals', {})

        if ct:
            st.markdown("---")
            st.markdown('<div class="section-header">🏢 KSEBL Consolidated — All SBUs</div>',
                        unsafe_allow_html=True)

            # SBU breakdown cards
            sbu_col1, sbu_col2, sbu_col3 = st.columns(3)
            sbu_pairs = [
                ('G', 'SBU-G Generation',    '#28a745', sbu_col1),
                ('T', 'SBU-T Transmission',  '#ffc107', sbu_col2),
                ('D', 'SBU-D Distribution',  '#dc3545', sbu_col3),
            ]
            for code, label, color, col in sbu_pairs:
                s = sbu_s.get(code, {})
                exc = (s.get('claimed', 0) or 0) - (s.get('allow', 0) or 0)
                with col:
                    st.markdown(f"""
                    <div class="metric-box">
                      <div class="value" style="color:{color}">+₹{exc:,.0f}</div>
                      <div class="label">{label}</div>
                      <div style="font-size:0.75rem;color:#888;margin-top:4px">
                        Claimed ₹{s.get('claimed',0):,.0f} · Allow ₹{s.get('allow',0):,.0f}
                      </div>
                    </div>""", unsafe_allow_html=True)

            # Company total
            total_c = ct.get('total_claimed', 0) or 0
            total_a = ct.get('total_allow',   0) or 0
            total_e = ct.get('total_excess',  0) or 0
            st.markdown(f"""
            <div style="background:#fff3cd;border-left:5px solid #ffc107;border-radius:8px;
                 padding:0.8rem 1.2rem;margin-top:0.8rem;">
            <b>KSEBL TOTAL:</b>&nbsp; Claimed ₹{total_c:,.2f} Cr &nbsp;|&nbsp;
            Allowable ₹{total_a:,.2f} Cr &nbsp;|&nbsp;
            <span style="color:#dc3545;font-weight:700">Excess +₹{total_e:,.2f} Cr</span>
            </div>""", unsafe_allow_html=True)

            # Top issues
            all_items = consolidated.get('all_items', [])
            top_issues = sorted(
                [i for i in all_items if (i.get('variance', 0) or 0) > 1],
                key=lambda x: x.get('variance', 0), reverse=True
            )[:8]

            if top_issues:
                st.markdown('<div class="section-header">🔝 Top Issues Requiring KSERC Attention</div>',
                            unsafe_allow_html=True)
                for rank, item in enumerate(top_issues, 1):
                    flag = item.get('flag', 'GREY')
                    icon = {'RED': '🔴', 'YELLOW': '🟡', 'GREEN': '✅'}.get(flag, '⬜')
                    var  = item.get('variance', 0) or 0
                    card = 'card-red' if flag == 'RED' else 'card-yellow' if flag == 'YELLOW' else 'card-grey'
                    st.markdown(f"""
                    <div class="{card}">
                    <b>{rank}. {icon} [SBU-{item.get('sbu','?')}] {item.get('name','')}</b><br>
                    <span style="font-size:0.85rem">
                      Claimed ₹{item.get('claimed',0):,.2f} Cr &nbsp;·&nbsp;
                      Allowable ₹{item.get('allowable',0):,.2f} Cr &nbsp;·&nbsp;
                      <b>Excess +₹{var:,.2f} Cr</b>
                    </span>
                    </div>""", unsafe_allow_html=True)

        # ─────────────────────────────────────────────────────────────────────
        # SBU-T RESULTS
        # ─────────────────────────────────────────────────────────────────────

        sbu_t_data   = results.get('sbu_t', {})
        sbu_t_items  = sbu_t_data.get('line_items', [])

        if sbu_t_items:
            st.markdown("---")
            st.markdown('<div class="section-header">🔌 SBU-T Transmission — Line Item Analysis</div>',
                        unsafe_allow_html=True)

            sbu_t_items_clean = [i for i in sbu_t_items
                                 if 'repayment' not in i.get('name','').lower()]
            tc_t = sum(i.get('claimed',0) or 0 for i in sbu_t_items_clean)
            ta_t = sum(i.get('allowable',0) or 0 for i in sbu_t_items_clean)

            tt1, tt2, tt3 = st.columns(3)
            tt1.metric("Claimed (Cr)",   f"₹{tc_t:,.2f}")
            tt2.metric("Allowable (Cr)", f"₹{ta_t:,.2f}")
            tt3.metric("Excess (Cr)",    f"+₹{tc_t-ta_t:,.2f}")

            FLAG_BADGE_T = {
                'GREEN':  '<span class="badge-green">✅ GREEN</span>',
                'YELLOW': '<span class="badge-yellow">🟡 YELLOW</span>',
                'RED':    '<span class="badge-red">🔴 RED</span>',
                'GREY':   '<span>⬜ INFO</span>',
            }
            for item in sbu_t_items_clean:
                name  = item.get('name', '')
                flag  = item.get('flag', 'GREY')
                cl    = item.get('claimed', 0) or 0
                al    = item.get('allowable', 0) or 0
                var   = cl - al
                icon  = {'RED':'🔴','YELLOW':'🟡','GREEN':'✅'}.get(flag,'⬜')
                badge = FLAG_BADGE_T.get(flag, flag)
                card  = {'RED':'card-red','YELLOW':'card-yellow',
                         'GREEN':'card-green'}.get(flag,'card-grey')
                note  = (item.get('note') or '')[:200]

                with st.expander(
                    f"{icon}  {name}  —  Claimed: ₹{cl:.2f} Cr  |  "
                    f"Allowable: ₹{al:.2f} Cr  |  Excess: {var:+.2f} Cr",
                    expanded=(flag == 'RED')
                ):
                    st.markdown(
                        f'<div class="{card}">{badge}&nbsp;&nbsp;<b>{name}</b>'
                        f'{"<br><span style=\'font-size:0.85rem\'>" + note + "</span>" if note else ""}'
                        f'</div>', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Claimed (Cr)",   f"₹{cl:.2f}")
                    c2.metric("Allowable (Cr)", f"₹{al:.2f}")
                    c3.metric("Excess (Cr)",    f"{var:+.2f}")

        # ─────────────────────────────────────────────────────────────────────
        # SBU-D RESULTS
        # ─────────────────────────────────────────────────────────────────────

        sbu_d_data  = results.get('sbu_d', {})
        sbu_d_items = sbu_d_data.get('line_items', [])

        if sbu_d_items:
            st.markdown("---")
            st.markdown('<div class="section-header">🏭 SBU-D Distribution — Line Item Analysis</div>',
                        unsafe_allow_html=True)

            tc_d = sum(i.get('claimed',0) or 0 for i in sbu_d_items)
            ta_d = sum(i.get('allowable',0) or 0 for i in sbu_d_items)

            td1, td2, td3 = st.columns(3)
            td1.metric("Claimed (Cr)",   f"₹{tc_d:,.2f}")
            td2.metric("Allowable (Cr)", f"₹{ta_d:,.2f}")
            td3.metric("Excess (Cr)",    f"+₹{tc_d-ta_d:,.2f}")

            FLAG_BADGE_D = {
                'GREEN':  '<span class="badge-green">✅ GREEN</span>',
                'YELLOW': '<span class="badge-yellow">🟡 YELLOW</span>',
                'RED':    '<span class="badge-red">🔴 RED</span>',
                'GREY':   '<span>⬜ INFO</span>',
            }

            for item in sbu_d_items:
                name  = item.get('name', '')
                flag  = item.get('flag', 'GREY')
                cl    = item.get('claimed', 0) or 0
                al    = item.get('allowable', 0) or 0
                var   = cl - al
                icon  = {'RED':'🔴','YELLOW':'🟡','GREEN':'✅'}.get(flag,'⬜')
                badge = FLAG_BADGE_D.get(flag, flag)
                card  = {'RED':'card-red','YELLOW':'card-yellow',
                         'GREEN':'card-green'}.get(flag,'card-grey')
                note  = (item.get('note') or '')[:200]

                with st.expander(
                    f"{icon}  {name}  —  Claimed: ₹{cl:.2f} Cr  |  "
                    f"Allowable: ₹{al:.2f} Cr  |  Excess: {var:+.2f} Cr",
                    expanded=(flag == 'RED')
                ):
                    st.markdown(
                        f'<div class="{card}">{badge}&nbsp;&nbsp;<b>{name}</b>'
                        f'{"<br><span style=\'font-size:0.85rem\'>" + note + "</span>" if note else ""}'
                        f'</div>', unsafe_allow_html=True)
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Claimed (Cr)",   f"₹{cl:.2f}")
                    c2.metric("Allowable (Cr)", f"₹{al:.2f}")
                    c3.metric("Excess (Cr)",    f"{var:+.2f}")

                    # Power Purchase: show sourcewise breakdown
                    if name == 'Power Purchase Cost':
                        sourcewise = item.get('sourcewise', {})
                        if sourcewise:
                            st.markdown("**Sourcewise Breakdown (D68):**")
                            src_rows = sorted(sourcewise.items(),
                                              key=lambda x: abs(x[1].get('cost_cr',0) or 0),
                                              reverse=True)
                            tbl = "| Source | MU | Cost (₹ Cr) | ₹/unit | Flag |\n"
                            tbl += "|--------|---:|------------:|-------:|------|\n"
                            for key, s in src_rows:
                                mu   = s.get('quantum_mu')
                                cost = s.get('cost_cr', 0) or 0
                                rate = s.get('rate_per_unit')
                                flg  = s.get('flag', 'GREY')
                                lbl  = s.get('label', key)
                                ico  = {'RED':'🔴','YELLOW':'⚠️','GREEN':'✅'}.get(flg,'⬜')
                                mu_s = f"{mu:,.2f}" if mu else '—'
                                rt_s = f"{rate:.2f}" if rate else '—'
                                tbl += f"| {lbl} | {mu_s} | {cost:,.2f} | {rt_s} | {ico} |\n"
                            tbl += f"| **MYT Approved** | | **10,716.26** | | |\n"
                            st.markdown(tbl)
                            st.caption("🔴 >₹60/unit  ⚠️ ₹45-60/unit  ✅ <₹45/unit  ⬜ Pass-through")

        # ── Download JSON ──
        st.markdown("---")
        dl_col, _ = st.columns([1, 3])
        with dl_col:
            # Clean results for JSON export
            def make_serializable(obj):
                if isinstance(obj, dict):
                    return {k: make_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [make_serializable(i) for i in obj]
                elif isinstance(obj, float):
                    return round(obj, 4)
                elif obj is None or isinstance(obj, (int, str, bool)):
                    return obj
                else:
                    return str(obj)

            json_out = json.dumps(make_serializable(results), indent=2)
            st.download_button(
                label="⬇️ Download Full Analysis (JSON)",
                data=json_out,
                file_name=f"KSERC_Analysis_{meta.get('fiscal_year','2024-25')}.json",
                mime="application/json",
                use_container_width=True
            )

else:
    # Empty state
    st.markdown("""
    <div style="text-align:center;padding:3rem;color:#888;">
        <div style="font-size:4rem">📄</div>
        <div style="font-size:1.1rem;margin-top:0.5rem">
            Upload a KSEB truing-up petition PDF to begin analysis
        </div>
        <div style="font-size:0.85rem;margin-top:0.5rem;color:#aaa">
            Supported format: KSEB standard petition PDF (2024-25 format)
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    '<div style="text-align:center;font-size:0.78rem;color:#aaa;">'
    'KSERC Truing-Up Analysis Tool · Beta v2.0 · All SBUs · '
    'Built for Kerala State Electricity Regulatory Commission · 2025'
    '</div>',
    unsafe_allow_html=True
)
