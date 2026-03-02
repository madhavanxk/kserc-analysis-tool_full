"""
KSERC Truing-Up Order Generator
================================
Takes analysis JSON from the pipeline and generates a draft
KSERC truing-up order as a Word (.docx) document using Gemini Flash.
"""

import io
import json
from datetime import datetime

import requests
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _set_cell_bg(cell, hex_color: str):
    """Set table cell background colour."""
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  hex_color)
    tcPr.append(shd)


def _heading(doc, text: str, level: int = 1):
    p = doc.add_heading(text, level=level)
    p.runs[0].font.color.rgb = RGBColor(0x1a, 0x3a, 0x5c)
    return p


def _para(doc, text: str = '', bold: bool = False,
          italic: bool = False, size: int = 11, center: bool = False):
    p = doc.add_paragraph()
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(text)
    run.bold   = bold
    run.italic = italic
    run.font.size = Pt(size)
    return p


def _fmt(value, decimals: int = 2) -> str:
    try:
        return f"₹{float(value):,.{decimals}f} Cr"
    except Exception:
        return str(value)


def _variance(claimed, allowable) -> str:
    try:
        c, a = float(claimed), float(allowable)
        if a == 0:
            return "—"
        return f"{(c - a) / a * 100:+.1f}%"
    except Exception:
        return "—"


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI CALL
# ─────────────────────────────────────────────────────────────────────────────

def _gemini_draft_all(api_key: str, bg_prompt: str, sbu_g_prompt: str,
                       sbu_d_prompt: str) -> tuple:
    """Single Gemini REST call — no library version issues."""
    import re

    combined_prompt = f"""You are drafting sections of a formal KSERC regulatory order.
Complete all three tasks below. Use XML tags to separate your responses exactly as shown.

<task1>
{bg_prompt}
</task1>

<task2>
{sbu_g_prompt}
</task2>

<task3>
{sbu_d_prompt}
</task3>

Respond in this exact format:
<background>
[your background text here]
</background>
<sbu_g>
[your SBU-G findings text here]
</sbu_g>
<sbu_d>
[your SBU-D findings text here]
</sbu_d>"""

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": combined_prompt}]}],
        "generationConfig": {"maxOutputTokens": 4096, "temperature": 0.3}
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

    def extract(tag, txt):
        m = re.search(rf'<{tag}>(.*?)</{tag}>', txt, re.DOTALL)
        return m.group(1).strip() if m else ''

    return (
        extract('background', text),
        extract('sbu_g',      text),
        extract('sbu_d',      text),
    )


def _sbu_g_section_prompt(line_items: dict, fiscal_year: str) -> str:
    items_text = []
    for key, item in line_items.items():
        if not item or item.get('status') in ['skipped', 'error']:
            continue
        ph  = item.get('primary_heuristic', item)
        cl  = item.get('claimed_value')  or ph.get('claimed_value',  0)
        al  = item.get('allowable_value') or ph.get('allowable_value', 0)
        flg = item.get('flag') or ph.get('flag', 'UNKNOWN')
        rec = ph.get('recommendation_text', '')
        reg = ph.get('regulatory_basis', '')
        items_text.append(
            f"- {key.upper()}: Claimed={cl} Cr, Allowable={al} Cr, Flag={flg}\n"
            f"  Basis: {reg}\n  Note: {rec[:200]}"
        )

    return f"""You are drafting the SBU-G (Generation) section of a formal KSERC truing-up order for FY {fiscal_year}.

Write in the style of Kerala State Electricity Regulatory Commission orders:
- Formal legal prose
- Third person ("The Commission", "The petitioner")
- Each line item gets 2-3 sentences: what KSEB claimed, what is normatively allowable, and the Commission's view
- End each item with a one-sentence operative direction

Line items:
{chr(10).join(items_text)}

Write ONLY the SBU-G findings section. No preamble, no headings. Start directly with the first line item finding.
Keep total length under 600 words."""


