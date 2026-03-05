"""
T&D Loss Heuristics for Truing-Up Assessment
==============================================
4 heuristics for Transmission & Distribution Loss analysis:
  - TRANS-LOSS-01: Transmission Loss Assessment
  - DIST-LOSS-01: Distribution Loss Assessment
  - TD-LOSS-COMBINED-01: Combined T&D Loss Assessment
  - TD-REWARD-01: T&D Loss Reduction Reward/Penalty

Based on FY 2023-24 KSERC Truing-Up Order, Chapter 4.

OUTPUT SCHEMA: Standardized dict (same as all SBU-G heuristics).
"""

from typing import Dict, Optional, List
from datetime import datetime


# =============================================================================
# HEURISTIC 1: TRANS-LOSS-01 - Transmission Loss Assessment
# =============================================================================

def heuristic_TRANS_LOSS_01(
    total_energy_input: float = 0.0,        # Total energy input to transmission system (MU)
    transmission_loss_mu: float = 0.0,      # Actual transmission loss (MU)
    myt_approved_trans_loss_pct: float = 0.0,  # MYT approved transmission loss %
    # Voltage-level breakdown (optional)
    loss_400kv_mu: float = 0.0,
    loss_220kv_mu: float = 0.0,
    loss_110kv_mu: float = 0.0,
    loss_66kv_mu: float = 0.0,
    # Peak demand
    peak_demand_mw: float = 0.0,
    # Methodology
    methodology: str = "Mi-Power Load Flow Study (CEA/FOR methodology)",
) -> Dict:
    """
    TRANS-LOSS-01: Transmission Loss Assessment

    Evaluates whether actual transmission losses are within approved norms.
    Transmission loss is measured up to 66kV level using load flow studies.

    Returns:
        Standardized heuristic result dict
    """

    calc_steps = [
        "═══ TRANSMISSION LOSS ASSESSMENT ═══",
        "",
        f"Methodology: {methodology}",
        f"Peak Demand: {peak_demand_mw:.0f} MW",
        "",
        "Calculation:",
        f"  Total Energy Input: {total_energy_input:,.2f} MU",
        f"  Transmission Loss: {transmission_loss_mu:,.2f} MU",
    ]

    # Compute actual transmission loss %
    if total_energy_input > 0:
        actual_trans_loss_pct = (transmission_loss_mu / total_energy_input) * 100
    else:
        actual_trans_loss_pct = 0.0

    variance_pp = actual_trans_loss_pct - myt_approved_trans_loss_pct

    calc_steps.extend([
        f"  Actual Loss %: {actual_trans_loss_pct:.2f}%",
        f"  MYT Approved: {myt_approved_trans_loss_pct:.2f}%",
        f"  Variance: {variance_pp:+.2f} percentage points",
    ])

    # Voltage-level breakdown if available
    if any([loss_400kv_mu, loss_220kv_mu, loss_110kv_mu, loss_66kv_mu]):
        calc_steps.extend([
            "",
            "Voltage-Level Breakdown:",
            f"  400kV: {loss_400kv_mu:.2f} MU",
            f"  220kV: {loss_220kv_mu:.2f} MU",
            f"  110kV: {loss_110kv_mu:.2f} MU",
            f"  66kV:  {loss_66kv_mu:.2f} MU",
        ])

    # Flag determination
    if variance_pp <= 0:
        flag = 'GREEN'
        recommendation = (
            f"Transmission loss {actual_trans_loss_pct:.2f}% is within/below "
            f"approved {myt_approved_trans_loss_pct:.2f}%. "
            f"Loss of {transmission_loss_mu:.2f} MU on input of "
            f"{total_energy_input:.2f} MU."
        )
    elif variance_pp <= 0.5:
        flag = 'YELLOW'
        recommendation = (
            f"Transmission loss {actual_trans_loss_pct:.2f}% marginally exceeds "
            f"approved {myt_approved_trans_loss_pct:.2f}% by {variance_pp:.2f}pp. "
            f"Review load flow study methodology."
        )
    else:
        flag = 'RED'
        recommendation = (
            f"Transmission loss {actual_trans_loss_pct:.2f}% significantly exceeds "
            f"approved {myt_approved_trans_loss_pct:.2f}% by {variance_pp:.2f}pp. "
            f"Investigate causes."
        )

    calc_steps.extend(["", f"Flag: {flag}"])

    return {
        # Identification
        'heuristic_id': 'TRANS-LOSS-01',
        'heuristic_name': 'Transmission Loss Assessment',
        'line_item': 'T&D Losses (Transmission)',

        # Calculation Results
        'claimed_value': round(actual_trans_loss_pct, 2),  # Actual loss % as "claimed"
        'allowable_value': myt_approved_trans_loss_pct,     # Target as "allowable"
        'variance_absolute': round(variance_pp, 2),
        'variance_percentage': None,  # Not applicable for % vs % comparison

        # Tool's Assessment
        'flag': flag,
        'recommended_amount': None,  # Not an amount-based heuristic
        'recommendation_text': recommendation,
        'regulatory_basis': 'Chapter 4, Truing-Up Order; Load flow methodology per CEA/FOR',

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
        'is_primary': False,  # Informational - feeds into TD-LOSS-COMBINED-01
        'output_type': 'assessment',

        # Additional context
        'loss_details': {
            'total_energy_input_mu': total_energy_input,
            'transmission_loss_mu': transmission_loss_mu,
            'actual_loss_pct': round(actual_trans_loss_pct, 2),
            'target_loss_pct': myt_approved_trans_loss_pct,
            'variance_pp': round(variance_pp, 2),
            'peak_demand_mw': peak_demand_mw,
            'methodology': methodology,
            'loss_400kv_mu': loss_400kv_mu,
            'loss_220kv_mu': loss_220kv_mu,
            'loss_110kv_mu': loss_110kv_mu,
            'loss_66kv_mu': loss_66kv_mu,
        }
    }


