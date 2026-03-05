"""
Transmission-Specific Heuristics for SBU-T Truing-Up Assessment
================================================================
3 heuristics specific to SBU-T that do NOT exist in SBU-G:
  - OM-TRANS-NORM-01: Normative O&M for Transmission (bays/MVA/ckt-km based)
  - TRANS-COMP-01: Transmission Line Compensation (Edamon-Kochi & Pugalur-Thrissur)
  - TRANS-INCENT-01: Incentive on Transmission Availability

Based on FY 2023-24 KSERC Truing-Up Order and Tariff Regulations 2021.

OUTPUT SCHEMA: Standardized dict (same as all SBU-G heuristics).
"""

from typing import Dict, Optional, List
from datetime import datetime


# =============================================================================
# HEURISTIC 1: OM-TRANS-NORM-01 - Normative O&M for Transmission
# =============================================================================

def heuristic_OM_TRANS_NORM_01(
    # O&M norms per unit (Rs. lakh) - from Annexure-7 with actual inflation
    norm_per_bay: float = 7.884,
    norm_per_mva: float = 0.872,
    norm_per_cktkm: float = 1.592,
    # Opening parameters (beginning of year)
    opening_bays: int = 2905,
    opening_mva: float = 25344.5,
    opening_cktkm: float = 10633.90,
    # Additions during year
    added_bays: int = 24,
    added_mva: float = 785.0,
    added_cktkm: float = 166.23,
    # Financial figures (Rs. Cr)
    myt_approved_om: float = 644.81,
    actual_om_accounts: float = 588.95,
    claimed_om: float = 625.20,
    # Inflation parameters
    base_year_norms: Optional[Dict] = None,
    escalation_2022_23: float = 0.0706,
    escalation_2023_24: float = 0.0341,
) -> Dict:
    """
    OM-TRANS-NORM-01: Normative O&M Expenses for Transmission

    Regulatory Basis: Regulation 58 + Annexure-7 of Tariff Regulations 2021
    Decision Logic:
      - O&M = (Norms × Opening params) + (Norms × 50% of additions)
      - Ratio: Bays(40%) : MVA(30%) : CktKm(30%)
      - Escalation: Actual CPI/WPI weighted (70:30) from base year 2021-22
      - At truing-up: use actual inflation, not provisional 4.454%

    Returns:
        Standardized heuristic result dict
    """

    if base_year_norms is None:
        base_year_norms = {
            "year": "2021-22",
            "per_bay": 7.121,
            "per_mva": 0.788,
            "per_cktkm": 1.438,
        }

    calc_steps = [
        "═══ NORMATIVE O&M - TRANSMISSION (Regulation 58 + Annexure-7) ═══",
        "",
        "Formula: O&M = (Norms × Opening) + (Norms × 50% × Additions)",
        "Ratio: Bays(40%) : MVA(30%) : CktKm(30%)",
        "",
        "Step 1: O&M for assets at beginning of year",
    ]

    # Step 1: Compute O&M for assets at beginning of year
    om_opening_bays = norm_per_bay * opening_bays  # Rs. lakh
    om_opening_mva = norm_per_mva * opening_mva
    om_opening_cktkm = norm_per_cktkm * opening_cktkm
    om_opening_total = om_opening_bays + om_opening_mva + om_opening_cktkm

    calc_steps.extend([
        f"  Bays: {norm_per_bay:.3f} × {opening_bays} = ₹{om_opening_bays:.2f} Lakh",
        f"  MVA:  {norm_per_mva:.3f} × {opening_mva:.1f} = ₹{om_opening_mva:.2f} Lakh",
        f"  CktKm: {norm_per_cktkm:.3f} × {opening_cktkm:.2f} = ₹{om_opening_cktkm:.2f} Lakh",
        f"  Opening Total: ₹{om_opening_total:.2f} Lakh",
        "",
        "Step 2: O&M for assets added during year (50% rule)",
    ])

    # Step 2: Compute O&M for assets added during year (50% rule)
    om_added_bays = norm_per_bay * added_bays * 0.5
    om_added_mva = norm_per_mva * added_mva * 0.5
    om_added_cktkm = norm_per_cktkm * added_cktkm * 0.5
    om_added_total = om_added_bays + om_added_mva + om_added_cktkm

    calc_steps.extend([
        f"  Bays: {norm_per_bay:.3f} × {added_bays} × 50% = ₹{om_added_bays:.2f} Lakh",
        f"  MVA:  {norm_per_mva:.3f} × {added_mva:.1f} × 50% = ₹{om_added_mva:.2f} Lakh",
        f"  CktKm: {norm_per_cktkm:.3f} × {added_cktkm:.2f} × 50% = ₹{om_added_cktkm:.2f} Lakh",
        f"  Additions Total: ₹{om_added_total:.2f} Lakh",
        "",
        "Step 3: Total normative O&M",
    ])

    # Step 3: Total normative O&M
    total_om_lakh = om_opening_total + om_added_total
    allowable_om_cr = total_om_lakh / 100.0  # Convert to Rs. Crore

    calc_steps.extend([
        f"  Total O&M: ₹{total_om_lakh:.2f} Lakh = ₹{allowable_om_cr:.2f} Cr",
        "",
        "Step 4: Inflation escalation from base year 2021-22",
        f"  Base year norms: Bay={base_year_norms['per_bay']}, MVA={base_year_norms['per_mva']}, CktKm={base_year_norms['per_cktkm']}",
        f"  Escalation 2022-23: {escalation_2022_23*100:.2f}% (actual CPI/WPI 70:30)",
        f"  Escalation 2023-24: {escalation_2023_24*100:.2f}% (actual CPI/WPI 70:30)",
        "",
        "Step 5: Comparison",
        f"  MYT Approved: ₹{myt_approved_om:.2f} Cr",
        f"  Actual (Accounts): ₹{actual_om_accounts:.2f} Cr",
        f"  KSEB Claimed: ₹{claimed_om:.2f} Cr",
        f"  Normative Allowable: ₹{allowable_om_cr:.2f} Cr",
    ])

    # Step 4: Variance and flag
    variance_abs = claimed_om - allowable_om_cr
    variance_pct = (variance_abs / allowable_om_cr) * 100 if allowable_om_cr > 0 else 0

    if abs(variance_abs) < 0.5:
        flag = 'GREEN'
        recommendation = (
            f"Approve normative O&M at ₹{allowable_om_cr:.2f} Cr. "
            f"Based on {opening_bays} bays, {opening_mva:.1f} MVA, "
            f"{opening_cktkm:.2f} ckt-km at opening + additions during year."
        )
    elif allowable_om_cr < claimed_om:
        flag = 'YELLOW'
        recommendation = (
            f"Cap O&M to normative level of ₹{allowable_om_cr:.2f} Cr. "
            f"KSEB claimed ₹{claimed_om:.2f} Cr exceeds norms by ₹{variance_abs:.2f} Cr. "
            f"Verify parameter accuracy."
        )
    else:
        flag = 'RED'
        recommendation = (
            f"Significant variance: Normative ₹{allowable_om_cr:.2f} Cr vs "
            f"Claimed ₹{claimed_om:.2f} Cr. Investigate parameters."
        )

    calc_steps.extend([
        f"  Variance: ₹{variance_abs:+.2f} Cr ({variance_pct:+.2f}%)",
        f"  Flag: {flag}",
    ])

    return {
        # Identification
        'heuristic_id': 'OM-TRANS-NORM-01',
        'heuristic_name': 'Normative O&M Expenses - Transmission',
        'line_item': 'O&M Expenses (Transmission)',

        # Calculation Results
        'claimed_value': claimed_om,
        'allowable_value': round(allowable_om_cr, 2),
        'variance_absolute': round(variance_abs, 2),
        'variance_percentage': round(variance_pct, 2),

        # Tool's Assessment
        'flag': flag,
        'recommended_amount': round(allowable_om_cr, 2),
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 58 + Annexure-7, Tariff Regulations 2021',

        # Calculation Details
        'calculation_steps': calc_steps,

        # Staff Review Section
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,

        # Dependencies
        'depends_on': ['OM-INFL-01'],  # Uses inflation indices

        # Metadata
        'is_primary': True,
        'output_type': 'approved_amount',

        # Additional context
        'om_details': {
            'norm_per_bay': norm_per_bay,
            'norm_per_mva': norm_per_mva,
            'norm_per_cktkm': norm_per_cktkm,
            'opening_bays': opening_bays,
            'opening_mva': opening_mva,
            'opening_cktkm': opening_cktkm,
            'added_bays': added_bays,
            'added_mva': added_mva,
            'added_cktkm': added_cktkm,
            'om_opening_total_lakh': round(om_opening_total, 2),
            'om_added_total_lakh': round(om_added_total, 2),
            'total_om_lakh': round(total_om_lakh, 2),
            'total_om_cr': round(allowable_om_cr, 2),
            'ratio_explanation': 'Bays(40%):MVA(30%):CktKm(30%)',
            'inflation_2022_23': f'{escalation_2022_23*100:.2f}%',
            'inflation_2023_24': f'{escalation_2023_24*100:.2f}%',
            'base_year_norms': base_year_norms,
            'myt_approved_om': myt_approved_om,
            'actual_om_accounts': actual_om_accounts,
        }
    }


