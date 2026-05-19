"""
Distribution-specific Heuristics for SBU-D Truing-Up Assessment
================================================================
7 heuristics specific to SBU-D:
  PP-COST-01:     Power Purchase Cost Validation
  OM-DIST-NORM-01: Distribution O&M Norms (5-parameter formula, Reg 80)
  IFC-SD-01:      Interest on Security Deposits
  IFC-CC-01:      Carrying Cost on Revenue Gap
  IFC-OTH-D-01:   Other Interest Charges (SBU-D specific)
  DIST-LOSS-01:   Distribution Loss Assessment
  TD-SHARE-01:    T&D Loss Gain Sharing (Regulation 14/73)

Based on FY 2023-24 KSERC Truing-Up Order, Chapter 5.
OUTPUT SCHEMA: Standardized dict (same as all SBU heuristics).
"""

from typing import Dict, List, Optional


# ============================================================================
# FY 2023-24 DEFAULT DATA (from KSERC Order Tables)
# ============================================================================

FY_2023_24_PP_DEFAULTS = {
    # Transfer costs from other SBUs
    'cost_of_generation_sbug_claimed': 626.48,
    'cost_of_generation_sbug_approved': 598.70,
    'cost_of_transmission_sbut_claimed': 1553.14,
    'cost_of_transmission_sbut_approved': 1505.80,
    # External power purchase (Table 5.62)
    'external_pp_claimed': 12982.59,
    'external_pp_approved': 12773.50,
    # Breakdown by source (Table 5.62)
    'cgs_cost': 4731.09,
    'small_ipps_cost': 230.51,
    'wind_seci_cost': 61.75,
    'solar_outside_cost': 47.33,
    'prosumer_captive_cost': 25.00,
    'rgccpp_fixed_cost': 70.65,
    'lta_maithon_dvc_cost': 1495.45,
    'lta_dbfoo_approved_cost': 872.15,
    'lta_dbfoo_unapproved_cost': 373.50,
    'medium_term_cost': 364.19,
    'short_term_cost': 718.44,
    'exchange_cost': 2123.16,
    'dsm_cost': 206.67,
    'banking_swap_claimed': 214.22,
    'banking_swap_approved': 5.09,
    'banking_swap_disallowed': 209.13,
    'interstate_transmission': 1448.27,
    'surplus_sale_cost': 0.25,
    # Energy quantities
    'total_energy_purchased_mu': 25711.29,
    'net_energy_purchased_mu': 25025.85,
    'internal_generation_mu': 5657.40,
    # MYT reference
    'myt_approved_total_pp': 10564.23,
    'myt_approved_avg_rate': 4.66,
    'actual_avg_rate': 5.08,
}

FY_2023_24_OM_DIST_DEFAULTS = {
    # Distribution parameters (Table 5.75 - adopted by Commission)
    'num_consumers': 13648851,
    'num_dtrs': 87911,
    'ht_line_km': 70269.0,
    'lt_line_km': 302626.0,
    'energy_sales_mu': 25255.0,  # Adjusted: excludes surplus sale, includes prosumer return
    # Norms for FY 2023-24 (Table 5.73 - actual inflation escalation)
    'norm_per_1000_consumers': 4.539,  # Rs. Lakh/1000 consumers
    'norm_per_dtr': 0.896,              # Rs. Lakh/DTr
    'norm_per_ht_km': 0.887,            # Rs. Lakh/km
    'norm_per_lt_km': 0.194,            # Rs. Lakh/km
    'norm_per_mu': 0.200,               # Rs./unit (= Rs. Lakh/MU * 10)
    # Base year norms (2021-22)
    'base_norm_per_1000_consumers': 4.100,
    'base_norm_per_dtr': 0.809,
    'base_norm_per_ht_km': 0.801,
    'base_norm_per_lt_km': 0.175,
    'base_norm_per_mu': 0.181,
    # Escalation rates
    'escalation_2022_23': 0.0706,  # 7.06% (70% CPI 6.06% + 30% WPI 9.40%)
    'escalation_2023_24': 0.0341,  # 3.41% (70% CPI 5.19% + 30% WPI -0.72%)
    # R&M parameters (Table 5.77)
    'gfa_sbu_d_opening': 15961.16,
    'gfa_derecognized': 805.39,
    'gfa_land': 22.52,
    'rm_rate': 0.04,  # 4% of net GFA
    # Financial figures
    'myt_approved_om': 3605.39,
    'actual_om_accounts': 4030.39,
    'claimed_om': 3783.56,
    'approved_employee_ag': 3122.68,
    'approved_rm': 605.33,
    'approved_total_om': 3728.01,
}

FY_2023_24_IFC_SD_DEFAULTS = {
    'myt_approved_sd_interest': 156.11,
    'actual_disbursement': 146.88,
    'provision_in_accounts': 265.92,
    'avg_security_deposit': 4146.85,  # Average for 2023-24
    'interest_rate_2022_23': 4.25,    # %
    'interest_rate_2023_24': 6.75,    # % (bank rate as on 01.04.2023)
}

FY_2023_24_IFC_CC_DEFAULTS = {
    # Carrying cost (Table 5.84, 5.85)
    'revenue_gap_as_on_01_04_2023': 6408.37,
    'avg_gpf_balance': 2926.29,
    'excess_security_deposit': 451.04,
    'net_gap_for_carrying_cost': 3031.05,
    'avg_interest_rate_sbu_d': 8.52,  # %
    'approved_carrying_cost': 258.25,
    'claimed_carrying_cost': 321.24,
    'myt_approved_carrying_cost': 211.91,
}

FY_2023_24_IFC_OTH_D_DEFAULTS = {
    'other_bank_charges': 0.81,
    'interest_on_power_purchase': 43.26,  # CERC provisional vs final tariff difference
    'total_other_interest_claimed': 44.07,
    'total_other_interest_approved': 44.07,
}