# =============================================================================
# HEURISTIC 2: DIST-LOSS-01 - Distribution Loss Assessment
# =============================================================================

def heuristic_DIST_LOSS_01(
    energy_input_to_dist_mu: float = 0.0,
    energy_sold_mu: float = 0.0,
    distribution_loss_mu: float = 0.0,
    myt_approved_dist_loss_pct: float = 0.0,
    # Sub-categories
    ht_loss_mu: float = 0.0,
    lt_loss_mu: float = 0.0,
) -> Dict:
    """
    DIST-LOSS-01: Distribution Loss Assessment

    Evaluates distribution-level losses (HT and LT network).

    Returns:
        Standardized heuristic result dict
    """

    calc_steps = [
        "═══ DISTRIBUTION LOSS ASSESSMENT ═══",
        "",
        f"Energy Input to Distribution: {energy_input_to_dist_mu:,.2f} MU",
        f"Energy Sold: {energy_sold_mu:,.2f} MU",
        f"Distribution Loss: {distribution_loss_mu:,.2f} MU",
    ]

    if energy_input_to_dist_mu > 0:
        actual_dist_loss_pct = (distribution_loss_mu / energy_input_to_dist_mu) * 100
    else:
        actual_dist_loss_pct = 0.0

    variance_pp = actual_dist_loss_pct - myt_approved_dist_loss_pct

    calc_steps.extend([
        f"  Actual Loss %: {actual_dist_loss_pct:.2f}%",
        f"  MYT Approved: {myt_approved_dist_loss_pct:.2f}%",
        f"  Variance: {variance_pp:+.2f} percentage points",
    ])

    if ht_loss_mu > 0 or lt_loss_mu > 0:
        calc_steps.extend([
            "",
            "Network Breakdown:",
            f"  HT Loss: {ht_loss_mu:.2f} MU",
            f"  LT Loss: {lt_loss_mu:.2f} MU",
        ])

    # Flag determination
    if variance_pp <= 0:
        flag = 'GREEN'
        recommendation = (
            f"Distribution loss {actual_dist_loss_pct:.2f}% is within/below "
            f"approved {myt_approved_dist_loss_pct:.2f}%."
        )
    elif variance_pp <= 0.5:
        flag = 'YELLOW'
        recommendation = (
            f"Distribution loss {actual_dist_loss_pct:.2f}% marginally exceeds "
            f"target by {variance_pp:.2f}pp."
        )
    else:
        flag = 'RED'
        recommendation = (
            f"Distribution loss {actual_dist_loss_pct:.2f}% exceeds "
            f"target {myt_approved_dist_loss_pct:.2f}% by {variance_pp:.2f}pp."
        )

    calc_steps.extend(["", f"Flag: {flag}"])

    return {
        # Identification
        'heuristic_id': 'DIST-LOSS-01',
        'heuristic_name': 'Distribution Loss Assessment',
        'line_item': 'T&D Losses (Distribution)',

        # Calculation Results
        'claimed_value': round(actual_dist_loss_pct, 2),
        'allowable_value': myt_approved_dist_loss_pct,
        'variance_absolute': round(variance_pp, 2),
        'variance_percentage': None,

        # Tool's Assessment
        'flag': flag,
        'recommended_amount': None,
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation on T&D Loss targets, Tariff Regulations 2021',

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
        'depends_on': [],

        # Metadata
        'is_primary': False,
        'output_type': 'assessment',

        # Additional context
        'loss_details': {
            'energy_input_to_dist_mu': energy_input_to_dist_mu,
            'energy_sold_mu': energy_sold_mu,
            'distribution_loss_mu': distribution_loss_mu,
            'actual_loss_pct': round(actual_dist_loss_pct, 2),
            'target_loss_pct': myt_approved_dist_loss_pct,
            'variance_pp': round(variance_pp, 2),
            'ht_loss_mu': ht_loss_mu,
            'lt_loss_mu': lt_loss_mu,
        }
    }


