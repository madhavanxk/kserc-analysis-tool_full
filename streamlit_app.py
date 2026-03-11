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
    .main { background-color: #f8f9fa; }

    .kserc-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2e6da4 100%);
        padding: 1.5rem 2rem; border-radius: 10px;
        color: white; margin-bottom: 1.5rem;
    }
    .kserc-header h1 { color: white; font-size: 1.8rem; margin: 0; }
    .kserc-header p  { color: #cce0f5; margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    .card-green  { background:#d4edda; border-left:5px solid #28a745;
                   border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
    .card-yellow { background:#fff3cd; border-left:5px solid #ffc107;
                   border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
    .card-red    { background:#f8d7da; border-left:5px solid #dc3545;
                   border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem; }
    .card-grey   { background:#e9ecef; border-left:5px solid #6c757d;
                   border-radius:8px; padding:1rem 1.2rem; margin-bottom:0.8rem; }

    .badge-green  { background:#28a745; color:white; padding:2px 10px;
                    border-radius:12px; font-size:0.78rem; font-weight:600; }
    .badge-yellow { background:#ffc107; color:#333; padding:2px 10px;
                    border-radius:12px; font-size:0.78rem; font-weight:600; }
    .badge-red    { background:#dc3545; color:white; padding:2px 10px;
                    border-radius:12px; font-size:0.78rem; font-weight:600; }

    .metric-box {
        background:white; border-radius:10px; padding:1rem;
        text-align:center; box-shadow:0 1px 4px rgba(0,0,0,0.08);
    }
    .metric-box .value { font-size:2rem; font-weight:700; }
    .metric-box .label { font-size:0.8rem; color:#666; margin-top:2px; }

    .section-header {
        font-size:1rem; font-weight:600; color:#1a3a5c;
        border-bottom:2px solid #2e6da4; padding-bottom:4px;
        margin:1.2rem 0 0.8rem 0;
    }

    .const-source { font-size:0.75rem; color:#888; font-style:italic; }
    .sidebar-section { font-weight:600; color:#1a3a5c; margin-top:1rem; }
    .step-complete { color:#28a745; font-weight:600; }
    .step-running  { color:#ffc107; font-weight:600; }
    .step-pending  { color:#aaa; }

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

    st.markdown("**📊 Inflation Indices (2024-25)**")
    st.caption("Source: RBI / CSO — Table D.571")
    cpi_old  = st.number_input("CPI 2023-24 (base 2001=100)", value=397.25, step=0.01, format="%.2f")
    cpi_new  = st.number_input("CPI 2024-25 (base 2001=100)", value=410.64, step=0.01, format="%.2f")
    wpi_old  = st.number_input("WPI 2023-24 (base 2011-12)", value=151.40, step=0.01, format="%.2f")
    wpi_new  = st.number_input("WPI 2024-25 (base 2011-12)", value=154.90, step=0.01, format="%.2f")

    st.markdown("---")

    st.markdown("**💰 Interest Rates**")
    st.caption("Source: MYT Order 2022 / SBI")
    sbi_eblr = st.number_input("SBI EBLR (%)", value=7.55, step=0.01, format="%.2f")
    gpf_rate = st.number_input("GPF Interest Rate (%)", value=7.10, step=0.01, format="%.2f")

    st.markdown("---")

    st.markdown("**🏦 GPF Balances 2024-25**")
    st.caption("Source: Table 5.27, MYT Order 2022")
    gpf_open  = st.number_input("Opening GPF Balance (Cr)", value=3364.32, step=0.01, format="%.2f")
    gpf_close = st.number_input("Closing GPF Balance (Cr)", value=3454.32, step=0.01, format="%.2f")

    st.markdown("---")

    st.markdown("**👥 SBU-G Allocation Ratios**")
    st.caption("Source: Table 4.51, MYT Order 2022")
    emp_ratio = st.number_input("Employee Strength Ratio (%)", value=5.13, step=0.01, format="%.2f")

    st.markdown("---")

    st.markdown("**🔧 O&M Base Year**")
    st.caption("Source: TU Order 14.06.2022")
    om_base = st.number_input("O&M Base Year Amount (Cr)", value=156.16, step=0.01, format="%.2f")

    st.markdown("---")

    st.markdown("**📋 Master Trust Bond Interest**")
    st.caption("Source: Table 4.51, MYT Order 2022")
    mt_total   = st.number_input("Total Company Bond Interest 2024-25 (Cr)", value=529.36, step=0.01, format="%.2f")
    mt_approved = st.number_input("MYT Approved SBU-G Share 2024-25 (Cr)", value=28.59, step=0.01, format="%.2f")

    st.markdown("---")

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

    st.markdown("---")
    st.markdown("**📝 Draft Order Generation**")
    st.caption("Powered by Google Gemini Flash (free tier)")
    gemini_api_key = st.text_input(
        "Gemini API Key",
        type="password",
        placeholder="Paste your free Gemini API key here",
        help="Get a free key at aistudio.google.com — no credit card needed."
    )
    if not gemini_api_key:
        st.caption("🔑 Add key above to enable draft order generation after analysis.")


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
        help="Upload the KSEB truing-up petition PDF."
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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        # ── VALIDATION ──
        def validate_kseb_petition(pdf_path: str) -> tuple:
            """Returns (is_valid, message, details)"""
            try:
                import pdfplumber

                # Keywords that must appear somewhere in the document
                required_keywords = ['truing up', 'kerala']

                kseb_entity_keywords = [
                    'kerala state electricity board',
                    'kseb ltd', 'kseb limited', 'ksebl', 'kseb',
                    'thiruvananthapuram', 'trivandrum',
                    'kerala electricity', 'vydyuthi bhavanam', 'pattom'
                ]

                # ARR table column headers that appear in petitions
                tu_specific = [
                    'tu sought', 'truing up sought', 'actuals',
                    'arr approval', 'actual expenditure'
                ]

                # KSERC order language — these appear in orders, not petitions
                myt_indicators = [
                    'it is hereby ordered',
                    'the commission hereby orders',
                    'this order shall come into force',
                    'kserc order no',
                    'the commission directs'
                ]

                # KSEB petition cover page identifiers — page 1 only
                # The petition opens with KSEB's own name/address as the applicant.
                # A KSERC order page 1 will not have these.
                petition_page1_markers = [
                    'vydyuthi bhavanam',
                    'vydyuthi bhavan',
                    'applicant',
                ]

                found_required  = set()
                found_tu        = set()
                found_myt       = set()
                found_entity    = set()
                found_page1     = set()
                page_count      = 0

                with pdfplumber.open(pdf_path) as pdf:
                    page_count = len(pdf.pages)
                    pages_to_check = min(40, page_count)

                    for i, page in enumerate(pdf.pages[:pages_to_check]):
                        text = (page.extract_text() or '').lower()

                        # Page 1 check
                        if i == 0:
                            for kw in petition_page1_markers:
                                if kw in text:
                                    found_page1.add(kw)

                        for kw in required_keywords:
                            if kw in text:
                                found_required.add(kw)
                        for kw in tu_specific:
                            if kw in text:
                                found_tu.add(kw)
                        for kw in myt_indicators:
                            if kw in text:
                                found_myt.add(kw)
                        for kw in kseb_entity_keywords:
                            if kw in text:
                                found_entity.add(kw)

                # Gate 1: page 1 must look like a petition cover page
                if not found_page1:
                    return False, "wrong_file", {'pages': page_count}

                # Gate 2: must not be a KSERC order
                if found_myt:
                    return False, "wrong_file", {'pages': page_count}

                # Gate 3: must be KSEB entity
                if not found_entity:
                    return False, "wrong_file", {'pages': page_count}

                # Gate 4: must contain required keywords
                if set(required_keywords) - found_required:
                    return False, "wrong_file", {'pages': page_count}

                # Gate 5: must have truing-up ARR content
                if not found_tu:
                    return False, "wrong_file", {'pages': page_count}

                return True, "valid", {
                    'pages': page_count,
                    'tu_keywords_found': list(found_tu),
                    'entity_confirmed': list(found_entity)
                }

            except Exception as e:
                return False, f"read_error: {e}", {}

        st.markdown("---")
        with st.spinner("Validating PDF..."):
            is_valid, val_message, val_details = validate_kseb_petition(tmp_path)

        if not is_valid:
            st.error("❌ Wrong file. Please upload the KSEB truing-up petition PDF.")
            os.unlink(tmp_path)
            st.stop()

        # Override constants
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

        # Progress
        st.markdown("---")
        st.markdown("### ⏳ Processing...")
        prog   = st.progress(0)
        status = st.empty()

        try:
            status.markdown("**Step 1/3:** Parsing PDF and extracting tables...")
            prog.progress(10)

            from integration_pipeline import process_petition
            import io
            from contextlib import redirect_stdout

            f_out = io.StringIO()
            with redirect_stdout(f_out):
                results = process_petition(tmp_path)
                st.session_state['results'] = results
                st.session_state['uploaded_name'] = uploaded_file.name

            prog.progress(80)
            status.markdown("**Step 2/3:** Running heuristics...")

            # ── SBU-G extraction quality gate ──
            line_items_check = results.get('line_items', {})
            items_with_data = sum(
                1 for item in line_items_check.values()
                if (item.get('claimed_value') or
                    item.get('primary_heuristic', {}).get('claimed_value') or 0) > 0.5
            )
            if items_with_data < 6:
                st.error(
                    f"❌ Extraction failed: only {items_with_data}/10 SBU-G line items "
                    f"could be read. The PDF format may differ from the expected 2024-25 "
                    f"standard. Please verify the file and try again."
                )
                st.stop()

            # ── Fiscal year check ──
            detected_fy = results.get('metadata', {}).get('fiscal_year', '')
            if detected_fy and detected_fy != '2024-25':
                st.error(
                    f"❌ Wrong petition year: this tool is calibrated for 2024-25 "
                    f"but the file appears to be for {detected_fy}."
                )
                st.stop()

            # ── SBU-T extraction quality ──
            # Use consolidated summary as ground truth — it has its own extraction
            # logic and is more reliable than checking line_items key names.
            sbu_t_consolidated = results.get('consolidated_summary', {}).get('sbu_summaries', {}).get('T', {})
            sbu_t_claimed_total = sbu_t_consolidated.get('claimed', 0) or 0
            sbu_t_items_check = [i for i in results.get("sbu_t", {}).get("line_items", []) if isinstance(i, dict)]
            sbu_t_with_data = 4 if sbu_t_claimed_total > 0 else 0  # trust consolidated if it has data
            if sbu_t_claimed_total == 0 and not sbu_t_items_check:
                st.error("⛔ SBU-T extraction failed — transmission data is missing. "
                         "Do not rely on consolidated totals.")

            # ── SBU-D extraction quality ──
            sbu_d_items_check = [i for i in results.get("sbu_d", {}).get("line_items", []) if isinstance(i, dict)]
            sbu_d_with_data = sum(1 for i in sbu_d_items_check if (i.get("claimed") or i.get("claimed_value") or 0) > 0.5)
            if not sbu_d_items_check:
                st.error("⛔ SBU-D extraction failed — distribution data is missing. "
                         "SBU-D is ~89% of total ARR. Do not use consolidated totals.")
            elif sbu_d_with_data < 6:
                st.warning(f"⚠️ SBU-D partial extraction: only {sbu_d_with_data} of "
                           f"{len(sbu_d_items_check)} distribution items have data. "
                           f"Consolidated excess figures will be understated.")

            prog.progress(95)
            status.markdown("**Step 3/3:** Generating report...")
            prog.progress(100)
            status.markdown("✅ **Analysis complete!**")

        except Exception as e:
            st.error(f"❌ Analysis failed: {e}")
            import traceback
            st.code(traceback.format_exc())
            st.stop()
        finally:
            os.unlink(tmp_path)

    # ── RESULTS — render from session_state (persists across reruns) ──
    if 'results' in st.session_state:
        results = st.session_state['results']
        meta    = results.get('metadata', {})

        st.markdown("---")

        line_items = results.get('line_items', {})
        meta       = results.get('metadata', {})

        # ── Extraction status banner ──
        # Use consolidated summary totals as ground truth
        _cs = results.get('consolidated_summary', {}).get('sbu_summaries', {})
        sbu_t_ok = (_cs.get('T', {}).get('claimed', 0) or 0) > 0
        sbu_d_ok = (_cs.get('D', {}).get('claimed', 0) or 0) > 0
        if sbu_t_ok and sbu_d_ok:
            st.success("✅ All three SBUs extracted successfully — results are complete.")
        else:
            missing = []
            if not sbu_t_ok: missing.append("SBU-T (Transmission)")
            if not sbu_d_ok: missing.append("SBU-D (Distribution)")
            st.error(
                f"⛔ INCOMPLETE ANALYSIS — {', '.join(missing)} data could not be fully "
                f"extracted. Consolidated totals are PARTIAL. Do not use these figures "
                f"for regulatory orders without manual verification."
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

        # ── Helper functions ──
        def get_flag(item):
            if item.get('flag'):
                return item['flag']
            return item.get('primary_heuristic', {}).get('flag', 'UNKNOWN')

        def get_claimed(item):
            return (item.get('claimed_value') or
                    item.get('primary_heuristic', {}).get('claimed_value') or 0)

        def get_allowable(item):
            return (item.get('allowable_value') or
                    item.get('primary_heuristic', {}).get('allowable_value') or 0)

        # ─────────────────────────────────────────────────────────────────────
        # STAFF REVIEW COMPONENT (reused across SBU-G, SBU-T, SBU-D)
        # ─────────────────────────────────────────────────────────────────────

        def render_staff_review_inline(item_ref: dict, widget_key: str, allowable_amount: float):
            """
            Render staff review UI inside a line item expander.
            Mutates item_ref in-place — changes persist in session_state['results'].

            Args:
                item_ref:         The result dict for this line item (mutable reference).
                widget_key:       Unique string for Streamlit widget keys.
                allowable_amount: System-calculated allowable amount (pre-fill for override).
            """
            st.markdown("---")
            review_status = item_ref.get('staff_review_status', 'Pending')

            # ── Already reviewed ──
            if review_status in ('Accepted', 'Overridden'):
                decision_color = "#28a745" if review_status == "Accepted" else "#ffc107"
                approved_amt = float(item_ref.get('staff_approved_amount') or allowable_amount or 0)
                st.markdown(
                    f'<div style="background:#f0fdf4;border-left:4px solid {decision_color};'
                    f'border-radius:6px;padding:0.6rem 1rem;font-size:0.88rem;">'
                    f'<b>👤 Staff Decision: {review_status}</b>&nbsp;&nbsp;'
                    f'<span style="color:#555">Reviewed by <b>{item_ref.get("reviewed_by","—")}</b>'
                    f' on {item_ref.get("reviewed_at","—")}</span><br>'
                    f'Approved Amount: <b>₹{approved_amt:.2f} Cr</b>'
                    + (f'<br><span style="color:#555">Justification: '
                       f'{item_ref.get("staff_justification","")}</span>'
                       if item_ref.get("staff_justification") else '')
                    + '</div>',
                    unsafe_allow_html=True
                )
                if st.button("✏️ Edit Review", key=f"edit_{widget_key}", help="Reset and re-review"):
                    item_ref['staff_review_status'] = 'Pending'
                    st.rerun()
                return

            # ── Pending review form ──
            st.markdown('<b>👤 Staff Review</b>', unsafe_allow_html=True)
            review_action = st.radio(
                "Review Action:",
                ["Accept", "Override Amount"],
                key=f"ra_{widget_key}",
                horizontal=True
            )

            col1, col2 = st.columns(2)
            with col1:
                if review_action == "Override Amount":
                    new_amount = st.number_input(
                        "New Approved Amount [Cr]:",
                        value=float(allowable_amount or 0),
                        step=0.01,
                        format="%.2f",
                        key=f"amt_{widget_key}"
                    )
                else:
                    new_amount = allowable_amount
                reviewed_by = st.text_input("Reviewed By:", key=f"rb_{widget_key}")
            with col2:
                justification = st.text_area(
                    "Justification (required for Override):",
                    key=f"jst_{widget_key}",
                    height=90
                )

            if st.button("✅ Submit Review", key=f"sub_{widget_key}", type="primary"):
                if not reviewed_by:
                    st.error("Please enter your name.")
                elif review_action == "Override Amount" and not justification.strip():
                    st.error("Justification is required when overriding amount.")
                else:
                    item_ref['staff_review_status'] = (
                        'Overridden' if review_action == "Override Amount" else 'Accepted'
                    )
                    item_ref['reviewed_by']         = reviewed_by
                    item_ref['reviewed_at']         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    item_ref['staff_justification'] = justification.strip()
                    if review_action == "Override Amount":
                        item_ref['staff_approved_amount'] = new_amount
                    st.success(f"✅ Review submitted by {reviewed_by}")
                    st.rerun()

        # ── Review progress summary (shown above line item tables) ──
        def count_reviews(r):
            """Count reviewed vs total line items across all SBUs."""
            total, done = 0, 0
            for v in r.get('line_items', {}).values():
                if v.get('status') in ('skipped', 'error'):
                    continue
                total += 1
                if v.get('staff_review_status') in ('Accepted', 'Overridden'):
                    done += 1
            for item in r.get('sbu_t', {}).get('line_items', []):
                if isinstance(item, dict):
                    total += 1
                    if item.get('staff_review_status') in ('Accepted', 'Overridden'):
                        done += 1
            for item in r.get('sbu_d', {}).get('line_items', []):
                if isinstance(item, dict):
                    total += 1
                    if item.get('staff_review_status') in ('Accepted', 'Overridden'):
                        done += 1
            return done, total

        reviewed_count, total_count = count_reviews(results)
        if total_count > 0:
            pct = int(reviewed_count / total_count * 100)
            review_bar_color = "#28a745" if reviewed_count == total_count else "#ffc107"
            st.markdown(
                f'<div style="background:white;border-radius:8px;padding:0.7rem 1.2rem;'
                f'box-shadow:0 1px 4px rgba(0,0,0,0.08);margin-bottom:1rem;">'
                f'<b>👤 Review Progress:</b> {reviewed_count}/{total_count} line items reviewed'
                f'&nbsp;({pct}%)'
                + ('&nbsp; ✅ <b>All reviews complete — ready for draft order.</b>'
                   if reviewed_count == total_count else
                   '&nbsp; ⏳ Complete all reviews before generating the draft order.')
                + '</div>',
                unsafe_allow_html=True
            )

        # ─────────────────────────────────────────────────────────────────────
        # CONSOLIDATED SUMMARY
        # ─────────────────────────────────────────────────────────────────────

        consolidated = results.get('consolidated_summary', {})
        sbu_s = consolidated.get('sbu_summaries', {})
        ct    = consolidated.get('company_totals', {})

        if ct:
            st.markdown('<div class="section-header">🏢 KSEBL Consolidated — All SBUs</div>',
                        unsafe_allow_html=True)

            sbu_col1, sbu_col2, sbu_col3 = st.columns(3)
            for code, label, color, col in [
                ('G', 'SBU-G Generation',   '#28a745', sbu_col1),
                ('T', 'SBU-T Transmission', '#ffc107', sbu_col2),
                ('D', 'SBU-D Distribution', '#dc3545', sbu_col3),
            ]:
                s   = sbu_s.get(code, {})
                exc = (s.get('claimed', 0) or 0) - (s.get('allow', 0) or 0)
                with col:
                    st.markdown(f"""<div class="metric-box">
                      <div class="value" style="color:{color}">+₹{exc:,.0f}</div>
                      <div class="label">{label}</div>
                      <div style="font-size:0.75rem;color:#888;margin-top:4px">
                        Claimed ₹{s.get('claimed',0):,.0f} · Allow ₹{s.get('allow',0):,.0f}
                      </div></div>""", unsafe_allow_html=True)

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

            all_items  = consolidated.get('all_items', [])
            top_issues = sorted(
                [i for i in all_items if (i.get('variance', 0) or 0) > 1],
                key=lambda x: x.get('variance', 0), reverse=True
            )[:8]

            if top_issues:
                st.markdown('<div class="section-header">🔝 Top Issues Requiring Attention</div>',
                            unsafe_allow_html=True)
                for rank, item in enumerate(top_issues, 1):
                    flag = item.get('flag', 'GREY')
                    icon = {'RED':'🔴','YELLOW':'🟡','GREEN':'✅'}.get(flag, '⬜')
                    var  = item.get('variance', 0) or 0
                    card = {'RED':'card-red','YELLOW':'card-yellow'}.get(flag, 'card-grey')
                    st.markdown(f"""<div class="{card}">
                    <b>{rank}. {icon} [SBU-{item.get('sbu','?')}] {item.get('name','')}</b><br>
                    <span style="font-size:0.85rem">
                      Claimed ₹{item.get('claimed',0):,.2f} Cr &nbsp;·&nbsp;
                      Allowable ₹{item.get('allowable',0):,.2f} Cr &nbsp;·&nbsp;
                      <b>Excess +₹{var:,.2f} Cr</b>
                    </span></div>""", unsafe_allow_html=True)

        # ─────────────────────────────────────────────────────────────────────
        # SBU-G LINE ITEMS
        # ─────────────────────────────────────────────────────────────────────

        st.markdown("---")
        flags = [get_flag(v) for v in line_items.values()
                 if v.get('status') not in ['skipped', 'error']]
        n_green  = flags.count('GREEN')
        n_yellow = flags.count('YELLOW')
        n_red    = flags.count('RED')

        total_claimed   = sum(get_claimed(v)   for v in line_items.values())
        total_allowable = sum(get_allowable(v) for v in line_items.values())
        potential_savings = total_claimed - total_allowable

        st.markdown('<div class="section-header">⚙️ SBU-G Generation — Summary</div>',
                    unsafe_allow_html=True)

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
                <div class="label">Claimed (Cr)</div></div>""", unsafe_allow_html=True)
        with m5:
            st.markdown(f"""<div class="metric-box">
                <div class="value">₹{total_allowable:.0f}</div>
                <div class="label">Allowable (Cr)</div></div>""", unsafe_allow_html=True)
        with m6:
            sc = "#dc3545" if potential_savings > 0 else "#28a745"
            st.markdown(f"""<div class="metric-box">
                <div class="value" style="color:{sc}">₹{abs(potential_savings):.0f}</div>
                <div class="label">{'Excess (Cr)' if potential_savings > 0 else 'Under-claimed (Cr)'}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">🔍 SBU-G Line Item Analysis</div>',
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
            variance  = ((claimed - allowable) / allowable * 100 if allowable else 0)
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
                primary  = item.get('primary_heuristic', item)
                rec_text = (primary.get('recommendation_text') or
                            primary.get('smart_recommendation', {}).get('reason', ''))

                st.markdown(
                    f'<div class="{card_cls}">'
                    f'<b>{badge}&nbsp;&nbsp;{display_name}</b><br>'
                    f'<span style="font-size:0.85rem">{rec_text[:300]}</span>'
                    f'</div>', unsafe_allow_html=True
                )

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Claimed (Cr)",   f"₹{claimed:.2f}")
                c2.metric("Allowable (Cr)", f"₹{allowable:.2f}")
                c3.metric("Variance",       f"{variance:+.2f}%")
                action = (primary.get('smart_recommendation', {}).get('action') or
                          ('ACCEPT' if flag == 'GREEN' else
                           'REVIEW' if flag == 'YELLOW' else 'SCRUTINIZE'))
                c4.metric("Recommended Action", action)

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

                reg_basis = primary.get('regulatory_basis', '')
                if reg_basis:
                    st.caption(f"📜 Regulatory basis: {reg_basis}")

                # ── Staff review ──
                render_staff_review_inline(
                    item_ref         = results['line_items'][key],
                    widget_key       = f"g_{key}",
                    allowable_amount = allowable
                )

        # ─────────────────────────────────────────────────────────────────────
        # SBU-T LINE ITEMS
        # ─────────────────────────────────────────────────────────────────────

        # Helper: resolve claimed/allowable regardless of field name convention
        def t_claimed(item):
            return float(item.get('claimed') or item.get('claimed_value') or 0)
        def t_allowable(item):
            return float(item.get('allowable') or item.get('allowable_value') or 0)
        def t_name(item):
            return (item.get('name') or item.get('heuristic_name') or
                    item.get('heuristic_id') or 'Unknown')

        # SBU-T line_items may be a list OR a dict keyed by item name
        raw_sbu_t = results.get("sbu_t", {}).get("line_items", [])
        if isinstance(raw_sbu_t, dict):
            # Convert dict format to list
            sbu_t_items = []
            for k, v in raw_sbu_t.items():
                if isinstance(v, dict) and v.get('status') not in ('skipped', 'error'):
                    # Chain items (om_expenses, ifc) have primary_heuristic
                    primary = v.get('primary_heuristic', v)
                    primary.setdefault('name', k.replace('_', ' ').title())
                    sbu_t_items.append(primary)
        else:
            sbu_t_items = [i for i in raw_sbu_t if isinstance(i, dict)]

        sbu_t_items = [i for i in sbu_t_items if "repayment" not in t_name(i).lower()]

        if sbu_t_items:
            st.markdown("---")
            st.markdown('<div class="section-header">🔌 SBU-T Transmission — Line Item Analysis</div>',
                        unsafe_allow_html=True)

            tc_t = sum(t_claimed(i)   for i in sbu_t_items)
            ta_t = sum(t_allowable(i) for i in sbu_t_items)
            tt1, tt2, tt3 = st.columns(3)
            tt1.metric("Claimed (Cr)",   f"₹{tc_t:,.2f}")
            tt2.metric("Allowable (Cr)", f"₹{ta_t:,.2f}")
            tt3.metric("Excess (Cr)",    f"+₹{tc_t - ta_t:,.2f}")

            for item in sbu_t_items:
                name  = t_name(item)
                flag  = item.get('flag', 'GREY')
                cl    = t_claimed(item)
                al    = t_allowable(item)
                var   = cl - al
                icon  = {'RED':'🔴','YELLOW':'🟡','GREEN':'✅'}.get(flag, '⬜')
                badge = FLAG_BADGE.get(flag, f'<span>{flag}</span>')
                card  = FLAG_CARD.get(flag, 'card-grey')
                note  = (item.get('note') or item.get('recommendation_text') or '')[:200]

                with st.expander(
                    f"{icon}  {name}  —  Claimed: ₹{cl:.2f} Cr  |  "
                    f"Allowable: ₹{al:.2f} Cr  |  Excess: {var:+.2f} Cr",
                    expanded=(flag == 'RED')
                ):
                    st.markdown(
                        f'<div class="{card}">{badge}&nbsp;&nbsp;<b>{name}</b>'
                        + (f'<br><span style="font-size:0.85rem">{note}</span>' if note else '')
                        + '</div>', unsafe_allow_html=True
                    )
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Claimed (Cr)",   f"₹{cl:.2f}")
                    c2.metric("Allowable (Cr)", f"₹{al:.2f}")
                    c3.metric("Excess (Cr)",    f"{var:+.2f}")

                    # ── Staff review ──
                    safe_name = name.replace(' ', '_').replace('/', '_').replace('&', 'and')
                    render_staff_review_inline(
                        item_ref         = item,
                        widget_key       = f"t_{safe_name}",
                        allowable_amount = al
                    )

        # ─────────────────────────────────────────────────────────────────────
        # SBU-D LINE ITEMS
        # ─────────────────────────────────────────────────────────────────────

        sbu_d_items = [i for i in results.get("sbu_d", {}).get("line_items", []) if isinstance(i, dict)]

        if sbu_d_items:
            st.markdown("---")
            st.markdown('<div class="section-header">🏭 SBU-D Distribution — Line Item Analysis</div>',
                        unsafe_allow_html=True)

            tc_d = sum(i.get('claimed', 0) or 0 for i in sbu_d_items)
            ta_d = sum(i.get('allowable', 0) or 0 for i in sbu_d_items)
            td1, td2, td3 = st.columns(3)
            td1.metric("Claimed (Cr)",   f"₹{tc_d:,.2f}")
            td2.metric("Allowable (Cr)", f"₹{ta_d:,.2f}")
            td3.metric("Excess (Cr)",    f"+₹{tc_d - ta_d:,.2f}")

            for item in sbu_d_items:
                name  = item.get('name', '')
                flag  = item.get('flag', 'GREY')
                cl    = item.get('claimed', 0) or 0
                al    = item.get('allowable', 0) or 0
                var   = cl - al
                icon  = {'RED':'🔴','YELLOW':'🟡','GREEN':'✅'}.get(flag, '⬜')
                badge = FLAG_BADGE.get(flag, f'<span>{flag}</span>')
                card  = FLAG_CARD.get(flag, 'card-grey')
                note  = (item.get('note') or '')[:200]

                with st.expander(
                    f"{icon}  {name}  —  Claimed: ₹{cl:.2f} Cr  |  "
                    f"Allowable: ₹{al:.2f} Cr  |  Excess: {var:+.2f} Cr",
                    expanded=(flag == 'RED')
                ):
                    st.markdown(
                        f'<div class="{card}">{badge}&nbsp;&nbsp;<b>{name}</b>'
                        + (f'<br><span style="font-size:0.85rem">{note}</span>' if note else '')
                        + '</div>', unsafe_allow_html=True
                    )
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Claimed (Cr)",   f"₹{cl:.2f}")
                    c2.metric("Allowable (Cr)", f"₹{al:.2f}")
                    c3.metric("Excess (Cr)",    f"{var:+.2f}")

                    # Power Purchase sourcewise breakdown
                    if name == 'Power Purchase Cost':
                        sourcewise = item.get('sourcewise', {})
                        if sourcewise:
                            st.markdown("**Sourcewise Breakdown (D68):**")
                            src_rows = sorted(sourcewise.items(),
                                              key=lambda x: abs(x[1].get('cost_cr', 0) or 0),
                                              reverse=True)
                            tbl  = "| Source | MU | Cost (₹ Cr) | ₹/unit | Flag |\n"
                            tbl += "|--------|---:|------------:|-------:|------|\n"
                            for key_s, s in src_rows:
                                mu   = s.get('quantum_mu')
                                cost = s.get('cost_cr', 0) or 0
                                rate = s.get('rate_per_unit')
                                flg  = s.get('flag', 'GREY')
                                lbl  = s.get('label', key_s)
                                ico  = {'RED':'🔴','YELLOW':'⚠️','GREEN':'✅'}.get(flg, '⬜')
                                mu_s = f"{mu:,.2f}" if mu else '—'
                                rt_s = f"{rate:.2f}" if rate else '—'
                                tbl += f"| {lbl} | {mu_s} | {cost:,.2f} | {rt_s} | {ico} |\n"
                            st.markdown(tbl)
                            st.caption("🔴 >₹60/unit  ⚠️ ₹45-60/unit  ✅ <₹45/unit  ⬜ Pass-through")

                    # ── Staff review ──
                    safe_name_d = name.replace(' ', '_').replace('/', '_').replace('&', 'and')
                    render_staff_review_inline(
                        item_ref         = item,
                        widget_key       = f"d_{safe_name_d}",
                        allowable_amount = al
                    )

        # ─────────────────────────────────────────────────────────────────────
        # NEXT STEPS (SBU-G)
        # ─────────────────────────────────────────────────────────────────────

        st.markdown("---")
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
                               "disallow per prior KSERC order unless KSEB provides new justification.")
        if line_items.get('exceptional_items', {}).get('flag') == 'RED':
            next_steps.append("🔴 **Exceptional Items**: Request separate account code "
                               "registers and supporting documents.")
        if not next_steps:
            next_steps.append("✅ No immediate action items — proceed to order drafting.")

        for step in next_steps:
            st.markdown(f"- {step}")

        st.markdown(
            '<div class="disclaimer">'
            '⚠️ <b>Important:</b> This tool provides an automated first-cut analysis '
            'only. All recommendations must be reviewed and approved by authorised '
            'KSERC staff before being incorporated into regulatory orders. '
            'The tool does not replace professional regulatory judgement.'
            '</div>', unsafe_allow_html=True
        )

        # ─────────────────────────────────────────────────────────────────────
        # STAFF REVIEW SUMMARY TABLE
        # ─────────────────────────────────────────────────────────────────────

        st.markdown("---")
        st.markdown('<div class="section-header">📋 Staff Review Summary</div>',
                    unsafe_allow_html=True)

        import pandas as pd
        review_rows = []

        # SBU-G
        for key, display_name in DISPLAY_NAMES.items():
            item = results.get('line_items', {}).get(key, {})
            if not item or item.get('status') in ('skipped', 'error'):
                continue
            rs = item.get('staff_review_status', 'Pending')
            al = get_allowable(item)
            approved = float(item.get('staff_approved_amount') or al or 0)
            review_rows.append({
                'SBU':            'G',
                'Line Item':      display_name,
                'System Flag':    get_flag(item),
                'Allowable (Cr)': round(al, 2),
                'Approved (Cr)':  round(approved, 2),
                'Decision':       rs,
                'Reviewed By':    item.get('reviewed_by', '—'),
                'Justification':  item.get('staff_justification', ''),
            })

        # SBU-T
        for item in sbu_t_items:
            if 'repayment' in t_name(item).lower():
                continue
            rs = item.get('staff_review_status', 'Pending')
            al = t_allowable(item)
            approved = float(item.get('staff_approved_amount') or al or 0)
            review_rows.append({
                'SBU':            'T',
                'Line Item':      t_name(item),
                'System Flag':    item.get('flag', 'GREY'),
                'Allowable (Cr)': round(al, 2),
                'Approved (Cr)':  round(approved, 2),
                'Decision':       rs,
                'Reviewed By':    item.get('reviewed_by', '—'),
                'Justification':  item.get('staff_justification', ''),
            })

        # SBU-D
        for item in results.get('sbu_d', {}).get('line_items', []):
            if not isinstance(item, dict):
                continue
            rs = item.get('staff_review_status', 'Pending')
            al = item.get('allowable', 0) or 0
            approved = float(item.get('staff_approved_amount') or al or 0)
            review_rows.append({
                'SBU':            'D',
                'Line Item':      item.get('name', ''),
                'System Flag':    item.get('flag', 'GREY'),
                'Allowable (Cr)': round(al, 2),
                'Approved (Cr)':  round(approved, 2),
                'Decision':       rs,
                'Reviewed By':    item.get('reviewed_by', '—'),
                'Justification':  item.get('staff_justification', ''),
            })

        if review_rows:
            df_reviews = pd.DataFrame(review_rows)

            def _highlight_decision(val):
                if val == 'Accepted':
                    return 'background-color:#d4edda;color:#155724'
                elif val == 'Overridden':
                    return 'background-color:#fff3cd;color:#856404'
                else:
                    return 'background-color:#f8d7da;color:#721c24'

            st.dataframe(
                df_reviews.style.applymap(_highlight_decision, subset=['Decision']),
                use_container_width=True,
                hide_index=True
            )

            pending_items = [r for r in review_rows if r['Decision'] == 'Pending']
            if pending_items:
                st.warning(f"⏳ {len(pending_items)} line item(s) still pending review: "
                           + ", ".join(f"[SBU-{r['SBU']}] {r['Line Item']}" for r in pending_items))
            else:
                st.success("✅ All line items reviewed. Justifications will be included in the draft order.")

        # ─────────────────────────────────────────────────────────────────────
        # DOWNLOAD JSON
        # ─────────────────────────────────────────────────────────────────────

        st.markdown("---")
        dl_col, _ = st.columns([1, 3])
        with dl_col:
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
                label="⬇️ Download Full Analysis + Staff Reviews (JSON)",
                data=json_out,
                file_name=f"KSERC_Analysis_{meta.get('fiscal_year','2024-25')}.json",
                mime="application/json",
                use_container_width=True
            )

        # ── DRAFT ORDER GENERATION ──
        st.markdown("---")
        st.markdown('<div class="section-header">📝 Draft Order Generation</div>',
                    unsafe_allow_html=True)

        if not gemini_api_key:
            st.info("🔑 Add your free Gemini API key in the sidebar to generate a draft order.")
        else:
            order_col, _ = st.columns([1, 3])
            with order_col:
                gen_order_btn = st.button(
                    "📄 Generate Draft Order (Word)",
                    type="primary",
                    use_container_width=True,
                    help="Uses Gemini Flash (free) to draft a KSERC order based on analysis results."
                )

            if gen_order_btn:
                order_prog   = st.progress(0)
                order_status = st.empty()

                def order_progress(pct, msg):
                    order_prog.progress(pct)
                    order_status.markdown(f"**{msg}**")

                try:
                    from order_generator import generate_order
                    order_bytes = generate_order(
                        results,
                        api_key=gemini_api_key,
                        progress_callback=order_progress
                    )
                    order_prog.progress(100)
                    order_status.markdown("✅ **Draft order ready!**")

                    st.download_button(
                        label="⬇️ Download Draft Order (.docx)",
                        data=order_bytes,
                        file_name=f"KSERC_Draft_Order_{meta.get('fiscal_year','2024-25')}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True
                    )
                    st.caption(
                        "⚠️ This is an AI-generated draft for internal review only. "
                        "All findings and directions must be verified by authorised KSERC officers."
                    )
                except Exception as e:
                    st.error(f"❌ Order generation failed: {e}")
                    import traceback
                    st.code(traceback.format_exc())

else:
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
    '</div>', unsafe_allow_html=True
)