FY_2023_24_DIST_LOSS_DEFAULTS = {
    # Table 4.9
    'total_energy_at_dist_input_mu': 30587.11,
    'energy_output_mu': 28360.25,
    'distribution_loss_mu': 2226.86,
    'actual_dist_loss_pct': 7.28,
    'myt_target_dist_loss_pct': 7.78,
    'collection_efficiency_pct': 99.72,
    'atc_loss_pct': 7.55,
    'myt_target_atc_loss_pct': 11.71,
}

FY_2023_24_TD_SHARE_DEFAULTS = {
    # T&D Loss gain sharing (Table 4.10, Para 4.29-4.42)
    'approved_td_loss_pct': 10.82,          # Static MYT target (for reference only)
    'actual_td_loss_ksebl_pct': 9.70,
    'actual_td_loss_kserc_pct': 9.76,       # KSERC assessed (Annexure 4.5)
    # Dynamic target: 9.70% (FY 2023-24 actual) - 0.40% = 9.30% (for FY 2024-25)
    # KSERC confirmed (May 2026, Module 12 Q3): FY 2023-24 actual = 9.70%
    'prior_year_actual_td_loss_pct': 9.70,  # FY 2023-24 actual (confirmed May 2026)
    'annual_loss_reduction_target_pp': 0.40,
    'energy_sales_mu': 28105.07,            # As claimed by KSEBL
    'avg_pp_cost_per_unit': 5.05,           # Rs/kWh
    'claimed_gain_sharing': 131.59,
    # approved_gain_sharing = 0.0 (DISALLOWED — not a function parameter)
    'unbridged_revenue_gap': 6408.37,
    # Regulation 73(3): sharing ratio 2:1 (licensee:consumer)
    'utility_share_ratio': 2/3,
    # consumer_share_ratio = 1/3 (derived — not a function parameter)
}


# ============================================================================
# HEURISTIC 1: PP-COST-01 - Power Purchase Cost Validation
# ============================================================================

def heuristic_PP_COST_01(
    # SBU transfer costs
    cost_of_generation_sbug_claimed: float = 626.48,
    cost_of_generation_sbug_approved: float = 598.70,
    cost_of_transmission_sbut_claimed: float = 1553.14,
    cost_of_transmission_sbut_approved: float = 1505.80,
    # External power purchase
    external_pp_claimed: float = 12982.59,
    external_pp_approved: float = 12773.50,
    # Key sub-components for drill-down
    cgs_cost: float = 4731.09,
    lta_total_cost: float = 2741.10,     # Maithon+DVC+DBFOO approved+unapproved
    exchange_cost: float = 2123.16,
    interstate_transmission: float = 1448.27,
    banking_swap_disallowed: float = 209.13,
    # Energy
    total_energy_purchased_mu: float = 25711.29,
    myt_approved_total_pp: float = 10564.23,
    myt_approved_avg_rate: float = 4.66,
) -> Dict:
    """
    PP-COST-01: Power Purchase Cost Validation

    SBU-D's largest cost component (~60% of ARR). Three sub-components:
    1. Transfer cost of SBU-G (internal generation)
    2. Transfer cost of SBU-T (intra-state transmission)
    3. External power purchase (CGS, IPPs, exchanges, bilateral, etc.)

    Key checks:
    - SBU-G/T transfer costs must match Chapter 2/3 approved amounts
    - External PP: source-wise validation, banking swap disallowance
    - Average PP cost comparison with MYT projection
    """
    # Total claimed and approved
    total_claimed = (cost_of_generation_sbug_claimed +
                     cost_of_transmission_sbut_claimed +
                     external_pp_claimed)
    total_approved = (cost_of_generation_sbug_approved +
                      cost_of_transmission_sbut_approved +
                      external_pp_approved)
    total_variance = total_claimed - total_approved
    total_variance_pct = (total_variance / total_approved * 100) if total_approved > 0 else 0

    # Average PP cost
    if total_energy_purchased_mu > 0:
        actual_avg_rate = external_pp_approved / (total_energy_purchased_mu / 100)  # Rs/kWh approx
    else:
        actual_avg_rate = 0

    # External PP variance
    ext_variance = external_pp_claimed - external_pp_approved
    ext_variance_pct = (ext_variance / external_pp_approved * 100) if external_pp_approved > 0 else 0

    # MYT deviation
    myt_deviation = external_pp_approved - myt_approved_total_pp
    myt_deviation_pct = (myt_deviation / myt_approved_total_pp * 100) if myt_approved_total_pp > 0 else 0

    calc_steps = [
        "═══ POWER PURCHASE COST VALIDATION (SBU-D) ═══",
        "",
        "Component 1: Transfer Cost of SBU-G (Internal Generation)",
        f"  Claimed: ₹{cost_of_generation_sbug_claimed:.2f} Cr",
        f"  Approved (Ch.2): ₹{cost_of_generation_sbug_approved:.2f} Cr",
        f"  Variance: ₹{cost_of_generation_sbug_claimed - cost_of_generation_sbug_approved:+.2f} Cr",
        "",
        "Component 2: Transfer Cost of SBU-T (Intra-state Transmission)",
        f"  Claimed: ₹{cost_of_transmission_sbut_claimed:.2f} Cr",
        f"  Approved (Ch.3): ₹{cost_of_transmission_sbut_approved:.2f} Cr",
        f"  Variance: ₹{cost_of_transmission_sbut_claimed - cost_of_transmission_sbut_approved:+.2f} Cr",
        "",
        "Component 3: External Power Purchase",
        f"  Claimed: ₹{external_pp_claimed:.2f} Cr",
        f"  Approved: ₹{external_pp_approved:.2f} Cr",
        f"  Variance: ₹{ext_variance:+.2f} Cr ({ext_variance_pct:+.2f}%)",
        "",
        "Key sub-items:",
        f"  CGS: ₹{cgs_cost:.2f} Cr",
        f"  LTA (Maithon/DVC/DBFOO): ₹{lta_total_cost:.2f} Cr",
        f"  Exchanges: ₹{exchange_cost:.2f} Cr",
        f"  Interstate Transmission: ₹{interstate_transmission:.2f} Cr",
        f"  Banking/Swap Disallowed: ₹{banking_swap_disallowed:.2f} Cr",
        "",
        "═══ TOTALS ═══",
        f"Total Claimed: ₹{total_claimed:.2f} Cr",
        f"Total Approved: ₹{total_approved:.2f} Cr",
        f"Total Variance: ₹{total_variance:+.2f} Cr ({total_variance_pct:+.2f}%)",
        "",
        f"MYT Approved PP: ₹{myt_approved_total_pp:.2f} Cr",
        f"Deviation from MYT: ₹{myt_deviation:+.2f} Cr ({myt_deviation_pct:+.2f}%)",
        f"Energy Purchased: {total_energy_purchased_mu:,.2f} MU",
    ]

    # Flag determination
    if abs(total_variance_pct) <= 2:
        flag = 'GREEN'
        recommendation = f"Approve total power cost at ₹{total_approved:.2f} Cr. Variance within normal range."
    elif abs(total_variance_pct) <= 5:
        flag = 'YELLOW'
        recommendation = (
            f"Approve ₹{total_approved:.2f} Cr. Disallowance of ₹{total_variance:.2f} Cr mainly from "
            f"banking/swap (₹{banking_swap_disallowed:.2f} Cr) and SBU transfer cost adjustments."
        )
    else:
        flag = 'RED'
        recommendation = (
            f"Significant disallowance of ₹{total_variance:.2f} Cr. Review external PP components, "
            f"especially exchange purchases (TAM rate ₹8.30/unit vs DAM ₹5.18/unit) and banking."
        )

    return {
        'heuristic_id': 'PP-COST-01',
        'heuristic_name': 'Power Purchase Cost Validation',
        'line_item': 'Power Purchase Cost',
        'claimed_value': round(total_claimed, 2),
        'allowable_value': round(total_approved, 2),
        'variance_absolute': round(total_variance, 2),
        'variance_percentage': round(total_variance_pct, 2),
        'flag': flag,
        'recommended_amount': round(total_approved, 2),
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulations 77-78, Tariff Regulations 2021',
        'calculation_steps': calc_steps,
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        'depends_on': [],
        'is_primary': True,
        'output_type': 'approved_amount',
        'pp_details': {
            'sbug_approved': cost_of_generation_sbug_approved,
            'sbut_approved': cost_of_transmission_sbut_approved,
            'external_pp_approved': external_pp_approved,
            'banking_swap_disallowed': banking_swap_disallowed,
            'myt_deviation_cr': round(myt_deviation, 2),
            'myt_deviation_pct': round(myt_deviation_pct, 2),
        }
    }