# =============================================================================
# HEURISTIC 3: TD-LOSS-COMBINED-01 - Combined T&D Loss
# =============================================================================

def heuristic_TD_LOSS_COMBINED_01(
    total_energy_input_mu: float = 0.0,
    total_energy_sold_mu: float = 0.0,
    myt_approved_td_loss_pct: float = 0.0,
    transmission_loss_mu: float = 0.0,
    distribution_loss_mu: float = 0.0,
    actual_td_loss_pct: float = 0.0,  # If pre-computed
) -> Dict:
    """
    TD-LOSS-COMBINED-01: Combined T&D Loss Assessment

    Overall T&D loss = Transmission Loss + Distribution Loss
    Computed as: (Energy Available - Energy Sold) / Energy Available × 100

    Returns:
        Standardized heuristic result dict
    """

    total_loss_mu = transmission_loss_mu + distribution_loss_mu

    if total_energy_input_mu > 0:
        computed_td_loss_pct = ((total_energy_input_mu - total_energy_sold_mu)
                                / total_energy_input_mu * 100)
    else:
        computed_td_loss_pct = actual_td_loss_pct

    variance_pp = computed_td_loss_pct - myt_approved_td_loss_pct

    calc_steps = [
        "═══ COMBINED T&D LOSS ASSESSMENT ═══",
        "",
        f"Total Energy Input: {total_energy_input_mu:,.2f} MU",
        f"Total Energy Sold: {total_energy_sold_mu:,.2f} MU",
        f"Total Loss: {total_loss_mu:,.2f} MU",
        f"  (Transmission: {transmission_loss_mu:.2f} MU + Distribution: {distribution_loss_mu:.2f} MU)",
        "",
        f"Combined T&D Loss: {computed_td_loss_pct:.2f}%",
        f"MYT Approved Target: {myt_approved_td_loss_pct:.2f}%",
        f"Variance: {variance_pp:+.2f} percentage points",
    ]

    # Flag determination
    if variance_pp <= 0:
        flag = 'GREEN'
        recommendation = (
            f"Combined T&D loss {computed_td_loss_pct:.2f}% is at or below "
            f"approved target of {myt_approved_td_loss_pct:.2f}%. "
            f"KSEB Ltd may be eligible for loss reduction reward."
        )
    elif variance_pp <= 0.5:
        flag = 'YELLOW'
        recommendation = (
            f"Combined T&D loss {computed_td_loss_pct:.2f}% marginally exceeds "
            f"target {myt_approved_td_loss_pct:.2f}% by {variance_pp:.2f}pp."
        )
    else:
        flag = 'RED'
        recommendation = (
            f"Combined T&D loss {computed_td_loss_pct:.2f}% exceeds "
            f"target by {variance_pp:.2f}pp. Penalty provisions may apply."
        )

    calc_steps.extend(["", f"Flag: {flag}"])

    return {
        # Identification
        'heuristic_id': 'TD-LOSS-COMBINED-01',
        'heuristic_name': 'Combined T&D Loss Assessment',
        'line_item': 'T&D Losses (Combined)',

        # Calculation Results
        'claimed_value': round(computed_td_loss_pct, 2),
        'allowable_value': myt_approved_td_loss_pct,
        'variance_absolute': round(variance_pp, 2),
        'variance_percentage': None,

        # Tool's Assessment
        'flag': flag,
        'recommended_amount': None,
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation on T&D Loss targets, Tariff Regulations 2021',

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
        'depends_on': ['TRANS-LOSS-01', 'DIST-LOSS-01'],

        # Metadata
        'is_primary': True,  # Primary combined assessment
        'output_type': 'assessment',

        # Additional context
        'loss_details': {
            'total_energy_input_mu': total_energy_input_mu,
            'total_energy_sold_mu': total_energy_sold_mu,
            'transmission_loss_mu': transmission_loss_mu,
            'distribution_loss_mu': distribution_loss_mu,
            'total_loss_mu': round(total_loss_mu, 2),
            'computed_td_loss_pct': round(computed_td_loss_pct, 2),
            'target_td_loss_pct': myt_approved_td_loss_pct,
            'variance_pp': round(variance_pp, 2),
        }
    }