def _sbu_d_section_prompt(sbu_d_items: list, fiscal_year: str) -> str:
    items_text = []
    for item in sbu_d_items:
        if not isinstance(item, dict):
            continue
        name = item.get('name', '')
        cl   = item.get('claimed',   0) or 0
        al   = item.get('allowable', 0) or 0
        flag = item.get('flag', 'GREY')
        note = (item.get('note') or '')[:150]
        items_text.append(
            f"- {name}: Claimed={cl:.2f} Cr, Allowable={al:.2f} Cr, Flag={flag}\n"
            f"  Note: {note}"
        )

    return f"""You are drafting the SBU-D (Distribution) section of a formal KSERC truing-up order for FY {fiscal_year}.

Same formal KSERC style as described. Focus on Power Purchase Cost (largest variance), IFC, and O&M.

Line items:
{chr(10).join(items_text[:10])}

Write ONLY the SBU-D findings. Start directly. Under 500 words."""


def _background_prompt(meta: dict, consolidated: dict, fiscal_year: str) -> str:
    ct = consolidated.get('company_totals', {})
    return f"""You are drafting the background section of a KSERC truing-up order for FY {fiscal_year}.

Facts:
- Petition filed by: Kerala State Electricity Board Limited (KSEBL), Vydyuthi Bhavanam, Pattom, Thiruvananthapuram
- Fiscal year: {fiscal_year}
- Total claimed ARR: {ct.get('total_claimed', 0):,.2f} Cr
- Total allowable ARR: {ct.get('total_allow', 0):,.2f} Cr
- Excess claimed: {ct.get('total_excess', 0):,.2f} Cr
- Three SBUs: Generation (SBU-G), Transmission (SBU-T), Distribution (SBU-D)
- MYT Regulation: KSERC MYT Regulations 2021, control period 2022-23 to 2026-27

Write 3-4 paragraphs covering:
1. Brief intro of petitioner and nature of petition
2. MYT regulatory framework context
3. Summary of what the Commission examined

Formal legal prose. Under 300 words."""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_order(results: dict, api_key: str,
                   progress_callback=None) -> bytes:
    """
    Generate a KSERC draft truing-up order as a Word document.
    Returns bytes of the .docx file.
    progress_callback(pct, message) if provided.
    """

    def progress(pct, msg):
        if progress_callback:
            progress_callback(pct, msg)

    meta         = results.get('metadata', {})
    fiscal_year  = meta.get('fiscal_year', '2024-25')
    line_items   = results.get('line_items', {})
    consolidated = results.get('consolidated_summary', {})
    sbu_s        = consolidated.get('sbu_summaries', {})
    ct           = consolidated.get('company_totals', {})
    sbu_d_items  = [i for i in results.get('sbu_d', {}).get('line_items', [])
                    if isinstance(i, dict)]
    sbu_t_items  = [i for i in results.get('sbu_t', {}).get('line_items', [])
                    if isinstance(i, dict)
                    and 'repayment' not in i.get('name', '').lower()]

    today = datetime.now().strftime('%d %B %Y')

    # ── 1. AI-generated sections (single API call) ──
    progress(5, "Drafting order text with Gemini...")
    bg_text, sbu_g_text, sbu_d_text = _gemini_draft_all(
        api_key,
        _background_prompt(meta, consolidated, fiscal_year),
        _sbu_g_section_prompt(line_items, fiscal_year),
        _sbu_d_section_prompt(sbu_d_items, fiscal_year),
    )
    progress(60, "Building Word document...")

    # ── 2. Build Word document ──
    doc = Document()

    # Page margins — A4, 1 inch margins
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1.25)
        section.right_margin  = Inches(1.25)

    # Default style
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # ── COVER ──
    _para(doc, 'BEFORE THE HONOURABLE', bold=True, size=12, center=True)
    _para(doc, 'KERALA STATE ELECTRICITY REGULATORY COMMISSION',
          bold=True, size=13, center=True)
    _para(doc, 'At its office at C V Raman Pillai Road, Vellayambalam, Thiruvananthapuram',
          size=10, center=True)
    doc.add_paragraph()

    # Case details table
    tbl = doc.add_table(rows=3, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.style = 'Table Grid'
    col_w = [Inches(1.5), Inches(4.5)]

    headers = ['In the matter of:', 'In the matter of:']
    vals = [
        f'Truing up of Accounts of Generation, Transmission and Distribution '
        f'Strategic Business Units of the Kerala State Electricity Board Limited '
        f'(KSEBL) for the year {fiscal_year}.',
        'Kerala State Electricity Board Limited,\nVydyuthi Bhavanam, Pattom, '
        'Thiruvananthapuram – 4\n\nAPPLICANT'
    ]

    rows_data = [
        ('In the matter of:', vals[0]),
        ('In the matter of:', vals[1]),
        ('OP No.', '          /2025'),
    ]

    for i, (label, value) in enumerate(rows_data):
        row = tbl.rows[i]
        row.cells[0].text = label
        row.cells[1].text = value
        row.cells[0].paragraphs[0].runs[0].bold = True
        _set_cell_bg(row.cells[0], 'D5E8F0')
        for cell, w in zip(row.cells, col_w):
            cell.width = w

    doc.add_paragraph()

    # Date and order title
    _para(doc, f'ORDER', bold=True, size=14, center=True)
    _para(doc, f'Date: {today}', size=11, center=True)
    doc.add_paragraph()

    # ── SECTION 1: BACKGROUND ──
    _heading(doc, '1. Background', level=1)
    for para in bg_text.split('\n'):
        if para.strip():
            doc.add_paragraph(para.strip())

    doc.add_paragraph()

    # ── SECTION 2: CONSOLIDATED SUMMARY TABLE ──
    _heading(doc, '2. Summary of ARR — All SBUs', level=1)
    _para(doc, f'The Commission has examined the truing-up petition filed by KSEBL for '
               f'FY {fiscal_year}. The aggregate revenue requirement claimed and '
               f'determined allowable across all three SBUs is as follows:')

    # Summary table
    summary_tbl = doc.add_table(rows=5, cols=4)
    summary_tbl.style = 'Table Grid'
    summary_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr_row = summary_tbl.rows[0]
    for i, h in enumerate(['SBU', 'Claimed (₹ Cr)', 'Allowable (₹ Cr)', 'Excess (₹ Cr)']):
        hdr_row.cells[i].text = h
        hdr_row.cells[i].paragraphs[0].runs[0].bold = True
        _set_cell_bg(hdr_row.cells[i], '1A3A5C')
        hdr_row.cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    sbu_rows = [
        ('SBU-G (Generation)',    'G'),
        ('SBU-T (Transmission)',  'T'),
        ('SBU-D (Distribution)',  'D'),
        ('KSEBL Total',           None),
    ]
    for i, (label, code) in enumerate(sbu_rows, 1):
        if code:
            s  = sbu_s.get(code, {})
            cl = s.get('claimed', 0) or 0
            al = s.get('allow',   0) or 0
            ex = cl - al
        else:
            cl = ct.get('total_claimed', 0) or 0
            al = ct.get('total_allow',   0) or 0
            ex = ct.get('total_excess',  0) or 0

        row = summary_tbl.rows[i]
        row.cells[0].text = label
        row.cells[1].text = f"{cl:,.2f}"
        row.cells[2].text = f"{al:,.2f}"
        row.cells[3].text = f"{ex:+,.2f}"

        if code is None:  # totals row
            for cell in row.cells:
                cell.paragraphs[0].runs[0].bold = True
            _set_cell_bg(row.cells[3], 'FCE4D6')

    doc.add_paragraph()

    # ── SECTION 3: SBU-G FINDINGS ──
    _heading(doc, '3. SBU-G — Generation: Findings', level=1)

    # SBU-G line items table
    g_tbl = doc.add_table(rows=1, cols=5)
    g_tbl.style = 'Table Grid'
    g_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = g_tbl.rows[0]
    for i, h in enumerate(['Line Item', 'Claimed (Cr)', 'Allowable (Cr)', 'Excess (Cr)', 'Flag']):
        hdr.cells[i].text = h
        hdr.cells[i].paragraphs[0].runs[0].bold = True
        _set_cell_bg(hdr.cells[i], 'D5E8F0')

    DISPLAY_NAMES = {
        'roe': 'Return on Equity',
        'depreciation': 'Depreciation',
        'fuel_costs': 'Fuel Costs',
        'om_expenses': 'O&M Expenses',
        'ifc': 'Interest & Finance Charges',
        'master_trust': 'Master Trust Bond Interest',
        'nti': 'Non-Tariff Income',
        'intangibles': 'Intangible Assets',
        'other_expenses': 'Other Expenses',
        'exceptional_items': 'Exceptional Items',
    }

    FLAG_COLORS = {'GREEN': 'C6EFCE', 'YELLOW': 'FFEB9C', 'RED': 'FFC7CE'}

    for key, name in DISPLAY_NAMES.items():
        item = line_items.get(key, {})
        if not item or item.get('status') in ['skipped', 'error']:
            continue
        ph  = item.get('primary_heuristic', item)
        cl  = item.get('claimed_value')  or ph.get('claimed_value',  0) or 0
        al  = item.get('allowable_value') or ph.get('allowable_value', 0) or 0
        flg = item.get('flag') or ph.get('flag', '—')
        ex  = cl - al

        row = g_tbl.add_row()
        row.cells[0].text = name
        row.cells[1].text = f"{cl:,.2f}"
        row.cells[2].text = f"{al:,.2f}"
        row.cells[3].text = f"{ex:+,.2f}"
        row.cells[4].text = flg
        if flg in FLAG_COLORS:
            _set_cell_bg(row.cells[4], FLAG_COLORS[flg])
            _set_cell_bg(row.cells[3], FLAG_COLORS[flg])

    doc.add_paragraph()
    _heading(doc, '3.1 Detailed Findings — SBU-G', level=2)
    for para in sbu_g_text.split('\n'):
        if para.strip():
            doc.add_paragraph(para.strip())

    doc.add_paragraph()

    # ── SECTION 4: SBU-T FINDINGS ──
    _heading(doc, '4. SBU-T — Transmission: Findings', level=1)

    if sbu_t_items:
        t_tbl = doc.add_table(rows=1, cols=4)
        t_tbl.style = 'Table Grid'
        hdr = t_tbl.rows[0]
        for i, h in enumerate(['Line Item', 'Claimed (Cr)', 'Allowable (Cr)', 'Flag']):
            hdr.cells[i].text = h
            hdr.cells[i].paragraphs[0].runs[0].bold = True
            _set_cell_bg(hdr.cells[i], 'D5E8F0')

        for item in sbu_t_items:
            cl  = item.get('claimed',   0) or 0
            al  = item.get('allowable', 0) or 0
            flg = item.get('flag', '—')
            row = t_tbl.add_row()
            row.cells[0].text = item.get('name', '')
            row.cells[1].text = f"{cl:,.2f}"
            row.cells[2].text = f"{al:,.2f}"
            row.cells[3].text = flg
            if flg in FLAG_COLORS:
                _set_cell_bg(row.cells[3], FLAG_COLORS[flg])
    else:
        t_s  = sbu_s.get('T', {})
        t_cl = t_s.get('claimed', 0) or 0
        t_al = t_s.get('allow',   0) or 0
        doc.add_paragraph(
            f'SBU-T total claimed: ₹{t_cl:,.2f} Cr. '
            f'Allowable: ₹{t_al:,.2f} Cr. '
            f'Excess: ₹{t_cl - t_al:+,.2f} Cr. '
            f'Detailed line-item breakdown to be reviewed from petition schedules.'
        )

    doc.add_paragraph()

    # ── SECTION 5: SBU-D FINDINGS ──
    _heading(doc, '5. SBU-D — Distribution: Findings', level=1)

    if sbu_d_items:
        d_tbl = doc.add_table(rows=1, cols=5)
        d_tbl.style = 'Table Grid'
        hdr = d_tbl.rows[0]
        for i, h in enumerate(['Line Item', 'Claimed (Cr)', 'Allowable (Cr)', 'Excess (Cr)', 'Flag']):
            hdr.cells[i].text = h
            hdr.cells[i].paragraphs[0].runs[0].bold = True
            _set_cell_bg(hdr.cells[i], 'D5E8F0')

        for item in sbu_d_items:
            cl  = item.get('claimed',   0) or 0
            al  = item.get('allowable', 0) or 0
            ex  = cl - al
            flg = item.get('flag', '—')
            row = d_tbl.add_row()
            row.cells[0].text = item.get('name', '')
            row.cells[1].text = f"{cl:,.2f}"
            row.cells[2].text = f"{al:,.2f}"
            row.cells[3].text = f"{ex:+,.2f}"
            row.cells[4].text = flg
            if flg in FLAG_COLORS:
                _set_cell_bg(row.cells[4], FLAG_COLORS[flg])
                _set_cell_bg(row.cells[3], FLAG_COLORS[flg])

    doc.add_paragraph()
    _heading(doc, '5.1 Detailed Findings — SBU-D', level=2)
    for para in sbu_d_text.split('\n'):
        if para.strip():
            doc.add_paragraph(para.strip())

    doc.add_paragraph()

    # ── SECTION 6: OPERATIVE DIRECTIONS ──
    _heading(doc, '6. Operative Directions', level=1)
    doc.add_paragraph(
        'Having examined the truing-up petition filed by KSEBL for '
        f'FY {fiscal_year} and after due consideration, the Commission '
        'hereby directs as follows:'
    )

    # Build directions from RED/YELLOW items
    directions = []
    dir_num = 1
    for key, item in line_items.items():
        ph  = item.get('primary_heuristic', item)
        flg = item.get('flag') or ph.get('flag', '')
        al  = item.get('allowable_value') or ph.get('allowable_value', 0) or 0
        name = DISPLAY_NAMES.get(key, key)
        if flg == 'RED':
            directions.append(
                f'{dir_num}. {name}: The Commission approves ₹{al:,.2f} Cr '
                f'as the allowable amount. The excess claimed is disallowed.'
            )
            dir_num += 1
        elif flg == 'YELLOW':
            directions.append(
                f'{dir_num}. {name}: The Commission provisionally approves ₹{al:,.2f} Cr '
                f'subject to verification of supporting documents.'
            )
            dir_num += 1
        elif flg == 'GREEN':
            directions.append(
                f'{dir_num}. {name}: The Commission approves the claimed amount of '
                f'₹{al:,.2f} Cr.'
            )
            dir_num += 1

    directions.append(
        f'{dir_num}. The total allowable ARR for KSEBL for FY {fiscal_year} '
        f'across all three SBUs is determined at ₹{ct.get("total_allow", 0):,.2f} Cr '
        f'against the claimed amount of ₹{ct.get("total_claimed", 0):,.2f} Cr.'
    )

    for d in directions:
        doc.add_paragraph(d)

    doc.add_paragraph()

    # ── SIGNATURE BLOCK ──
    doc.add_paragraph()
    _para(doc, 'Sd/-', center=True)
    _para(doc, 'Chairman / Member', bold=True, center=True)
    _para(doc, 'Kerala State Electricity Regulatory Commission', center=True)
    _para(doc, f'Thiruvananthapuram', center=True)
    _para(doc, f'Date: {today}', center=True)

    doc.add_paragraph()
    _para(doc, '— DRAFT FOR INTERNAL REVIEW ONLY —',
          bold=True, italic=True, center=True, size=10)
    _para(doc, 'Generated by KSERC Truing-Up Analysis Tool. '
               'All findings require review by authorised KSERC officers '
               'before issuance.', italic=True, center=True, size=9)

    # ── Return as bytes ──
    progress(95, "Finalising document...")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()
