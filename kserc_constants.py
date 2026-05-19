"""
KSERC Regulatory Constants
==========================
Static values from KSERC orders used across heuristics.
Source: Table D.571 - Escalation Rate based on actual inflationary index for FY 2024-25

Update these values each tariff year.
"""

# =============================================================================
# INFLATION INDICES (Table D.571)
# =============================================================================

# CPI - Industrial Workers (Base: 2001=100)
CPI = {
    '2021-22': 356.06,
    '2022-23': 377.62,
    '2023-24': 397.25,
    '2024-25': 410.64,
}

# Annual CPI increase (%)
CPI_INCREASE_PCT = {
    '2021-22': 5.13,
    '2022-23': 6.05,
    '2023-24': 5.19,
    '2024-25': 3.37,
}

# WPI (2011-12 series)
WPI = {
    '2021-22': 139.4,
    '2022-23': 152.5,
    '2023-24': 151.4,
    '2024-25': 154.90,
}

# Annual WPI increase (%)
WPI_INCREASE_PCT = {
    '2021-22': 12.97,
    '2022-23': 9.4,
    '2023-24': -0.72,
    '2024-25': 2.31,
}

# Weighted inflation: CPI (70%) + WPI (30%)
WEIGHTED_INFLATION_PCT = {
    '2021-22': 7.48,
    '2022-23': 7.06,
    '2023-24': 3.41,
    '2024-25': 3.05,
}

# =============================================================================
# O&M BASE YEAR (from MYT Order 2022)
# =============================================================================

# Base year O&M for SBU-G as approved in TU order dated 14.06.2022
OM_BASE_YEAR_SBU_G = 156.15  # Rs Cr (2021-22) — confirmed by KSERC May 2026

# Component ratios (MYT Order 2022, Table 4.23)
OM_COMPONENT_RATIOS = {
    'employee': 0.7703,   # 77.03%
    'ag':       0.0432,   # 4.32%
    'rm':       0.1865,   # 18.65%
}

# =============================================================================
# CURRENT FISCAL YEAR
# =============================================================================

CURRENT_FY  = '2024-25'
PREVIOUS_FY = '2023-24'

# =============================================================================
# NON-TARIFF INCOME BASELINE (Table 4.61, MYT Order 2022)
# =============================================================================

# MYT approved NTI (Other Income) for SBU-G (Rs Cr)
NTI_BASELINE_SBU_G = {
    '2022-23': 10.30,
    '2023-24': 10.81,
    '2024-25': 11.35,
    '2025-26': 11.92,
    '2026-27': 12.52,
}

# =============================================================================
# LOAN SUMMARY (Table 5.3, Petition 2024-25)
# =============================================================================

LOAN_OPENING_SBU_G      = 1273.68   # Rs Cr (01/04/2024)
LOAN_ADDITIONS_SBU_G    = 278.14    # Rs Cr
LOAN_REPAYMENTS_SBU_G   = 296.27    # Rs Cr
LOAN_CLOSING_SBU_G      = 1255.55   # Rs Cr (31/03/2025)
LOAN_AVERAGE_SBU_G      = 1264.62   # Rs Cr
LOAN_INTEREST_ACTUAL    = 111.74    # Rs Cr (from audited accounts)
LOAN_AVG_RATE_SBU_G     = 8.84      # % weighted average
# =============================================================================

GPF_INTEREST_RATE    = 7.10   # % (confirmed)
SBU_G_GPF_RATIO      = 5.13   # % (same as employee strength ratio)

# Company-wide GPF balances by year (Rs Cr)
GPF_OPENING_BALANCE = {
    '2022-23': 2852.52,
    '2023-24': 3274.32,
    '2024-25': 3364.32,
    '2025-26': 3454.32,
    '2026-27': 3544.32,
}
GPF_CLOSING_BALANCE = {
    '2022-23': 3274.32,
    '2023-24': 3364.32,
    '2024-25': 3454.32,
    '2025-26': 3544.32,
    '2026-27': 3634.32,
}
GPF_TOTAL_INTEREST = {
    '2022-23': 217.50,
    '2023-24': 235.67,
    '2024-25': 242.06,
    '2025-26': 248.45,
    '2026-27': 254.84,
}

# SBU-G employee strength ratio (used for allocation)
SBU_G_EMPLOYEE_RATIO = 5.13  # %

# Total company-wide Master Trust bond interest by year (Rs Cr)
MT_BOND_TOTAL_COMPANY = {
    '2022-23': 610.80,
    '2023-24': 570.08,
    '2024-25': 529.36,
    '2025-26': 488.64,
    '2026-27': 447.92,
}

