# KSERC Truing-Up Analysis Tool

Automated first-cut analysis of KSEB truing-up petitions for the Kerala State Electricity Regulatory Commission (KSERC).

**Version:** Beta v2.0
**Coverage:** All three Strategic Business Units (SBU-G · SBU-T · SBU-D)
**Fiscal Year:** 2024-25

---

## What It Does

KSERC staff upload a KSEB truing-up petition PDF. The tool automatically:

1. Extracts line items from all three SBU chapters of the petition
2. Extracts supporting tables from Chapter 5
3. Runs regulatory heuristics against MYT-approved values
4. Produces a traffic light analysis (GREEN / YELLOW / RED) for each item
5. Identifies excess claims and flags items requiring scrutiny
6. Generates a KSEBL consolidated summary across all SBUs

**Typical processing time:** ~100 seconds for a 381-page petition.

---

## Coverage — Line Items

### SBU-G (Generation) — 10 line items

| Line Item | Heuristic(s) |
|-----------|-------------|
| Return on Equity (ROE) | ROE-01 |
| Depreciation | DEP-GEN-01 |
| Fuel Costs | FUEL-01 |
| O&M Expenses | OM-INFL-01, OM-NORM-01, OM-APPORT-01, EMP-PAYREV-01 |
| Interest & Finance Charges | IFC-LTL-01, IFC-WC-01, IFC-GPF-01, IFC-OTH-02 |
| Master Trust Bond Interest | MT-BOND-01 |
| Non-Tariff Income | NTI-01 |
| Intangible Assets | INTANG-01 |
| Other Expenses | OTHER-EXP-01 |
| Exceptional Items | EXC-01 |

### SBU-T (Transmission) — 12 line items

| Line Item | Heuristic(s) |
|-----------|-------------|
| Return on Equity (14%) | ROE-T-01 |
| Depreciation (Normative) | DEP-T-01 |
| O&M Expenses (Normative) | OM-TRANS-NORM-01 |
| Interest & Finance Charges | IFC-LTL, IFC-WC, IFC-GPF, IFC-OTH |
| Master Trust Bonds | MT-T-01 |
| Non-Tariff Income | NTI-T-01 |
| Intangible Assets | INTANG-T-01 |
| Exceptional Items | EXC-T-01 |
| Line Compensation — Edamon-Kochi 400kV | TRANS-COMP-01 |
| Line Compensation — Pugalur-Thrissur HVDC | TRANS-COMP-01 |
| Incentive on Transmission Availability | TRANS-INCENT-01 |

### SBU-D (Distribution) — 13 line items

| Line Item | Heuristic(s) |
|-----------|-------------|
| Power Purchase Cost (with D68 sourcewise breakdown) | PP-D-01 |
| O&M Expenses (Normative) | OM-D-01 |
| Depreciation (Normative) | DEP-D-01 |
| Return on Equity (14%) | ROE-D-01 |
| Interest & Finance Charges | IFC-D-01 |
| Master Trust Contribution | MT-D-01 |
| Non-Tariff Income | NTI-D-01 |
| T&D Loss Reduction Gain | TD-LOSS-01 |
| Intangible Assets | INTANG-D-01 |
| Exceptional Items | EXC-D-01 |
| Solar Registration Refund | SOLAR-REG-01 |
| Liquidated Damages Refund | LIQ-DAM-01 |
| Other Expenses | OTHER-D-01 |

---

## Safety — Document Validation

The tool rejects incorrect files at multiple gates before any analysis runs:

| Gate | What it checks | If failed |
|------|---------------|-----------|
| 1 | MYT Order language detected | Hard reject — wrong document type |
| 2 | KSEB Ltd entity identifiers | Hard reject — wrong utility |
| 3 | Truing-up ARR column headers present | Hard reject — not a petition |
| 4 | SBU-G extraction quality (≥6/10 items) | Hard stop |
| 5 | Fiscal year mismatch | Hard stop |
| 6 | SBU-T extraction quality (≥4 items) | Warning banner |
| 7 | SBU-D extraction quality (≥6 items) | Warning banner |
| 8 | Any partial extraction + consolidated total | Error — marks totals as PARTIAL |

If any extraction is incomplete, the results page shows a prominent **⛔ INCOMPLETE ANALYSIS** banner so KSERC staff cannot mistake partial figures for complete ones. A green **✅ All three SBUs extracted successfully** banner confirms completeness on a successful run.

---

## Installation (Local)

**Requirements:** Python 3.10+

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app opens automatically at `http://localhost:8501`.

---

## Running from Command Line (without UI)

```bash
python integration_pipeline.py KSEB_Petition.pdf
```

Output is saved as `KSERC_TruingUp_2024-25_KSEB_analysis.json` in the same directory.

---

## File Structure

