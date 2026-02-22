"""
Non-Tariff Income (NTI) Heuristics for SBU-G
Contains: NTI-01
"""

from typing import Dict, Optional

def heuristic_NTI_01(
    # MYT baseline (from MYT 2022 order)
    myt_baseline_nti: float,
    
    # Income from accounts
    base_income_from_accounts: float,
    
    # Exclusions (to be removed from NTI)
    exclusion_grant_clawback: float = 0.0,
    exclusion_led_bulbs: float = 0.0,
    exclusion_nilaavu_scheme: float = 0.0,
    exclusion_provision_reversals: float = 0.0,
    exclusion_kwa_unrealized: float = 0.0,
    
    # Additions (to be added to NTI)
    addition_kwa_arrears_released: float = 0.0,
    
    # Other exclusions/additions
    other_exclusions: float = 0.0,
    other_additions: float = 0.0,
    
    # KSEB's claimed NTI
    claimed_nti: float = 0.0
) -> Dict:
    """
    NTI-01: Non-Tariff Income Validation
    
    Validates NTI calculation by verifying:
    1. Base income from audited accounts
    2. Regulatory exclusions (grant claw-back, provisions, etc.)
    3. Regulatory additions (KWA arrears, etc.)
    
    Unlike cost items, higher NTI is favorable (reduces tariff burden).
    
    Args:
        myt_baseline_nti: NTI approved in MYT 2022 for this year
        base_income_from_accounts: Total other income from audited accounts
        exclusion_grant_clawback: Grant claw-back (depreciation-related)
        exclusion_led_bulbs: LED bulb costs (booked under A&G)
        exclusion_nilaavu_scheme: Nilaavu scheme income (disputed)
        exclusion_provision_reversals: Reversal of doubtful debt provisions
        exclusion_kwa_unrealized: Unrealized KWA interest
        addition_kwa_arrears_released: KWA arrears released by Govt
        other_exclusions: Any other exclusions
        other_additions: Any other additions
        claimed_nti: Total NTI claimed by KSEB
    
    Returns:
        Heuristic result dictionary with NTI validation
    """
    
    # Calculate total exclusions
    total_exclusions = (
        exclusion_grant_clawback +
        exclusion_led_bulbs +
        exclusion_nilaavu_scheme +
        exclusion_provision_reversals +
        exclusion_kwa_unrealized +
        other_exclusions
    )
    
    # Calculate total additions
    total_additions = (
        addition_kwa_arrears_released +
        other_additions
    )
    
    # Calculate allowable NTI
    allowable_nti = base_income_from_accounts - total_exclusions + total_additions
    
    # Variance analysis (claimed vs calculated)
    variance_vs_calculated = claimed_nti - allowable_nti
    variance_vs_calculated_pct = (variance_vs_calculated / allowable_nti) * 100 if allowable_nti > 0 else 0
    
    # Variance vs MYT baseline
    variance_vs_myt = allowable_nti - myt_baseline_nti
    variance_vs_myt_pct = (variance_vs_myt / myt_baseline_nti) * 100 if myt_baseline_nti > 0 else 0
    
    # Flag determination (revenue-favorable logic)
    # For NTI, higher is better (reduces tariff burden)
    if abs(variance_vs_calculated_pct) <= 2:
        flag = 'GREEN'
        recommendation = 'Approve as calculated - matches KSEB calculation'
    elif abs(variance_vs_calculated_pct) <= 5:
        flag = 'YELLOW'
        recommendation = 'Minor variance in calculation - verify components'
    else:
        flag = 'RED'
        recommendation = 'Significant calculation variance - scrutinize adjustments'
    
    # Additional note if significantly higher than MYT
    myt_note = ""
    if variance_vs_myt_pct > 50:
        myt_note = f"Note: NTI is {variance_vs_myt_pct:.1f}% higher than MYT baseline. Verify actual income from audited accounts."
    elif variance_vs_myt_pct < -20:
        myt_note = f"Note: NTI is {abs(variance_vs_myt_pct):.1f}% lower than MYT baseline. Verify for revenue shortfall."
    
    # Calculation steps for display
    calc_steps = [
        "NON-TARIFF INCOME CALCULATION (Regulation 52, Tariff Regulations 2021)",
        "",
        "═══ INCOME FROM ACCOUNTS ═══",
        f"Base Income (from audited accounts): ₹{base_income_from_accounts:.2f} Cr",
        "",
        "═══ REGULATORY EXCLUSIONS ═══"
    ]
    
    # Add exclusion details
    if exclusion_grant_clawback > 0:
        calc_steps.append(f"Less: Grant claw-back (depreciation-related): ₹{exclusion_grant_clawback:.2f} Cr")
    if exclusion_led_bulbs > 0:
        calc_steps.append(f"Less: LED bulb costs (A&G expense): ₹{exclusion_led_bulbs:.2f} Cr")
    if exclusion_nilaavu_scheme > 0:
        calc_steps.append(f"Less: Nilaavu scheme income: ₹{exclusion_nilaavu_scheme:.2f} Cr")
    if exclusion_provision_reversals > 0:
        calc_steps.append(f"Less: Provision reversals (unrealized): ₹{exclusion_provision_reversals:.2f} Cr")
    if exclusion_kwa_unrealized > 0:
        calc_steps.append(f"Less: KWA unrealized interest: ₹{exclusion_kwa_unrealized:.2f} Cr")
    if other_exclusions > 0:
        calc_steps.append(f"Less: Other exclusions: ₹{other_exclusions:.2f} Cr")
    
    calc_steps.append(f"Total Exclusions: ₹{total_exclusions:.2f} Cr")
    calc_steps.append("")
    
    # Add addition details
    if total_additions > 0:
        calc_steps.append("═══ REGULATORY ADDITIONS ═══")
        if addition_kwa_arrears_released > 0:
            calc_steps.append(f"Add: KWA arrears released by Govt: ₹{addition_kwa_arrears_released:.2f} Cr")
        if other_additions > 0:
            calc_steps.append(f"Add: Other additions: ₹{other_additions:.2f} Cr")
        calc_steps.append(f"Total Additions: ₹{total_additions:.2f} Cr")
        calc_steps.append("")
    
    calc_steps.extend([
        "═══ ALLOWABLE NTI ═══",
        f"Base Income: ₹{base_income_from_accounts:.2f} Cr",
        f"Less: Total Exclusions: ₹{total_exclusions:.2f} Cr",
        f"Add: Total Additions: ₹{total_additions:.2f} Cr",
        f"Allowable NTI: ₹{allowable_nti:.2f} Cr",
        "",
        "═══ COMPARISON ═══",
        f"MYT Baseline (2023-24): ₹{myt_baseline_nti:.2f} Cr",
        f"KSERC Calculated: ₹{allowable_nti:.2f} Cr",
        f"KSEB Claimed: ₹{claimed_nti:.2f} Cr",
        f"Variance (Claimed vs Calculated): {variance_vs_calculated:+.2f} Cr ({variance_vs_calculated_pct:+.2f}%)",
        f"Variance vs MYT: {variance_vs_myt:+.2f} Cr ({variance_vs_myt_pct:+.2f}%)",
        ""
    ])
    
    if myt_note:
        calc_steps.append(myt_note)
    
    calc_steps.append("")
    calc_steps.append("Note: Higher NTI reduces tariff burden on consumers.")
    
    # Create breakdown dictionary for detailed view
    exclusions_breakdown = {
        'grant_clawback': exclusion_grant_clawback,
        'led_bulbs': exclusion_led_bulbs,
        'nilaavu_scheme': exclusion_nilaavu_scheme,
        'provision_reversals': exclusion_provision_reversals,
        'kwa_unrealized': exclusion_kwa_unrealized,
        'other': other_exclusions,
        'total': total_exclusions
    }
    
    additions_breakdown = {
        'kwa_arrears_released': addition_kwa_arrears_released,
        'other': other_additions,
        'total': total_additions
    }
    
    return {
        # Identification
        'heuristic_id': 'NTI-01',
        'heuristic_name': 'Non-Tariff Income Validation',
        'line_item': 'Non-Tariff Income',
        
        # Calculation Results
        'claimed_value': claimed_nti,
        'allowable_value': allowable_nti,
        'variance_absolute': variance_vs_calculated,
        'variance_percentage': variance_vs_calculated_pct,
        
        # Tool's Assessment
        'flag': flag,
        'recommended_amount': allowable_nti,
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 52, Tariff Regulations 2021',
        
        # Calculation Details
        'calculation_steps': calc_steps,
        
        # Detailed breakdowns
        'nti_breakdown': {
            'base_income': base_income_from_accounts,
            'exclusions': exclusions_breakdown,
            'additions': additions_breakdown,
            'allowable_nti': allowable_nti,
            'myt_baseline': myt_baseline_nti,
            'variance_vs_myt': variance_vs_myt,
            'variance_vs_myt_pct': variance_vs_myt_pct
        },
        
        # Staff Review Section
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        
        # Dependencies
        'depends_on': [],  # Independent calculation
        
        # Metadata
        'is_primary': True,  # PRIMARY HEURISTIC - determines approved NTI
        'output_type': 'approved_amount',
        'note': 'NTI is revenue - higher values reduce consumer tariff burden'
    }