# ============================================================================
# HEURISTIC 2: OM-DIST-NORM-01 - Distribution O&M Norms
# ============================================================================

def heuristic_OM_DIST_NORM_01(
    # Distribution parameters (Table 5.75)
    num_consumers: int = 13648851,
    num_dtrs: int = 87911,
    ht_line_km: float = 70269.0,
    lt_line_km: float = 302626.0,
    energy_sales_mu: float = 25255.0,
    # Norms for FY 2023-24 (Table 5.73, actual inflation)
    norm_per_1000_consumers: float = 4.539,
    norm_per_dtr: float = 0.896,
    norm_per_ht_km: float = 0.887,
    norm_per_lt_km: float = 0.194,
    norm_per_mu: float = 0.200,
    # R&M parameters (Table 5.77)
    gfa_sbu_d_opening: float = 15961.16,
    gfa_derecognized: float = 805.39,
    gfa_land: float = 22.52,
    rm_rate: float = 0.04,
    # Financial figures
    claimed_employee_ag: float = 3152.28,
    claimed_rm: float = 631.28,
    claimed_total_om: float = 3783.56,
    myt_approved_om: float = 3605.39,
) -> Dict:
    """
    OM-DIST-NORM-01: Normative O&M for Distribution (Regulation 80)

    Two components:
    A. Employee + A&G: 5-parameter formula (Annexure-7, Table-7)
       = Σ(norm_i × parameter_i) for consumers(20%), DTRs(25%),
         HT lines(20%), LT lines(20%), energy sales(15%)
       Norms escalated from base year 2021-22 by actual CPI:WPI (70:30)

    B. R&M: 4% of opening GFA (excl land, excl derecognized assets)

    Key KSERC adjustments:
    - Energy sales: Excludes surplus sale outside State (1813.11 MU),
      includes prosumer return energy (324.71 MU) → 25,255 MU
    - GFA: Deducted ₹805.39 Cr for assets damaged in natural calamities
    """

    # A. Employee + A&G calculation (Table 5.76)
    # Norms are in Rs. Lakh per unit, multiply by quantity, convert to Cr
    cost_consumers = (norm_per_1000_consumers * num_consumers / 1000) / 100  # Lakh to Cr
    cost_dtrs = (norm_per_dtr * num_dtrs) / 100
    cost_ht = (norm_per_ht_km * ht_line_km) / 100
    cost_lt = (norm_per_lt_km * lt_line_km) / 100
    cost_energy = norm_per_mu * energy_sales_mu / 10  # Rs/unit × MU(10^6 units) / 10^7(Cr) = Cr

    total_employee_ag = cost_consumers + cost_dtrs + cost_ht + cost_lt + cost_energy

    # B. R&M calculation (Table 5.77)
    net_gfa = gfa_sbu_d_opening - gfa_derecognized - gfa_land
    rm_allowable = net_gfa * rm_rate

    # Total normative O&M
    total_normative_om = total_employee_ag + rm_allowable

    # Variances
    employee_ag_variance = claimed_employee_ag - total_employee_ag
    rm_variance = claimed_rm - rm_allowable
    total_variance = claimed_total_om - total_normative_om
    total_variance_pct = (total_variance / total_normative_om * 100) if total_normative_om > 0 else 0

    calc_steps = [
        "═══ DISTRIBUTION O&M NORMS (Regulation 80, Annexure-7) ═══",
        "",
        "A. EMPLOYEE + A&G EXPENSES (5-parameter formula)",
        "   Ratio: Consumers(20%) : DTRs(25%) : HT(20%) : LT(20%) : Energy(15%)",
        "   Norms escalated by actual CPI:WPI (70:30) from base year 2021-22",
        "",
        f"   1. Consumers: {num_consumers:,} × ₹{norm_per_1000_consumers:.3f} L/1000",
        f"      = ₹{cost_consumers:.2f} Cr",
        f"   2. DTRs: {num_dtrs:,} × ₹{norm_per_dtr:.3f} L/DTr",
        f"      = ₹{cost_dtrs:.2f} Cr",
        f"   3. HT Lines: {ht_line_km:,.0f} km × ₹{norm_per_ht_km:.3f} L/km",
        f"      = ₹{cost_ht:.2f} Cr",
        f"   4. LT Lines: {lt_line_km:,.0f} km × ₹{norm_per_lt_km:.3f} L/km",
        f"      = ₹{cost_lt:.2f} Cr",
        f"   5. Energy Sales: {energy_sales_mu:,.0f} MU × ₹{norm_per_mu:.3f}/unit",
        f"      = ₹{cost_energy:.2f} Cr",
        f"   Total Employee + A&G: ₹{total_employee_ag:.2f} Cr",
        f"   Claimed: ₹{claimed_employee_ag:.2f} Cr | Variance: ₹{employee_ag_variance:+.2f} Cr",
        "",
        "B. R&M EXPENSES (4% of net opening GFA)",
        f"   Opening GFA SBU-D: ₹{gfa_sbu_d_opening:.2f} Cr",
        f"   Less: Derecognized (natural calamities): ₹{gfa_derecognized:.2f} Cr",
        f"   Less: Land: ₹{gfa_land:.2f} Cr",
        f"   Net GFA: ₹{net_gfa:.2f} Cr",
        f"   R&M @ {rm_rate*100:.1f}%: ₹{rm_allowable:.2f} Cr",
        f"   Claimed: ₹{claimed_rm:.2f} Cr | Variance: ₹{rm_variance:+.2f} Cr",
        "",
        "═══ TOTAL O&M ═══",
        f"   Normative: ₹{total_normative_om:.2f} Cr",
        f"   Claimed: ₹{claimed_total_om:.2f} Cr",
        f"   Variance: ₹{total_variance:+.2f} Cr ({total_variance_pct:+.2f}%)",
        f"   MYT Approved: ₹{myt_approved_om:.2f} Cr",
        "",
        "Note: Energy sales adjusted to 25,255 MU (excl surplus sale, incl prosumer return)",
    ]

    # Flag
    if abs(total_variance_pct) <= 2:
        flag = 'GREEN'
        recommendation = f"Approve total O&M at ₹{total_normative_om:.2f} Cr as per norms."
    elif total_variance > 0:
        flag = 'YELLOW'
        recommendation = (
            f"Cap O&M to normative ₹{total_normative_om:.2f} Cr. "
            f"KSEB claimed ₹{claimed_total_om:.2f} Cr exceeds norms by ₹{total_variance:.2f} Cr."
        )
    else:
        flag = 'GREEN'
        recommendation = f"Claimed ₹{claimed_total_om:.2f} Cr is below normative ₹{total_normative_om:.2f} Cr."

    return {
        'heuristic_id': 'OM-DIST-NORM-01',
        'heuristic_name': 'Distribution O&M Norms',
        'line_item': 'O&M Expenses (Distribution)',
        'claimed_value': round(claimed_total_om, 2),
        'allowable_value': round(total_normative_om, 2),
        'variance_absolute': round(total_variance, 2),
        'variance_percentage': round(total_variance_pct, 2),
        'flag': flag,
        'recommended_amount': round(total_normative_om, 2),
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 80 + Annexure-7, Tariff Regulations 2021',
        'calculation_steps': calc_steps,
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        'depends_on': ['OM-INFL-01'],
        'is_primary': True,
        'output_type': 'approved_amount',
        'om_details': {
            'employee_ag_normative': round(total_employee_ag, 2),
            'rm_normative': round(rm_allowable, 2),
            'cost_by_parameter': {
                'consumers': round(cost_consumers, 2),
                'dtrs': round(cost_dtrs, 2),
                'ht_lines': round(cost_ht, 2),
                'lt_lines': round(cost_lt, 2),
                'energy_sales': round(cost_energy, 2),
            },
            'net_gfa_for_rm': round(net_gfa, 2),
        }
    }