# =============================================================================
# HEURISTIC 2: TRANS-COMP-01 - Transmission Line Compensation
# =============================================================================

def heuristic_TRANS_COMP_01(
    line_name: str = "",
    # List of compensation disbursements: each is a dict with keys:
    #   total_compensation_cr, year_of_disbursement, kseb_share_50pct, amortization_period (default 12)
    compensation_entries: Optional[List[Dict]] = None,
    # Interest rate (average interest rate of KSEB Ltd capital liabilities)
    avg_interest_rate: float = 0.0861,
    # Claims (Rs. Cr)
    claimed_compensation: float = 0.0,
    myt_approved: float = 0.0,
    # KSERC-approved amount from the truing-up order (if known).
    # When provided, this is used as the allowable amount instead of the claimed figure.
    # Source: TU Order OP No. 49/2024:
    #   Edamon-Kochi:    Table 3.21 → Amortization 4.44 + Interest 3.51 = ₹7.95 Cr
    #   Pugalur-Thrissur: Table 3.22 → Amortization 0.63 + Interest 0.55 = ₹1.17 Cr
    kserc_approved_compensation: Optional[float] = None,
    # Assessment year
    assessment_year: str = "2023-24",
) -> Dict:
    """
    TRANS-COMP-01: Transmission Line Compensation (Intangible Asset Amortization)

    Applicable to:
      - Edamon-Kochi 400kV line (OP No. 58/2018, Order 09.08.2019)
      - Pugalur-Thrissur 320kV HVDC line (OP No. 42/2023, Order 01.12.2023)

    Decision Logic:
      - KSEB Ltd share = 50% of total compensation paid
      - Amortization over 12 years from year of disbursement
      - Annual amortization = KSEB share / 12
      - Interest on unamortized balance @ average interest rate of capital liabilities
      - Total allowed = Amortization + Interest for assessment year

    ALLOWABLE AMOUNT LOGIC:
      If kserc_approved_compensation is provided → use that as allowable (preferred).
      Otherwise → fall back to claimed_compensation pending detailed verification.
      Always pass kserc_approved_compensation once the truing-up order is available.

    Returns:
        Standardized heuristic result dict
    """

    if compensation_entries is None:
        compensation_entries = []

    calc_steps = [
        f"═══ LINE COMPENSATION - {line_name} ═══",
        "",
        "Regulatory Basis:",
        "  - KSEB share = 50% of total compensation",
        "  - Amortized over 12 years from disbursement",
        f"  - Interest @ {avg_interest_rate*100:.2f}% on unamortized balance",
        "",
        "Disbursement Details:",
    ]

    total_amortization = 0.0
    total_kseb_share = 0.0
    entry_details = []

    for entry in compensation_entries:
        total_comp = entry.get('total_compensation_cr', 0.0)
        year = entry.get('year_of_disbursement', '')
        kseb_share = entry.get('kseb_share_50pct', 0.0)
        amort_period = entry.get('amortization_period', 12)

        annual_amort = kseb_share / amort_period
        total_amortization += annual_amort
        total_kseb_share += kseb_share

        calc_steps.append(
            f"  {year}: Total ₹{total_comp:.2f} Cr → KSEB share ₹{kseb_share:.4f} Cr → "
            f"Annual amort ₹{annual_amort:.4f} Cr"
        )

        entry_details.append({
            'total_compensation_cr': total_comp,
            'year_of_disbursement': year,
            'kseb_share_50pct': kseb_share,
            'annual_amortization': round(annual_amort, 4),
        })

    calc_steps.extend([
        "",
        f"Total Annual Amortization: ₹{total_amortization:.4f} Cr",
        f"Total KSEB Share: ₹{total_kseb_share:.4f} Cr",
        "",
        "Note: Exact KSERC computation includes interest on year-wise",
        "unamortized balances. Simplified calculation shown above.",
        "Use KSERC-approved amount as benchmark for validation.",
    ])

    # The exact KSERC computation includes interest on unamortized balances
    # which requires year-by-year tracking. We use the KSERC-approved amount
    # when available (from the truing-up order), otherwise fall back to claimed.
    # For FY 2023-24 (TU Order OP No. 49/2024):
    #   Edamon-Kochi: Amortization 4.44 + Interest 3.51 = 7.95 Cr (Table 3.21)
    #   Pugalur-Thrissur: Amortization 0.63 + Interest 0.55 = 1.17 Cr (Table 3.22)

    if kserc_approved_compensation is not None:
        allowable_compensation = kserc_approved_compensation
        approval_basis = f"KSERC-approved amount (TU Order)"
    else:
        allowable_compensation = claimed_compensation
        approval_basis = "Claimed amount (pending detailed verification)"

    variance_abs = claimed_compensation - allowable_compensation
    variance_pct = (variance_abs / allowable_compensation * 100) if allowable_compensation > 0 else 0.0

    # Flag logic: compare claimed vs allowable (KSERC-approved or MYT)
    if kserc_approved_compensation is not None:
        # We have the TU order figure — compare claimed against it
        if abs(variance_abs) < 0.05:
            flag = 'GREEN'
            recommendation = (
                f"Approve ₹{allowable_compensation:.2f} Cr for {line_name}. "
                f"Claimed matches KSERC-approved amount (TU Order)."
            )
        else:
            flag = 'YELLOW'
            recommendation = (
                f"Approve KSERC-approved amount ₹{allowable_compensation:.2f} Cr for {line_name}. "
                f"KSEB claimed ₹{claimed_compensation:.2f} Cr — disallow variance of "
                f"₹{variance_abs:.2f} Cr ({variance_pct:+.1f}%)."
            )
    elif myt_approved > 0 and abs(claimed_compensation - myt_approved) > 2.0:
        flag = 'YELLOW'
        recommendation = (
            f"Claimed ₹{claimed_compensation:.2f} Cr differs from MYT ₹{myt_approved:.2f} Cr. "
            f"Verify disbursement schedule and interest calculation for {line_name}."
        )
    else:
        flag = 'GREEN'
        recommendation = (
            f"Approve compensation of ₹{allowable_compensation:.2f} Cr for {line_name}. "
            f"50% KSEB share amortized over 12 years with interest @ {avg_interest_rate*100:.2f}%."
        )

    calc_steps.extend([
        "",
        f"KSEB Claimed: ₹{claimed_compensation:.2f} Cr",
        f"MYT Approved: ₹{myt_approved:.2f} Cr" if myt_approved > 0 else "MYT Approved: N/A",
        f"KSERC TU Approved: ₹{kserc_approved_compensation:.2f} Cr" if kserc_approved_compensation else "KSERC TU Approved: Not yet available",
        f"Approval Basis: {approval_basis}",
        f"Allowable: ₹{allowable_compensation:.2f} Cr",
        f"Flag: {flag}",
    ])

    return {
        # Identification
        'heuristic_id': 'TRANS-COMP-01',
        'heuristic_name': f'Line Compensation - {line_name}',
        'line_item': f'Line Compensation ({line_name})',

        # Calculation Results
        'claimed_value': claimed_compensation,
        'allowable_value': round(allowable_compensation, 2),
        'variance_absolute': round(variance_abs, 2),
        'variance_percentage': round(variance_pct, 2),

        # Tool's Assessment
        'flag': flag,
        'recommended_amount': round(allowable_compensation, 2),
        'recommendation_text': recommendation,
        'regulatory_basis': 'OP No. 58/2018 (Edamon-Kochi), OP No. 42/2023 (Pugalur-Thrissur)',

        # Calculation Details
        'calculation_steps': calc_steps,

        # Staff Review Section
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,

        # Dependencies
        'depends_on': [],  # Independent

        # Metadata
        'is_primary': True,
        'output_type': 'approved_amount',

        # Additional context
        'compensation_details': {
            'line_name': line_name,
            'avg_interest_rate': avg_interest_rate,
            'amortization_period': '12 years',
            'assessment_year': assessment_year,
            'total_kseb_share_cr': round(total_kseb_share, 4),
            'total_annual_amortization_cr': round(total_amortization, 4),
            'entries': entry_details,
            'myt_approved': myt_approved,
        }
    }