# =============================================================================
# HEURISTIC 4: TD-REWARD-01 - T&D Loss Reduction Reward/Penalty
# =============================================================================

def heuristic_TD_REWARD_01(
    approved_td_loss_pct: float = 0.0,
    actual_td_loss_pct: float = 0.0,
    total_energy_input_mu: float = 0.0,
    avg_power_purchase_cost_per_unit: float = 0.0,  # Rs/unit
    # Sharing ratio (as per Regulation 14(1): 2/3 utility, 1/3 consumer)
    utility_share_pct: float = 66.67,
    consumer_share_pct: float = 33.33,
    # Dynamic target support (CRITICAL — see docstring)
    prior_year_actual_td_loss_pct: Optional[float] = None,
    annual_loss_reduction_target_pp: float = 0.40,
    # Claims
    claimed_reward: float = 0.0,
) -> Dict:
    """
    TD-REWARD-01: T&D Loss Reduction Reward/Penalty

    SHARING RATIO — Regulation 14(1):
      Utility (KSEB) share = 2/3 of monetary gain (66.67%)
      Consumer share = 1/3 (33.33%)
      Default has been corrected from 50/50 to 66.67/33.33.

    DYNAMIC TARGET — Critical for correct application:
      The Commission does NOT use the static MYT approved loss% as the
      reward/penalty target at truing-up. Instead it uses a dynamic target:

        Dynamic Target = Prior Year Actual T&D Loss% - Annual Reduction Target (0.40%)

      Source: TU Order OP No. 49/2024, Para 4.34:
        FY 2022-23 actual = 9.30%
        Annual reduction target = 0.40%
        FY 2023-24 dynamic target = 9.30% - 0.40% = 8.90%

      In FY 2023-24, KSEB's actual (9.76%) EXCEEDED this dynamic target (8.90%),
      so KSEB was NOT eligible for gain sharing — even though it beat the static
      MYT target of 10.82%. The ₹131.59 Cr claim was therefore rejected on merit,
      NOT merely deferred due to revenue gap.

      HOW TO USE:
        Option A (recommended): Pass prior_year_actual_td_loss_pct.
          The function will compute the dynamic target automatically.
        Option B (fallback): Pass approved_td_loss_pct directly as the
          pre-computed dynamic target. Set prior_year_actual_td_loss_pct = None.

    If actual T&D loss < effective target:
      Gain = (Target% - Actual%) × Energy Input × Avg Power Purchase Cost
      KSEB share = Gain × 2/3
    If actual T&D loss > effective target:
      Loss = (Actual% - Target%) × Energy Input × Avg Power Purchase Cost
      This is a penalty / disallowance

    Returns:
        Standardized heuristic result dict
    """
    # Compute effective target: dynamic if prior year actual is provided
    if prior_year_actual_td_loss_pct is not None:
        effective_target_pct = prior_year_actual_td_loss_pct - annual_loss_reduction_target_pp
    else:
        effective_target_pct = approved_td_loss_pct

    loss_reduction_pp = effective_target_pct - actual_td_loss_pct

    # Build target source label for display
    if prior_year_actual_td_loss_pct is not None:
        target_label = (
            f"Dynamic Target: {prior_year_actual_td_loss_pct:.2f}% (prior yr actual) "
            f"- {annual_loss_reduction_target_pp:.2f}pp = {effective_target_pct:.2f}%"
        )
    else:
        target_label = f"Approved T&D Loss Target (static MYT): {effective_target_pct:.2f}%"

    calc_steps = [
        "═══ T&D LOSS REDUCTION REWARD/PENALTY ═══",
        "",
        target_label,
        f"Actual T&D Loss (KSERC-assessed): {actual_td_loss_pct:.2f}%",
        f"Loss Reduction vs Effective Target: {loss_reduction_pp:+.2f} percentage points",
        f"Energy Input: {total_energy_input_mu:,.2f} MU",
        f"Avg Power Purchase Cost: ₹{avg_power_purchase_cost_per_unit:.2f}/unit",
        f"Sharing Ratio: Utility {utility_share_pct:.2f}% : Consumer {consumer_share_pct:.2f}%",
        "",
    ]

    if loss_reduction_pp > 0:
        # Gain scenario - loss reduction achieved
        energy_saved_mu = (loss_reduction_pp / 100) * total_energy_input_mu
        monetary_gain_cr = (energy_saved_mu * avg_power_purchase_cost_per_unit) / 100  # MU × Rs/unit / 100 = Cr
        utility_share_cr = monetary_gain_cr * utility_share_pct / 100
        allowable_reward = utility_share_cr

        flag = 'GREEN'
        recommendation = (
            f"T&D loss reduction of {loss_reduction_pp:.2f}pp achieved "
            f"(Actual {actual_td_loss_pct:.2f}% vs Target {approved_td_loss_pct:.2f}%). "
            f"Energy saved: {energy_saved_mu:.2f} MU. "
            f"KSEB Ltd share of gains: ₹{utility_share_cr:.2f} Cr "
            f"({utility_share_pct:.0f}% sharing)."
        )

        calc_steps.extend([
            "✓ REWARD CALCULATION:",
            f"  Energy Saved: ({loss_reduction_pp:.2f}/100) × {total_energy_input_mu:,.2f} = {energy_saved_mu:,.2f} MU",
            f"  Total Savings: {energy_saved_mu:,.2f} × ₹{avg_power_purchase_cost_per_unit:.2f} / 100 = ₹{monetary_gain_cr:.2f} Cr",
            f"  Utility Share ({utility_share_pct:.0f}%): ₹{utility_share_cr:.2f} Cr",
            f"  Consumer Share ({consumer_share_pct:.0f}%): ₹{monetary_gain_cr - utility_share_cr:.2f} Cr",
        ])

    elif loss_reduction_pp == 0:
        energy_saved_mu = 0
        monetary_gain_cr = 0
        utility_share_cr = 0
        allowable_reward = 0

        flag = 'YELLOW'
        recommendation = f"T&D loss exactly at target. No reward or penalty."

        calc_steps.append("Result: T&D loss exactly at target. No reward or penalty.")

    else:
        # Penalty scenario - loss exceeds target
        excess_loss_pp = abs(loss_reduction_pp)
        energy_wasted_mu = (excess_loss_pp / 100) * total_energy_input_mu
        monetary_loss_cr = (energy_wasted_mu * avg_power_purchase_cost_per_unit) / 100
        utility_share_cr = 0
        allowable_reward = 0

        flag = 'RED'
        recommendation = (
            f"T&D loss EXCEEDS target by {excess_loss_pp:.2f}pp. "
            f"Excess energy loss: {energy_wasted_mu:.2f} MU. "
            f"Potential penalty exposure: ₹{monetary_loss_cr:.2f} Cr."
        )

        calc_steps.extend([
            "✗ PENALTY ZONE:",
            f"  Excess Loss: {excess_loss_pp:.2f}pp above target",
            f"  Energy Wasted: {energy_wasted_mu:,.2f} MU",
            f"  Monetary Impact: ₹{monetary_loss_cr:.2f} Cr",
        ])

    # Variance between claimed and allowable
    variance_abs = claimed_reward - allowable_reward if claimed_reward > 0 else 0
    variance_pct = (variance_abs / claimed_reward * 100) if claimed_reward > 0 else 0.0

    calc_steps.extend([
        "",
        f"Claimed Reward: ₹{claimed_reward:.2f} Cr",
        f"Allowable Reward: ₹{allowable_reward:.2f} Cr",
        f"Flag: {flag}",
    ])

    return {
        # Identification
        'heuristic_id': 'TD-REWARD-01',
        'heuristic_name': 'T&D Loss Reduction Reward/Penalty',
        'line_item': 'T&D Loss Reward',

        # Calculation Results
        'claimed_value': claimed_reward,
        'allowable_value': round(allowable_reward, 2),
        'variance_absolute': round(variance_abs, 2),
        'variance_percentage': round(variance_pct, 2) if variance_pct else None,

        # Tool's Assessment
        'flag': flag,
        'recommended_amount': round(allowable_reward, 2),
        'recommendation_text': recommendation,
        'regulatory_basis': 'T&D Loss reduction incentive provisions, Tariff Regulations 2021',

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
        'depends_on': ['TD-LOSS-COMBINED-01'],

        # Metadata
        'is_primary': True,
        'output_type': 'approved_amount',
        'note': 'Reward only if actual loss < target loss',

        # Additional context
        'reward_details': {
            'approved_td_loss_pct': approved_td_loss_pct,
            'actual_td_loss_pct': actual_td_loss_pct,
            'loss_reduction_pp': round(loss_reduction_pp, 2),
            'total_energy_input_mu': total_energy_input_mu,
            'avg_ppc_per_unit': avg_power_purchase_cost_per_unit,
            'utility_share_pct': utility_share_pct,
            'consumer_share_pct': consumer_share_pct,
        }
    }