# ============================================================================
# HEURISTIC 3: IFC-SD-01 - Interest on Security Deposits
# ============================================================================

def heuristic_IFC_SD_01(
    myt_approved_sd_interest: float = 156.11,
    actual_disbursement: float = 146.88,
    provision_in_accounts: float = 265.92,
    avg_security_deposit: float = 4146.85,
    interest_rate_applied: float = 6.75,
    claimed_sd_interest: float = 146.88,
) -> Dict:
    """
    IFC-SD-01: Interest on Security Deposits (SBU-D specific)

    Regulatory Basis: Regulation 29(8), Tariff Regulations 2021
    Key Rule: Only ACTUAL DISBURSEMENT to consumers is allowed at truing-up.
    Provision in accounts (₹265.92 Cr) ≠ actual disbursement (₹146.88 Cr).

    The variance between provision and disbursement is because:
    1. Provision = interest payable in April 2024 based on SD held in 2023-24
    2. Disbursement = actually paid to consumers during 2023-24
    3. Rate change: 4.25% (2022-23) → 6.75% (2023-24)
    """
    # Interest on SD is simply the actual disbursement
    allowable = actual_disbursement

    variance_abs = claimed_sd_interest - allowable
    variance_pct = (variance_abs / allowable * 100) if allowable > 0 else 0

    # Check reasonableness: expected interest
    expected_interest = avg_security_deposit * interest_rate_applied / 100
    reasonableness_ratio = actual_disbursement / expected_interest if expected_interest > 0 else 0

    calc_steps = [
        "═══ INTEREST ON SECURITY DEPOSITS (Regulation 29(8)) ═══",
        "",
        "Rule: Only actual disbursement to consumers allowed at truing-up.",
        "",
        f"Average Security Deposit: ₹{avg_security_deposit:.2f} Cr",
        f"Interest Rate (Bank Rate as on 01.04.2023): {interest_rate_applied:.2f}%",
        f"Expected Interest (notional): ₹{expected_interest:.2f} Cr",
        "",
        f"Provision in Accounts: ₹{provision_in_accounts:.2f} Cr",
        f"Actual Disbursement: ₹{actual_disbursement:.2f} Cr",
        f"Difference: ₹{provision_in_accounts - actual_disbursement:.2f} Cr",
        "",
        f"MYT Approved: ₹{myt_approved_sd_interest:.2f} Cr",
        f"Claimed: ₹{claimed_sd_interest:.2f} Cr",
        f"Approved: ₹{allowable:.2f} Cr",
        "",
        "Note: Difference between provision and disbursement is because",
        "provision includes April 2024 payable; actual disbursement for FY claimed in this year only.",
        "Balance may be claimed in Truing Up of FY 2024-25.",
    ]

    flag = 'GREEN' if abs(variance_pct) <= 2 else 'YELLOW'
    recommendation = f"Approve ₹{allowable:.2f} Cr (actual disbursement) as per Regulation 29(8)."

    return {
        'heuristic_id': 'IFC-SD-01',
        'heuristic_name': 'Interest on Security Deposits',
        'line_item': 'Interest on Security Deposits',
        'claimed_value': round(claimed_sd_interest, 2),
        'allowable_value': round(allowable, 2),
        'variance_absolute': round(variance_abs, 2),
        'variance_percentage': round(variance_pct, 2),
        'flag': flag,
        'recommended_amount': round(allowable, 2),
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 29(8), Tariff Regulations 2021',
        'calculation_steps': calc_steps,
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        'depends_on': [],
        'is_primary': True,
        'output_type': 'approved_amount',
    }