# MYT approved SBU-G share of bond interest (Rs Cr)
MT_BOND_APPROVED_SBU_G = {
    '2022-23': 32.98,
    '2023-24': 30.78,
    '2024-25': 28.59,
    '2025-26': 26.39,
    '2026-27': 24.19,
}

# Opening GFA excl. land SBU-G (derived from MYT WC requirement 2024-25)
# WC req = O&M/12 + 1% GFA → 78.00 = 14.85 + GFA*0.01 → GFA ≈ 6315 Cr
OPENING_GFA_EXCL_LAND_SBU_G = 6315.0   # Rs Cr (as on 01.04.2024)

# =============================================================================
# INTEREST ON WORKING CAPITAL (Table 4.45, MYT Order 2022)
# =============================================================================

# SBI EBLR as fixed by KSERC for MYT period 2023-24 to 2026-27
SBI_EBLR_RATE = 7.55          # % (effective from 15.06.2022)
IWC_RATE      = 9.55          # % (EBLR + 2% per Regulation 32(2))

# MYT approved IWC amounts for SBU-G (Table 4.46)
IWC_APPROVED_SBU_G = {
    '2022-23': 5.54,
    '2023-24': 6.87,
    '2024-25': 7.45,
    '2025-26': 7.81,
    '2026-27': 8.21,
}

# MYT approved working capital requirement for SBU-G (Table 4.46)
WC_REQUIREMENT_SBU_G = {
    '2022-23': 64.01,
    '2023-24': 71.90,
    '2024-25': 78.00,
    '2025-26': 81.81,
    '2026-27': 85.93,
}

# =============================================================================
# SBU-T SPECIFIC CONSTANTS (from MYT Order 2022 + Petition 2024-25)
# =============================================================================

# Normative loan SBU-T (from petition Chapter 3, para 3.7)
LOAN_OPENING_SBU_T   = 4549.51   # Rs Cr (normative as on 01.04.2024)
LOAN_ADDITIONS_SBU_T = 0.0       # Placeholder — needs Chapter 5 SBU-T table
LOAN_AVG_RATE_SBU_T  = 9.01      # % (derived: TU=409.93 / opening=4549.51)

# GPF allocation ratio for SBU-T (derived: TU=16.32 / company total=242.06)
SBU_T_GPF_RATIO = 6.74   # %

# Master Trust bond allocation ratio for SBU-T
# Derived: TU=47.4 Cr / company total MT 2024-25=529.36 Cr
SBU_T_MT_RATIO  = 8.96   # %

# Opening GFA excl. land SBU-T (from WC table, page 36 petition)
# "1% of Historical cost of plants & Equipment = 82.78 Cr" → GFA = 8278 Cr
OPENING_GFA_EXCL_LAND_SBU_T = 8278.0   # Rs Cr (as on 01.04.2024)

# MYT approved O&M for SBU-T (from ARR Table T6, row 9 approved)
MYT_APPROVED_OM_SBU_T = 644.81   # Rs Cr

# MYT approved NTI for SBU-T (from MYT Order 2022, Table for Transmission)
NTI_BASELINE_SBU_T = {
    '2022-23': 54.00,
    '2023-24': 56.70,
    '2024-25': 57.60,   # From ARR T6 row 21 approved
    '2025-26': 60.48,
    '2026-27': 63.50,
}

# MYT approved IWC for SBU-T (from ARR T6 row 4 approved)
IWC_APPROVED_SBU_T = {
    '2024-25': 26.95,
}

# Transmission incentive target (Regulation 56(2), KSERC TR 2021)
TRANS_AVAILABILITY_TARGET = 98.50   # %

# Revenue gap deferral threshold for transmission incentive
TRANS_INCENTIVE_DEFERRAL_GAP = 5000.0  # Rs Cr

# Unbridged revenue gap from 2023-24 True-up Order (Para 7.23, confirmed KSERC May 2026)
UNBRIDGED_REVENUE_GAP_2024_25 = 6645.301  # Rs Cr (corrected from 6408.37)

# =============================================================================
# IFC — LONG-TERM LOAN CORRECTIONS (KSERC confirmed May 2026, Module 5)
# =============================================================================

# Opening normative loan SBU-G for FY 2024-25
# Confirmed by KSERC: closing balance from last approved TU order
IFC_OPENING_NORMATIVE_LOAN_SBU_G = 1149.51   # Rs Cr

# Disputed APTEL amount included in KSEB's opening loan — must be excluded
# KSERC Module 5 Q2: ₹135.23 Cr still subject to APTEL/court proceedings
IFC_DISPUTED_APTEL_AMOUNT = 135.23   # Rs Cr

