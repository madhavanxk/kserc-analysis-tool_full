"""
Depreciation Heuristics for SBU-G
Contains: DEP-GEN-01
"""

from typing import Dict, Optional

def heuristic_DEP_GEN_01(
    # Opening balances (from previous year truing-up)
    gfa_opening_total: float,
    gfa_13_to_30_years: float,
    land_13_to_30_years: float,
    grants_13_to_30_years: float,
    gfa_below_13_years: float,
    land_below_13_years: float,
    grants_below_13_years: float,
    
    # Changes during the year
    asset_additions: float,
    
    # KSEB's claim
    claimed_depreciation: float,
    
    # Optional parameters (with defaults)
    asset_withdrawals: float = 0.0
) -> Dict:
    """
    DEP-GEN-01: Depreciation Calculation for Generation Assets
    
    Calculates depreciation using two age-based buckets:
    1. Assets 13-30 years: 1.42% on closing balance
    2. Assets <13 years: 5.14% on average balance
    
    Args:
        gfa_opening_total: Total GFA as on 31.03 previous year
        gfa_13_to_30_years: GFA for assets aged 13-30 years
        land_13_to_30_years: Land value in 13-30 years bucket
        grants_13_to_30_years: Grants & contributions in 13-30 years bucket
        gfa_below_13_years: GFA for assets aged <13 years
        land_below_13_years: Land value in <13 years bucket
        grants_below_13_years: Grants & contributions in <13 years bucket
        asset_additions: New assets capitalized during the year
        asset_withdrawals: Assets withdrawn (natural calamities, etc.)
        claimed_depreciation: Total depreciation claimed by KSEB
    
    Returns:
        Heuristic result dictionary with calculated depreciation
    """
    
    # BUCKET 1: Assets 13-30 years (Depreciation @ 1.42%)
    # Calculate depreciable assets (excluding land and grants)
    depreciable_13_to_30 = gfa_13_to_30_years - land_13_to_30_years - grants_13_to_30_years
    depreciation_13_to_30 = depreciable_13_to_30 * 0.0142  # 1.42%
    
    # BUCKET 2: Assets <13 years (Depreciation @ 5.14% on average)
    # Opening depreciable assets
    opening_below_13 = gfa_below_13_years - land_below_13_years - grants_below_13_years
    
    # Closing depreciable assets (opening + additions - withdrawals)
    closing_below_13 = opening_below_13 + asset_additions - asset_withdrawals
    
    # Average of opening and closing
    average_below_13 = (opening_below_13 + closing_below_13) / 2
    
    # Depreciation @ 5.14%
    depreciation_below_13 = average_below_13 * 0.0514  # 5.14%
    
    # TOTAL ALLOWABLE DEPRECIATION
    total_allowable = depreciation_13_to_30 + depreciation_below_13
    
    # Variance analysis
    variance_abs = claimed_depreciation - total_allowable
    variance_pct = (variance_abs / total_allowable) * 100 if total_allowable > 0 else 0
    
    # Flag determination
    if abs(variance_pct) <= 2:
        flag = 'GREEN'
        recommendation = 'Approve as calculated - within tolerance'
    elif abs(variance_pct) <= 5:
        flag = 'YELLOW'
        recommendation = 'Minor variance - verify calculation methodology'
    else:
        flag = 'RED'
        recommendation = 'Significant variance - requires detailed scrutiny'
    
    # Calculation steps for display
    calc_steps = [
        "DEPRECIATION CALCULATION (Regulation 48, Tariff Regulations 2021)",
        "",
        "═══ BUCKET 1: Assets 13-30 Years ═══",
        f"Total GFA (13-30 years): ₹{gfa_13_to_30_years:.2f} Cr",
        f"Less: Land value: ₹{land_13_to_30_years:.2f} Cr",
        f"Less: Grants & contributions: ₹{grants_13_to_30_years:.2f} Cr",
        f"Depreciable Assets (13-30 years): ₹{depreciable_13_to_30:.2f} Cr",
        f"Depreciation Rate: 1.42%",
        f"Depreciation (13-30 years): ₹{depreciation_13_to_30:.2f} Cr",
        "",
        "═══ BUCKET 2: Assets <13 Years ═══",
        f"Opening GFA (<13 years): ₹{gfa_below_13_years:.2f} Cr",
        f"Less: Land value: ₹{land_below_13_years:.2f} Cr",
        f"Less: Grants & contributions: ₹{grants_below_13_years:.2f} Cr",
        f"Opening Depreciable Assets: ₹{opening_below_13:.2f} Cr",
        "",
        f"Add: Asset additions (FY): ₹{asset_additions:.2f} Cr",
        f"Less: Asset withdrawals: ₹{asset_withdrawals:.2f} Cr",
        f"Closing Depreciable Assets: ₹{closing_below_13:.2f} Cr",
        "",
        f"Average = (Opening + Closing) / 2",
        f"Average Depreciable Assets: ₹{average_below_13:.2f} Cr",
        f"Depreciation Rate: 5.14%",
        f"Depreciation (<13 years): ₹{depreciation_below_13:.2f} Cr",
        "",
        "═══ TOTAL DEPRECIATION ═══",
        f"Bucket 1 (13-30 years): ₹{depreciation_13_to_30:.2f} Cr",
        f"Bucket 2 (<13 years): ₹{depreciation_below_13:.2f} Cr",
        f"Total Allowable Depreciation: ₹{total_allowable:.2f} Cr",
        "",
        f"KSEB Claimed: ₹{claimed_depreciation:.2f} Cr",
        f"Variance: {variance_abs:+.2f} Cr ({variance_pct:+.2f}%)",
        "",
        "Threshold: ±2% = GREEN, ±5% = YELLOW, >5% = RED"
    ]
    
    return {
        # Identification
        'heuristic_id': 'DEP-GEN-01',
        'heuristic_name': 'Depreciation Calculation',
        'line_item': 'Depreciation',
        
        # Calculation Results
        'claimed_value': claimed_depreciation,
        'allowable_value': total_allowable,
        'variance_absolute': variance_abs,
        'variance_percentage': variance_pct,
        
        # Tool's Assessment
        'flag': flag,
        'recommended_amount': total_allowable,
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 48, Tariff Regulations 2021',
        
        # Calculation Details
        'calculation_steps': calc_steps,
        
        # Detailed breakdown for reference
        'depreciation_breakdown': {
            'bucket_13_to_30': {
                'gfa': gfa_13_to_30_years,
                'land': land_13_to_30_years,
                'grants': grants_13_to_30_years,
                'depreciable': depreciable_13_to_30,
                'rate': 0.0142,
                'depreciation': depreciation_13_to_30
            },
            'bucket_below_13': {
                'gfa_opening': gfa_below_13_years,
                'land': land_below_13_years,
                'grants': grants_below_13_years,
                'depreciable_opening': opening_below_13,
                'additions': asset_additions,
                'withdrawals': asset_withdrawals,
                'depreciable_closing': closing_below_13,
                'depreciable_average': average_below_13,
                'rate': 0.0514,
                'depreciation': depreciation_below_13
            },
            'total': total_allowable
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
        'is_primary': True,  # PRIMARY HEURISTIC - determines approved depreciation
        'output_type': 'approved_amount'
    }