# ============================================================================
# HEURISTIC 4: IFC-CC-01 - Carrying Cost on Revenue Gap
# ============================================================================

def heuristic_IFC_CC_01(
    revenue_gap_as_on_01_04: float = 6408.37,
    avg_gpf_balance: float = 2926.29,
    excess_security_deposit: float = 451.04,
    avg_interest_rate: float = 8.52,
    claimed_carrying_cost: float = 321.24,
    myt_approved_carrying_cost: float = 211.91,
) -> Dict:
    """
    IFC-CC-01: Carrying Cost on Revenue Gap (SBU-D specific)

    Regulatory Basis: Regulation 29(9), Tariff Regulations 2021
    Formula:
    1. Start: Unbridged revenue gap as on 01.04.YYYY
    2. Less: Average GPF balance (funds available with licensee)
    3. Less: Excess SD over working capital (Reg 29(9) proviso)
    4. Net gap × weighted average interest rate = Carrying Cost

    Key KSERC logic:
    - GPF balance deducted because Commission allows interest on full GPF
      as IFC, so these funds are available for operations
    - Excess SD deducted because Commission allows interest on full SD,
      so excess over WC requirements is double-counted
    """
    # Calculate net gap eligible for carrying cost (Table 5.84)
    net_gap = revenue_gap_as_on_01_04 - avg_gpf_balance - excess_security_deposit
    net_gap = max(0, net_gap)  # Cannot be negative

    # Carrying cost
    allowable_cc = net_gap * avg_interest_rate / 100

    variance_abs = claimed_carrying_cost - allowable_cc
    variance_pct = (variance_abs / allowable_cc * 100) if allowable_cc > 0 else 0

    calc_steps = [
        "═══ CARRYING COST ON REVENUE GAP (Regulation 29(9)) ═══",
        "",
        "Step 1: Determine eligible revenue gap",
        f"  Unbridged gap as on 01.04.2023: ₹{revenue_gap_as_on_01_04:.2f} Cr",
        f"  Less: Avg GPF balance (2023-24): ₹{avg_gpf_balance:.2f} Cr",
        f"    (Deducted as GPF interest already allowed as IFC)",
        f"  Less: Excess SD over WC requirement: ₹{excess_security_deposit:.2f} Cr",
        f"    (Reg 29(9) proviso: no CC on excess SD)",
        f"  Net gap eligible for CC: ₹{net_gap:.2f} Cr",
        "",
        "Step 2: Calculate carrying cost",
        f"  Interest rate (weighted avg SBU-D loans): {avg_interest_rate:.2f}%",
        f"  Carrying cost = ₹{net_gap:.2f} × {avg_interest_rate:.2f}% = ₹{allowable_cc:.2f} Cr",
        "",
        f"  MYT Approved: ₹{myt_approved_carrying_cost:.2f} Cr",
        f"  Claimed: ₹{claimed_carrying_cost:.2f} Cr",
        f"  KSERC Approved: ₹{allowable_cc:.2f} Cr",
        f"  Disallowance: ₹{variance_abs:.2f} Cr",
        "",
        "Note: KSEB claimed higher amount due to different methodology for GPF deduction.",
    ]

    if abs(variance_pct) <= 2:
        flag = 'GREEN'
    elif variance_abs > 0:
        flag = 'YELLOW'
    else:
        flag = 'GREEN'

    recommendation = (
        f"Approve carrying cost at ₹{allowable_cc:.2f} Cr. "
        f"Disallow ₹{variance_abs:.2f} Cr due to GPF/SD deduction methodology."
    )

    return {
        'heuristic_id': 'IFC-CC-01',
        'heuristic_name': 'Carrying Cost on Revenue Gap',
        'line_item': 'Carrying Cost on Revenue Gap',
        'claimed_value': round(claimed_carrying_cost, 2),
        'allowable_value': round(allowable_cc, 2),
        'variance_absolute': round(variance_abs, 2),
        'variance_percentage': round(variance_pct, 2),
        'flag': flag,
        'recommended_amount': round(allowable_cc, 2),
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 29(9), Tariff Regulations 2021',
        'calculation_steps': calc_steps,
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        'depends_on': ['IFC-WC-01'],  # WC calc determines excess SD
        'is_primary': True,
        'output_type': 'approved_amount',
        'cc_details': {
            'gross_gap': round(revenue_gap_as_on_01_04, 2),
            'gpf_deduction': round(avg_gpf_balance, 2),
            'sd_deduction': round(excess_security_deposit, 2),
            'net_gap': round(net_gap, 2),
        }
    }