```
kserc-analysis-tool/
│
├── streamlit_app.py              # Main UI — run this
├── integration_pipeline.py       # End-to-end pipeline (all 3 SBUs)
├── ksebl_consolidated_summary.py # Cross-SBU aggregation and display
├── kserc_constants.py            # Regulatory constants (CPI, WPI, rates etc.)
│
├── pdf_parser_sbu_g.py           # SBU-G PDF table extraction
├── pdf_parser_sbu_t.py           # SBU-T PDF table extraction
├── pdf_parser_sbu_d.py           # SBU-D PDF table extraction
│
├── data_mapper_sbu_g.py          # Maps extracted data → heuristic inputs (G)
├── data_mapper_sbu_t.py          # Maps extracted data → heuristic inputs (T)
├── data_mapper_sbu_d.py          # Maps extracted data → heuristic inputs (D)
│
├── roe_heuristics.py             # ROE-01
├── depreciation_heuristics.py    # DEP-GEN-01
├── fuel_heuristics.py            # FUEL-01
├── om_heuristics.py              # OM chain (4 heuristics)
├── ifc_heuristics.py             # IFC chain (4 heuristics)
├── master_trust_heuristics.py    # MT-BOND-01
├── nti_heuristics.py             # NTI-01
├── intangible_heuristics.py      # INTANG-01
├── other_items_heuristics.py     # OTHER-EXP-01, EXC-01
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Regulatory Constants

All constants sourced from KSERC MYT Order 2022 and published RBI/CSO indices. All are visible and editable in the sidebar before each run.

| Constant | Value | Source |
|----------|-------|--------|
| CPI 2024-25 | 410.64 | RBI / CSO — Table D.571 |
| WPI 2024-25 | 154.90 | RBI / CSO — Table D.571 |
| SBI EBLR | 7.55% | MYT Order 2022 |
| GPF Rate | 7.10% | Table 5.27, MYT Order 2022 |
| SBU-G Employee Ratio | 5.40% | Table 4.51, MYT Order 2022 |
| O&M Base Year (SBU-G) | ₹156.16 Cr | TU Order 14.06.2022 |
| PP Approved (SBU-D) | ₹10,716.26 Cr | MYT Order 2022 |
| IFC Approved (SBU-D) | ₹1,499.43 Cr | MYT Order 2022 |
| GPF Opening 2024-25 | ₹3,364.32 Cr | Table 5.27, MYT Order 2022 |
| GPF Closing 2024-25 | ₹3,454.32 Cr | Table 5.27, MYT Order 2022 |

---

## FY 2024-25 Analysis Results (Reference Run)

When run against the KSEB FY 2024-25 truing-up petition:

| SBU | Claimed (₹ Cr) | Allowable (₹ Cr) | Excess (₹ Cr) |
|-----|---------------|-----------------|--------------|
| SBU-G Generation | 922.61 | 847.06 | +75.55 |
| SBU-T Transmission | 1,772.05 | 1,647.41 | +124.64 |
| SBU-D Distribution | 19,996.53 | 17,001.72 | +2,994.81 |
| **KSEBL Total** | **22,394.06** | **19,203.99** | **+3,190.07** |

Top issues identified:
1. Power Purchase Cost — SBU-D: +₹2,214 Cr (exchanges at ₹64/unit, short-term at ₹65/unit vs MYT approved)
2. Interest & Finance Charges — SBU-D: +₹382 Cr
3. O&M Expenses — SBU-D: +₹183 Cr
4. T&D Loss Reduction Gain — SBU-D: +₹132 Cr
5. IFC — SBU-T: +₹83 Cr

---

## Updating for a New Year

When a new truing-up petition is filed:

1. Update `kserc_constants.py` with new CPI/WPI values (from RBI)
2. Update GPF opening/closing balances (shift one year from Table 5.27)
3. Update loan opening balance and interest rate (from new petition Table 5.3)
4. All MYT constants remain fixed until the next MYT order (2027)

Estimated update effort: **2-3 hours per year.**

---

## Known Limitations (v2.0)

- **2024-25 petition format only** — table layouts may differ in earlier petitions
- Tables 5.1 and 5.22 (company-level IFC detail) not extractable — workaround uses Table G10
- O&M component table 5.37 not found in current petition format
- SBU-T actual availability % not extracted — transmission incentive uses 99% placeholder; KSERC staff must verify from SLDC certificate independently
- T&D loss approved% and actual% not directly extracted — gain computed from reported figure in D89 only
- Opening GFA for SBU-G derived from MYT WC requirement (not directly extracted from petition)

---

## Important Disclaimer

This tool provides an automated first-cut analysis only. All recommendations must be reviewed and approved by authorised KSERC staff before being incorporated into regulatory orders. The tool does not replace professional regulatory judgement.

---

## Built For

Kerala State Electricity Regulatory Commission (KSERC)
Thiruvananthapuram, Kerala, India

---

*For technical queries, contact the development team.*