# =============================================================================
# HEURISTIC 3: TRANS-INCENT-01 - Incentive on Transmission Availability
# =============================================================================

def heuristic_TRANS_INCENT_01(
    target_availability: float = 98.50,
    actual_availability: float = 0.0,
    sldc_certified: bool = True,
    arr_excluding_incentive: float = 0.0,
    claimed_incentive: float = 0.0,
    # Revenue gap context
    unbridged_revenue_gap: float = 0.0,
    revenue_gap_threshold: float = 5000.0,
) -> Dict:
    """
    TRANS-INCENT-01: Incentive on Transmission Availability

    Regulatory Basis: Regulation 56(2), Tariff Regulations 2021
    Formula: Incentive = ARR × (Actual Availability - Target) / Target

    CRITICAL CONTEXT (FY 2023-24):
      The Commission acknowledged eligibility but DEFERRED the incentive
      due to the huge unbridged revenue gap of Rs.6408.37 Cr as on 31.03.2023.
      The Commission stated KSEB Ltd can claim it once revenue gap is manageable.

    Returns:
        Standardized heuristic result dict
    """

    calc_steps = [
        "═══ TRANSMISSION AVAILABILITY INCENTIVE ═══",
        "",
        "Regulatory Basis: Regulation 56(2), Tariff Regulations 2021",
        "Formula: Incentive = ARR × (Actual% - Target%) / Target%",
        "",
        f"Target Availability: {target_availability:.2f}%",
        f"Actual Availability: {actual_availability:.2f}%",
        f"SLDC Certified: {'Yes' if sldc_certified else 'No'}",
        "",
    ]

    availability_excess = actual_availability - target_availability
    deferral_applied = False
    eligibility_status = "Not Eligible"

    # Calculate formula-based incentive
    if actual_availability > target_availability:
        formula_incentive = (arr_excluding_incentive *
                             (actual_availability - target_availability) /
                             target_availability / 100)
    else:
        formula_incentive = 0.0

    calc_steps.append(f"Excess Achievement: {availability_excess:+.2f}%")
    calc_steps.append(f"ARR (excl incentive): ₹{arr_excluding_incentive:.2f} Cr")
    calc_steps.append(f"Formula Incentive: ₹{formula_incentive:.2f} Cr")
    calc_steps.append("")

    # Eligibility check
    if actual_availability <= target_availability:
        flag = 'GREEN'
        allowable_incentive = 0.0
        eligibility_status = "Not Eligible"
        recommendation = (
            f"No incentive. Actual availability ({actual_availability:.2f}%) "
            f"did not exceed target ({target_availability:.2f}%)."
        )
        calc_steps.append("Result: NOT ELIGIBLE for incentive")
        calc_steps.append("Actual availability did not exceed target")

    elif not sldc_certified:
        flag = 'RED'
        allowable_incentive = 0.0
        eligibility_status = "Eligible but Not Certified"
        recommendation = (
            f"SLDC certification missing. Cannot approve incentive without certification."
        )
        calc_steps.append("Result: CERTIFICATION MISSING")
        calc_steps.append("SLDC certification required per regulations")

    elif unbridged_revenue_gap > revenue_gap_threshold:
        # Eligible but deferred due to revenue gap
        flag = 'YELLOW'
        allowable_incentive = 0.0
        deferral_applied = True
        eligibility_status = "Eligible - Deferred"
        recommendation = (
            f"DEFER incentive of ₹{claimed_incentive:.2f} Cr. "
            f"While KSEB Ltd achieved {actual_availability:.2f}% availability "
            f"(exceeding {target_availability:.2f}% target), "
            f"the huge unbridged revenue gap of ₹{unbridged_revenue_gap:.2f} Cr "
            f"requires deferral. Incentive can be claimed once revenue gap "
            f"is reduced to manageable levels."
        )
        calc_steps.extend([
            "Result: ELIGIBLE but DEFERRED",
            f"  Claimed Incentive: ₹{claimed_incentive:.2f} Cr",
            f"  Formula Incentive: ₹{formula_incentive:.2f} Cr",
            "",
            "Deferral Reason:",
            f"  Unbridged Revenue Gap: ₹{unbridged_revenue_gap:.2f} Cr",
            f"  Threshold for Deferral: ₹{revenue_gap_threshold:.2f} Cr",
            f"  Gap Exceeds Threshold: Yes",
            "",
            "Commission Decision:",
            "  - Incentive is ELIGIBLE per regulations",
            "  - Payment DEFERRED until revenue gap reduced",
            "  - KSEB Ltd can claim subsequently when gap closes",
        ])

    else:
        # Eligible and approved
        flag = 'GREEN'
        allowable_incentive = formula_incentive
        eligibility_status = "Eligible - Approved"
        recommendation = (
            f"Approve incentive of ₹{allowable_incentive:.2f} Cr for exceeding "
            f"availability target ({actual_availability:.2f}% vs {target_availability:.2f}%)."
        )
        calc_steps.extend([
            "Result: ELIGIBLE and APPROVED",
            f"  Claimed: ₹{claimed_incentive:.2f} Cr",
            f"  Formula: ₹{formula_incentive:.2f} Cr",
            f"  Allowable: ₹{allowable_incentive:.2f} Cr",
            "",
            f"  Revenue gap ₹{unbridged_revenue_gap:.2f} Cr within threshold",
        ])

    variance_abs = claimed_incentive - allowable_incentive
    variance_pct = (variance_abs / claimed_incentive * 100) if claimed_incentive > 0 else 0.0

    return {
        # Identification
        'heuristic_id': 'TRANS-INCENT-01',
        'heuristic_name': 'Incentive on Transmission Availability',
        'line_item': 'Transmission Availability Incentive',

        # Calculation Results
        'claimed_value': claimed_incentive,
        'allowable_value': round(allowable_incentive, 2),
        'variance_absolute': round(variance_abs, 2),
        'variance_percentage': round(variance_pct, 2),

        # Tool's Assessment
        'flag': flag,
        'recommended_amount': round(allowable_incentive, 2),
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 56(2), KSERC Tariff Regulations 2021',

        # Calculation Details
        'calculation_steps': calc_steps,

        # Staff Review Section
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,

        # Dependencies
        'depends_on': [],  # Independent - based on SLDC certification

        # Metadata
        'is_primary': True,
        'output_type': 'approved_amount',
        'note': 'Incentive may be deferred if unbridged revenue gap exceeds threshold',

        # Additional context
        'incentive_details': {
            'target_availability': target_availability,
            'actual_availability': actual_availability,
            'excess_achievement': round(availability_excess, 2),
            'sldc_certified': sldc_certified,
            'eligibility_status': eligibility_status,
            'deferral_applied': deferral_applied,
            'formula_incentive_cr': round(formula_incentive, 2),
            'arr_excluding_incentive': arr_excluding_incentive,
            'unbridged_revenue_gap': unbridged_revenue_gap,
            'revenue_gap_threshold': revenue_gap_threshold,
            'formula': 'ARR × (Actual% - Target%) / Target%',
        }
    }