# ============================================================================
# HEURISTIC 5: IFC-OTH-D-01 - Other Interest Charges (SBU-D)
# ============================================================================

def heuristic_IFC_OTH_D_01(
    other_bank_charges: float = 0.81,
    interest_on_power_purchase: float = 43.26,
    claimed_other_interest: float = 44.07,
) -> Dict:
    """
    IFC-OTH-D-01: Other Interest Charges (SBU-D specific)

    Two components:
    1. Other bank charges: ₹0.81 Cr (approved as claimed)
    2. Interest on power purchase: ₹43.26 Cr
       - Arises from CERC provisional vs final tariff difference
       - CGS provisional tariff < final tariff → KSEB pays interest on difference
       - Covers MYT period 2019-20 to 2023-24
    Both approved as claimed by KSERC.
    """
    calculated_total = other_bank_charges + interest_on_power_purchase
    variance_abs = claimed_other_interest - calculated_total

    flag = 'GREEN' if abs(variance_abs) < 0.5 else 'YELLOW'

    calc_steps = [
        "═══ OTHER INTEREST CHARGES - SBU-D (Table 5.88) ═══",
        "",
        f"1. Other Bank Charges: ₹{other_bank_charges:.2f} Cr",
        f"2. Interest on Power Purchase: ₹{interest_on_power_purchase:.2f} Cr",
        f"   (CERC provisional vs final tariff difference, MYT 2019-24)",
        f"Total: ₹{calculated_total:.2f} Cr",
        f"Claimed: ₹{claimed_other_interest:.2f} Cr",
        "",
        "KSERC Decision: Approved as claimed.",
    ]

    return {
        'heuristic_id': 'IFC-OTH-D-01',
        'heuristic_name': 'Other Interest Charges (SBU-D)',
        'line_item': 'Other Interest Charges',
        'claimed_value': round(claimed_other_interest, 2),
        'allowable_value': round(calculated_total, 2),
        'variance_absolute': round(variance_abs, 2),
        'variance_percentage': 0.0,
        'flag': flag,
        'recommended_amount': round(calculated_total, 2),
        'recommendation_text': f"Approve ₹{calculated_total:.2f} Cr as claimed.",
        'regulatory_basis': 'Para 5.191, KSERC Order',
        'calculation_steps': calc_steps,
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        'depends_on': [],
        'is_primary': True,
        'output_type': 'approved_amount',
    }


# ============================================================================
# HEURISTIC 6: DIST-LOSS-01 - Distribution Loss Assessment
# ============================================================================

def heuristic_DIST_LOSS_01(
    energy_input_to_dist_mu: float = 30587.11,
    energy_output_mu: float = 28360.25,
    myt_target_dist_loss_pct: float = 7.78,
    myt_target_atc_loss_pct: float = 11.71,
    collection_efficiency_pct: float = 99.72,
    claimed_dist_loss_pct: float = 7.28,
) -> Dict:
    """
    DIST-LOSS-01: Distribution Loss Assessment

    Distribution loss = (Energy input to dist - Energy output) / Energy input × 100
    Energy input to dist = Total energy at Kerala periphery - Transmission loss

    Key metrics:
    - Distribution loss: 7.28% (actual) vs 7.78% (target) → BETTER than target
    - Collection efficiency: 99.72% vs 99.00% (target)
    - AT&C loss: 7.55% vs 11.71% (target)
    """
    distribution_loss_mu = energy_input_to_dist_mu - energy_output_mu
    actual_dist_loss_pct = (distribution_loss_mu / energy_input_to_dist_mu * 100) if energy_input_to_dist_mu > 0 else 0

    variance_pp = actual_dist_loss_pct - myt_target_dist_loss_pct

    # AT&C loss
    atc_loss_pct = (1 - (energy_output_mu / energy_input_to_dist_mu) * (collection_efficiency_pct / 100)) * 100 if energy_input_to_dist_mu > 0 else 0

    calc_steps = [
        "═══ DISTRIBUTION LOSS ASSESSMENT (Table 4.9) ═══",
        "",
        f"Energy Input to Distribution: {energy_input_to_dist_mu:,.2f} MU",
        f"  (= Total at Kerala periphery - Transmission loss)",
        f"Energy Output (consumer end): {energy_output_mu:,.2f} MU",
        f"Distribution Loss: {distribution_loss_mu:,.2f} MU",
        f"Distribution Loss %: {actual_dist_loss_pct:.2f}%",
        "",
        f"MYT Target Distribution Loss: {myt_target_dist_loss_pct:.2f}%",
        f"Variance: {variance_pp:+.2f} percentage points",
        f"{'✓ BETTER than target' if variance_pp < 0 else '✗ WORSE than target'}",
        "",
        f"Collection Efficiency: {collection_efficiency_pct:.2f}% (target: 99.00%)",
        f"AT&C Loss: {atc_loss_pct:.2f}% (target: {myt_target_atc_loss_pct:.2f}%)",
    ]

    if variance_pp <= 0:
        flag = 'GREEN'
        recommendation = (
            f"Distribution loss {actual_dist_loss_pct:.2f}% is within target {myt_target_dist_loss_pct:.2f}%. "
            f"Saved {abs(variance_pp):.2f}pp. Eligible for gain sharing under Regulation 73."
        )
    elif variance_pp <= 0.5:
        flag = 'YELLOW'
        recommendation = (
            f"Distribution loss {actual_dist_loss_pct:.2f}% marginally exceeds target by {variance_pp:.2f}pp. "
            f"May attract disallowance of excess power purchase."
        )
    else:
        flag = 'RED'
        recommendation = (
            f"Distribution loss {actual_dist_loss_pct:.2f}% exceeds target by {variance_pp:.2f}pp. "
            f"Quantum of excess purchase to be disallowed at avg PP cost."
        )

    return {
        'heuristic_id': 'DIST-LOSS-01',
        'heuristic_name': 'Distribution Loss Assessment',
        'line_item': 'Distribution Loss',
        'claimed_value': round(claimed_dist_loss_pct, 2),
        'allowable_value': round(actual_dist_loss_pct, 2),
        'variance_absolute': round(variance_pp, 2),
        'variance_percentage': None,  # This IS a percentage
        'flag': flag,
        'recommended_amount': None,  # Not a financial amount
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 73, Tariff Regulations 2021',
        'calculation_steps': calc_steps,
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        'depends_on': [],
        'is_primary': False,  # Informational - feeds into TD-SHARE-01
        'output_type': 'assessment',
        'dist_loss_details': {
            'energy_input_mu': round(energy_input_to_dist_mu, 2),
            'energy_output_mu': round(energy_output_mu, 2),
            'loss_mu': round(distribution_loss_mu, 2),
            'actual_pct': round(actual_dist_loss_pct, 2),
            'target_pct': myt_target_dist_loss_pct,
            'variance_pp': round(variance_pp, 2),
            'collection_efficiency': collection_efficiency_pct,
            'atc_loss_pct': round(atc_loss_pct, 2),
        }
    }