# Master Trust items KSEB incorrectly includes in O&M base for WC calculation
# This is a recurring error per KSERC (Module 5 Q4)
IFC_MT_BOND_REPAY_IN_OM   = 21.99   # Rs Cr — MT bond repayment in KSEB O&M
IFC_MT_ADDL_CONTRIB_IN_OM = 21.60   # Rs Cr — MT additional contribution in KSEB O&M

# SBU-T O&M normative norms (Annexure-7, TR 2021, base year 2021-22)
SBU_T_BASE_YEAR_NORMS = {
    'year':      '2021-22',
    'per_bay':   7.121,    # Rs lakh per bay
    'per_mva':   0.788,    # Rs lakh per MVA
    'per_cktkm': 1.438,    # Rs lakh per ckt-km
}
# Inflated norms 2024-25 (after escalation 2022-23: 7.06%, 2023-24: 3.41%, 2024-25: 3.05%)
# KSERC confirmed May 2026: CPI 410.64, WPI 154.9, escalation = 3.05%
SBU_T_NORM_PER_BAY   = 8.124   # Rs lakh per bay   (was 7.884 for 2023-24)
SBU_T_NORM_PER_MVA   = 0.899   # Rs lakh per MVA   (was 0.872 for 2023-24)
SBU_T_NORM_PER_CKTKM = 1.641   # Rs lakh per ckt-km (was 1.592 for 2023-24)

# Edamon-Kochi compensation disbursement history (from T17 petition data)
EDAMON_KOCHI_DISBURSEMENTS = [
    {'total_compensation_cr': 5.20,  'year_of_disbursement': '2019-20',
     'kseb_share_50pct': 2.60,  'amortization_period': 12},
    {'total_compensation_cr': 0.80,  'year_of_disbursement': '2019-20',
     'kseb_share_50pct': 0.40,  'amortization_period': 12},
    {'total_compensation_cr': 12.00, 'year_of_disbursement': '2019-20',
     'kseb_share_50pct': 6.00,  'amortization_period': 12},
    {'total_compensation_cr': 22.00, 'year_of_disbursement': '2020-21',
     'kseb_share_50pct': 11.00, 'amortization_period': 12},
    {'total_compensation_cr': 40.65, 'year_of_disbursement': '2021-22',
     'kseb_share_50pct': 20.33, 'amortization_period': 12},
    {'total_compensation_cr': 25.78, 'year_of_disbursement': '2022-23',
     'kseb_share_50pct': 12.89, 'amortization_period': 12},
]

# Average interest rate for line compensation amortization
TRANS_COMP_AVG_INTEREST = 0.0861   # 8.61%

# =============================================================================
# SBU-D SPECIFIC CONSTANTS (from MYT Order 2022 + Petition 2024-25)
# =============================================================================

# MYT approved power purchase (D89 approved column)
PP_APPROVED_SBU_D = 10716.26   # Rs Cr

# MYT approved O&M for SBU-D
MYT_APPROVED_OM_SBU_D = 3830.59   # Rs Cr (D89 approved)

# MYT approved IFC for SBU-D
IFC_APPROVED_SBU_D = 1499.43   # Rs Cr

# MYT approved Depreciation for SBU-D
DEP_APPROVED_SBU_D = 328.04    # Rs Cr

# MYT approved ROE for SBU-D (14% on equity)
ROE_APPROVED_SBU_D = 253.50    # Rs Cr

# MYT approved NTI for SBU-D
NTI_APPROVED_SBU_D = 841.33    # Rs Cr

# MYT approved Master Trust contribution SBU-D
MT_APPROVED_SBU_D  = 333.42    # Rs Cr

# MYT approved bond repayment SBU-D
BOND_REPAYMENT_SBU_D = 339.42  # Rs Cr

# MYT approved T&D loss target (%) for 2024-25
TD_LOSS_TARGET_SBU_D = 8.50    # % (from MYT Order 2022, Regulation 37)

# GPF allocation ratio for SBU-D
# Derived: TU=157.01 Cr / company total GPF interest=242.06 Cr
SBU_D_GPF_RATIO = 64.86   # %

# Master Trust bond allocation ratio for SBU-D
# Derived: TU=456.14 Cr / company total MT 2024-25=529.36 Cr
SBU_D_MT_RATIO  = 86.17   # %

# WC interest rate used by KSEB (actual, not approved)
IWC_RATE_ACTUAL_SBU_D = 11.15  # % (KSEB claim: 9.15% base + 2%)

# KSERC approved WC interest rate for SBU-D (SBI EBLR + 2%)
IWC_RATE_APPROVED = 9.55       # % (same as SBU-G/T)

# T&D loss reduction gain sharing (Regulation 37, TR 2021)
# KSEB gets 50% of gains from over-achievement of T&D loss target
TD_LOSS_GAIN_SHARE_PCT = 66.7  # %