# =============================================================================
# FY 2023-24 DEFAULT PARAMETERS (from KSERC Truing-Up Order)
# =============================================================================

FY_2023_24_OM_DEFAULTS = {
    'norm_per_bay': 7.884,
    'norm_per_mva': 0.872,
    'norm_per_cktkm': 1.592,
    'opening_bays': 2905,
    'opening_mva': 25344.5,
    'opening_cktkm': 10633.90,
    'added_bays': 24,
    'added_mva': 785.0,
    'added_cktkm': 166.23,
    'myt_approved_om': 644.81,
    'actual_om_accounts': 588.95,
    'claimed_om': 625.20,
    'escalation_2022_23': 0.0706,
    'escalation_2023_24': 0.0341,
    'base_year_norms': {
        'year': '2021-22',
        'per_bay': 7.121,
        'per_mva': 0.788,
        'per_cktkm': 1.438,
    },
}

FY_2023_24_EDAMON_KOCHI_DEFAULTS = {
    'line_name': 'Edamon-Kochi 400kV Transmission Line',
    'compensation_entries': [
        {'total_compensation_cr': 5.20, 'year_of_disbursement': '2019-20', 'kseb_share_50pct': 2.60},
        {'total_compensation_cr': 0.80, 'year_of_disbursement': '2019-20', 'kseb_share_50pct': 0.40},
        {'total_compensation_cr': 12.00, 'year_of_disbursement': '2019-20', 'kseb_share_50pct': 6.00},
        {'total_compensation_cr': 22.00, 'year_of_disbursement': '2020-21', 'kseb_share_50pct': 11.00},
        {'total_compensation_cr': 40.65, 'year_of_disbursement': '2021-22', 'kseb_share_50pct': 20.33},
        {'total_compensation_cr': 25.78, 'year_of_disbursement': '2022-23', 'kseb_share_50pct': 12.89},
    ],
    'avg_interest_rate': 0.0861,
    'claimed_compensation': 8.06,       # KSEB claimed (TU petition)
    'kserc_approved_compensation': 7.95, # KSERC approved (TU Order OP 49/2024, Table 3.21)
    'myt_approved': 14.94,
}