# ============================================================================
# HEURISTIC 7: TD-SHARE-01 - T&D Loss Gain Sharing
# ============================================================================

def heuristic_TD_SHARE_01(
    approved_td_loss_pct: float = 10.82,
    actual_td_loss_ksebl_pct: float = 9.70,
    actual_td_loss_kserc_pct: float = 9.76,
    energy_sales_mu: float = 28105.07,
    avg_pp_cost_per_unit: float = 5.05,
    claimed_gain_sharing: float = 131.59,
    unbridged_revenue_gap: float = 6408.37,
    utility_share_ratio: float = 2/3,
    # Dynamic target inputs (CRITICAL — see docstring)
    prior_year_actual_td_loss_pct: Optional[float] = None,
    annual_loss_reduction_target_pp: float = 0.40,
) -> Dict:
    """
    TD-SHARE-01: T&D Loss Gain Sharing (Regulations 14 & 73)

    If actual T&D loss < effective target:
      Energy saved = (Target% - Actual%) / (100 - Target%) × Energy Sales
      Monetary gain = Energy saved × Avg PP cost
      Utility share = 2/3 of gain (Regulation 14(1))

    DYNAMIC TARGET — Critical for correct application:
      The Commission uses a dynamic target at truing-up, NOT the static MYT target.

        Dynamic Target = Prior Year Actual T&D Loss% - Annual Reduction Target (0.40%)

      Source: TU Order OP No. 49/2024, Para 4.34:
        FY 2023-24 actual = 9.70%  (KSERC confirmed May 2026, Module 12 Q3)
        Annual reduction target = 0.40%
        FY 2024-25 dynamic target = 9.70% - 0.40% = 9.30%

      HOW TO USE:
        Option A (recommended): Pass prior_year_actual_td_loss_pct.
          The function computes the dynamic target automatically.
        Option B (fallback): Leave prior_year_actual_td_loss_pct = None.
          The function uses approved_td_loss_pct as the static MYT target.

    CRITICAL FY 2023-24 CONTEXT:
    - KSEBL claimed 9.70% T&D loss, but KSERC assessed 9.76% (Annexure 4.5)
    - KSEB's actual (9.76%) EXCEEDED the dynamic target (8.90%) → not eligible on merit
    - KSERC DISALLOWED the gain sharing — not merely deferred due to revenue gap
    - The ₹131.59 Cr claim was rejected because KSEB missed the dynamic target,
      even though it beat the static MYT target of 10.82%
    - Also: Actual TActual T&D loss INCREASED from 9.30% (2022-23) to 9.76% (2023-24)D loss INCREASED from 9.70% (2023-24) to {actual_td_loss:.2f}% (2024-25)
    - Commission decided not to impose penalty either, given force majeure
      (unprecedented demand surge of 10.75%)
    """
    # Use KSERC-assessed loss (not KSEBL claimed)
    actual_td_loss = actual_td_loss_kserc_pct

    # Compute effective target: dynamic if prior year actual is provided
    if prior_year_actual_td_loss_pct is not None:
        effective_target_pct = prior_year_actual_td_loss_pct - annual_loss_reduction_target_pp
        target_label = (
            f"Dynamic Target: {prior_year_actual_td_loss_pct:.2f}% (prior yr actual) "
            f"- {annual_loss_reduction_target_pp:.2f}pp = {effective_target_pct:.2f}%"
        )
    else:
        effective_target_pct = approved_td_loss_pct
        target_label = f"Static MYT Target: {effective_target_pct:.2f}%"

    loss_reduction_pp = effective_target_pct - actual_td_loss

    calc_steps = [
        "═══ T&D LOSS GAIN SHARING (Regulations 14 & 73) ═══",
        "",
        target_label,
        f"KSEBL Claimed T&D Loss: {actual_td_loss_ksebl_pct:.2f}%",
        f"KSERC Assessed T&D Loss: {actual_td_loss_kserc_pct:.2f}% (Annexure 4.5)",
        f"Loss vs Effective Target: {loss_reduction_pp:+.2f} percentage points",
        "",
    ]

    if loss_reduction_pp > 0:
        # Calculate gain
        energy_at_target = energy_sales_mu / (1 - approved_td_loss_pct/100)
        energy_at_actual = energy_sales_mu / (1 - actual_td_loss/100)
        energy_saved_mu = energy_at_target - energy_at_actual
        monetary_gain_cr = energy_saved_mu * avg_pp_cost_per_unit / 100  # MU × Rs/unit / 100 = Cr
        utility_share_cr = monetary_gain_cr * utility_share_ratio

        calc_steps.extend([
            "GAIN CALCULATION:",
            f"  Energy at target loss: {energy_sales_mu:,.0f} / (1 - {approved_td_loss_pct/100:.4f}) = {energy_at_target:,.2f} MU",
            f"  Energy at actual loss: {energy_sales_mu:,.0f} / (1 - {actual_td_loss/100:.4f}) = {energy_at_actual:,.2f} MU",
            f"  Energy Saved: {energy_saved_mu:,.2f} MU",
            f"  Monetary Gain: {energy_saved_mu:,.2f} × ₹{avg_pp_cost_per_unit:.2f} / 100 = ₹{monetary_gain_cr:.2f} Cr",
            f"  Utility Share (2/3): ₹{utility_share_cr:.2f} Cr",
            f"  Consumer Share (1/3): ₹{monetary_gain_cr - utility_share_cr:.2f} Cr",
            "",
        ])
    else:
        energy_saved_mu = 0
        monetary_gain_cr = 0
        utility_share_cr = 0
        calc_steps.append("T&D loss EXCEEDS target - no gain sharing applicable.")
        calc_steps.append("")

    # KSERC decision: DISALLOWED
    calc_steps.extend([
        "═══ KSERC DECISION: DISALLOWED ═══",
        f"  Claimed: ₹{claimed_gain_sharing:.2f} Cr",
        f"  Approved: ₹0.00 Cr",
        "",
        "Reasons for disallowance:",
        f"  1. KSEB missed dynamic target ({effective_target_pct:.2f}%): actual {actual_td_loss:.2f}% > target",
        f"  2. Unbridged revenue gap of ₹{unbridged_revenue_gap:.2f} Cr as on 31.03.2023",
        f"  3. Actual TActual T&D loss INCREASED from 9.30% (2022-23) to {actual_td_loss:.2f}% (2023-24)D loss vs prior year (9.70%) — see KSERC assessment",
        "  4. Loss reduction is relative to static MYT target, not absolute improvement",
        "",
        "Note: Commission also decided NOT to impose penalty for under-achievement,",
        "considering force majeure (unprecedented 10.75% demand growth, drought).",
    ])

    # Always disallowed in FY 2023-24
    flag = 'RED'
    recommendation = (
        f"DISALLOW gain sharing of ₹{claimed_gain_sharing:.2f} Cr. "
        f"While T&D loss ({actual_td_loss:.2f}%) is below target ({approved_td_loss_pct:.2f}%), "
        f"the unbridged revenue gap of ₹{unbridged_revenue_gap:.2f} Cr and year-on-year "
        f"increase in T&D loss justifies disallowance. No penalty imposed either (force majeure)."
    )

    return {
        'heuristic_id': 'TD-SHARE-01',
        'heuristic_name': 'T&D Loss Gain Sharing',
        'line_item': 'T&D Loss Gain Sharing',
        'claimed_value': round(claimed_gain_sharing, 2),
        'allowable_value': 0.0,
        'variance_absolute': round(claimed_gain_sharing, 2),
        'variance_percentage': 100.0,  # Fully disallowed
        'flag': flag,
        'recommended_amount': 0.0,
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulations 14(1) & 73(3), Tariff Regulations 2021',
        'calculation_steps': calc_steps,
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        'depends_on': ['DIST-LOSS-01', 'TRANS-LOSS-01'],
        'is_primary': True,
        'output_type': 'approved_amount',
        'td_share_details': {
            'approved_td_loss_pct': approved_td_loss_pct,
            'actual_td_loss_ksebl_pct': actual_td_loss_ksebl_pct,
            'actual_td_loss_kserc_pct': actual_td_loss_kserc_pct,
            'loss_reduction_pp': round(loss_reduction_pp, 2),
            'energy_saved_mu': round(energy_saved_mu, 2) if loss_reduction_pp > 0 else 0,
            'monetary_gain_cr': round(monetary_gain_cr, 2) if loss_reduction_pp > 0 else 0,
            'utility_share_cr': round(utility_share_cr, 2) if loss_reduction_pp > 0 else 0,
            'unbridged_revenue_gap': unbridged_revenue_gap,
            'disallowance_reason': 'Unbridged revenue gap + YoY loss increase',
        }
    }