# =============================================================================
# FY 2023-24 DEFAULT PARAMETERS
# =============================================================================

FY_2023_24_TRANS_LOSS_DEFAULTS = {
    'total_energy_input': 31406.32,
    'transmission_loss_mu': 819.23,
    'myt_approved_trans_loss_pct': 2.75,
    'peak_demand_mw': 5301,
}

FY_2023_24_TD_REWARD_DEFAULTS = {
    # MYT static target (for reference only — NOT used for reward/penalty)
    'approved_td_loss_pct': 10.82,
    # KSERC-assessed actual (TU Order OP 49/2024, Annexure 4.5)
    'actual_td_loss_pct': 9.76,
    # Dynamic target inputs (prior year actual 9.30% - 0.40% = 8.90% effective target)
    # KSEB actual 9.76% > 8.90% dynamic target → NOT eligible for reward
    'prior_year_actual_td_loss_pct': 9.30,
    'annual_loss_reduction_target_pp': 0.40,
    'total_energy_input_mu': 31406.32,
    'avg_power_purchase_cost_per_unit': 5.05,   # TU Order Para 4.30
    'utility_share_pct': 66.67,
    'consumer_share_pct': 33.33,
    'claimed_reward': 131.59,
}


# =============================================================================
# CONVENIENCE: Run all T&D loss heuristics
# =============================================================================