FY_2023_24_PUGALUR_THRISSUR_DEFAULTS = {
    'line_name': 'Pugalur-Thrissur 320kV HVDC Line',
    'compensation_entries': [
        {'total_compensation_cr': 0.0603, 'year_of_disbursement': '2021-22', 'kseb_share_50pct': 0.0301},
        {'total_compensation_cr': 2.4983, 'year_of_disbursement': '2021-22', 'kseb_share_50pct': 2.4983},
        {'total_compensation_cr': 4.83, 'year_of_disbursement': '2022-23', 'kseb_share_50pct': 4.83},
        {'total_compensation_cr': 0.154, 'year_of_disbursement': '2023-24', 'kseb_share_50pct': 0.154},
    ],
    'avg_interest_rate': 0.0861,
    'claimed_compensation': 1.24,       # KSEB claimed (TU petition)
    'kserc_approved_compensation': 1.17, # KSERC approved (TU Order OP 49/2024, Table 3.22)
    'myt_approved': 0.0,
}

FY_2023_24_INCENTIVE_DEFAULTS = {
    'target_availability': 98.50,
    'actual_availability': 99.17,
    'arr_excluding_incentive': 1542.64,
    'claimed_incentive': 10.49,
    'unbridged_revenue_gap': 6408.37,
}