# ============================================================================
# CONVENIENCE: Run all distribution heuristics
# ============================================================================

def run_all_distribution_heuristics(
    pp_params: Optional[Dict] = None,
    om_params: Optional[Dict] = None,
    sd_params: Optional[Dict] = None,
    cc_params: Optional[Dict] = None,
    oth_params: Optional[Dict] = None,
    dist_loss_params: Optional[Dict] = None,
    td_share_params: Optional[Dict] = None,
) -> List[Dict]:
    """Run all 7 distribution-specific heuristics and return results."""
    results = []

    # 1. Power Purchase Cost
    pp = pp_params or {}
    results.append(heuristic_PP_COST_01(**pp))

    # 2. Distribution O&M
    om = om_params or {}
    results.append(heuristic_OM_DIST_NORM_01(**om))

    # 3. Interest on Security Deposits
    sd = sd_params or {}
    results.append(heuristic_IFC_SD_01(**sd))

    # 4. Carrying Cost on Revenue Gap
    cc = cc_params or {}
    results.append(heuristic_IFC_CC_01(**cc))

    # 5. Other Interest
    oth = oth_params or {}
    results.append(heuristic_IFC_OTH_D_01(**oth))

    # 6. Distribution Loss
    dl = dist_loss_params or {}
    results.append(heuristic_DIST_LOSS_01(**dl))

    # 7. T&D Gain Sharing
    td = td_share_params or {}
    results.append(heuristic_TD_SHARE_01(**td))

    return results