def run_all_td_loss_heuristics(
    trans_loss_params: Optional[Dict] = None,
    td_reward_params: Optional[Dict] = None,
) -> List[Dict]:
    """Run all T&D loss heuristics and return results."""

    results = []

    # 1. Transmission Loss
    tp = trans_loss_params or FY_2023_24_TRANS_LOSS_DEFAULTS
    results.append(heuristic_TRANS_LOSS_01(**tp))

    # 2. T&D Reward
    rp = td_reward_params or FY_2023_24_TD_REWARD_DEFAULTS
    results.append(heuristic_TD_REWARD_01(**rp))

    return results


if __name__ == "__main__":
    print("=" * 80)
    print("T&D LOSS HEURISTICS - FY 2023-24 Evaluation")
    print("=" * 80)

    results = run_all_td_loss_heuristics()
    for r in results:
        flag_emoji = {'GREEN': '🟢', 'YELLOW': '🟡', 'RED': '🔴'}[r['flag']]
        print(f"\n{flag_emoji} {r['heuristic_id']}: {r['heuristic_name']}")
        print(f"   Claimed: {r['claimed_value']} | Allowable: {r['allowable_value']}")
        print(f"   Flag: {r['flag']} | Primary: {r['is_primary']}")
        print(f"   Recommendation: {r['recommendation_text'][:100]}...")