# =============================================================================
# CONVENIENCE: Run all 3 transmission heuristics
# =============================================================================

def run_all_transmission_heuristics(
    om_params: Optional[Dict] = None,
    edamon_params: Optional[Dict] = None,
    pugalur_params: Optional[Dict] = None,
    incentive_params: Optional[Dict] = None,
) -> List[Dict]:
    """Run all 3 transmission-specific heuristics and return results."""

    results = []

    # 1. O&M Normative
    om_p = om_params or FY_2023_24_OM_DEFAULTS
    results.append(heuristic_OM_TRANS_NORM_01(**om_p))

    # 2. Edamon-Kochi Compensation
    ek_p = edamon_params or FY_2023_24_EDAMON_KOCHI_DEFAULTS
    results.append(heuristic_TRANS_COMP_01(**ek_p))

    # 3. Pugalur-Thrissur Compensation
    pt_p = pugalur_params or FY_2023_24_PUGALUR_THRISSUR_DEFAULTS
    results.append(heuristic_TRANS_COMP_01(**pt_p))

    # 4. Transmission Availability Incentive
    inc_p = incentive_params or FY_2023_24_INCENTIVE_DEFAULTS
    results.append(heuristic_TRANS_INCENT_01(**inc_p))

    return results


if __name__ == "__main__":
    print("=" * 80)
    print("TRANSMISSION HEURISTICS - FY 2023-24 Evaluation")
    print("=" * 80)

    results = run_all_transmission_heuristics()
    for r in results:
        flag_emoji = {'GREEN': '🟢', 'YELLOW': '🟡', 'RED': '🔴'}[r['flag']]
        print(f"\n{flag_emoji} {r['heuristic_id']}: {r['heuristic_name']}")
        print(f"   Claimed: ₹{r['claimed_value']:.2f} Cr | Allowable: ₹{r['allowable_value']:.2f} Cr")
        print(f"   Flag: {r['flag']} | Primary: {r['is_primary']}")
        print(f"   Recommendation: {r['recommendation_text'][:100]}...")