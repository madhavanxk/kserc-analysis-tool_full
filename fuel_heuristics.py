"""
Fuel Costs Heuristics for SBU-G
Contains: FUEL-01
"""

from typing import Dict, List, Optional

def heuristic_FUEL_01(
    # Fuel type totals
    heavy_fuel_oil: float = 0.0,
    hsd_oil: float = 0.0,
    lube_oil: float = 0.0,
    lubricants_consumables: float = 0.0,
    
    # Total claimed
    total_claimed_fuel_cost: float = 0.0,
    
    # Optional: Previous year for trend check
    previous_year_fuel_cost: float = 0.0,
    
    # Optional: Station-wise breakdown (for display)
    station_breakdown: Optional[List[Dict]] = None
) -> Dict:
    """
    FUEL-01: Fuel Costs Validation
    
    Validates fuel and lubricant costs for generation stations.
    This is a pass-through item - no MYT baseline exists.
    
    Validation checks:
    1. Components add up to claimed total
    2. Not abnormally high vs previous year (if available)
    3. Matches audited accounts
    
    Args:
        heavy_fuel_oil: Total heavy fuel oil cost (KDPP, BDPP)
        hsd_oil: Total HSD oil cost
        lube_oil: Total lube oil cost (hydel stations)
        lubricants_consumables: Total lubricants & consumables
        total_claimed_fuel_cost: Total fuel cost claimed by KSEB
        previous_year_fuel_cost: Previous year fuel cost (for trend check)
        station_breakdown: List of dicts with station-wise details (optional)
    
    Returns:
        Heuristic result dictionary with fuel cost validation
    """
    
    # Calculate total from components
    calculated_total = (
        heavy_fuel_oil +
        hsd_oil +
        lube_oil +
        lubricants_consumables
    )
    
    # Variance between claimed and calculated
    variance_abs = total_claimed_fuel_cost - calculated_total
    variance_pct = (variance_abs / calculated_total) * 100 if calculated_total > 0 else 0
    
    # Trend check (if previous year data available)
    yoy_change = 0.0
    yoy_change_pct = 0.0
    trend_note = ""
    
    if previous_year_fuel_cost > 0:
        yoy_change = total_claimed_fuel_cost - previous_year_fuel_cost
        yoy_change_pct = (yoy_change / previous_year_fuel_cost) * 100
        
        if yoy_change_pct > 100:
            trend_note = f"Note: Fuel cost increased by {yoy_change_pct:.1f}% vs previous year. Verify operational reasons."
        elif yoy_change_pct < -50:
            trend_note = f"Note: Fuel cost decreased by {abs(yoy_change_pct):.1f}% vs previous year. Verify reduced generation."
    
    # Flag determination
    if abs(variance_pct) <= 1:
        flag = 'GREEN'
        recommendation = 'Approve as per audited accounts'
    elif abs(variance_pct) <= 5:
        flag = 'YELLOW'
        recommendation = 'Minor calculation variance - verify component breakdown'
    else:
        flag = 'RED'
        recommendation = 'Calculation error - components do not add up to claimed total'
    
    # Additional check: abnormal increase
    if flag == 'GREEN' and yoy_change_pct > 100:
        flag = 'YELLOW'
        recommendation = 'Approve but note significant increase vs previous year'
    
    # Calculation steps
    calc_steps = [
        "FUEL COSTS VALIDATION (Operational Consumables)",
        "",
        "Note: Fuel costs are pass-through items based on actual consumption.",
        "No MYT baseline exists - costs depend on generation & maintenance needs.",
        "",
        "═══ FUEL TYPE BREAKDOWN ═══"
    ]
    
    if heavy_fuel_oil > 0:
        calc_steps.append(f"Heavy Fuel Oil (Diesel Stations): ₹{heavy_fuel_oil:.2f} Cr")
    if hsd_oil > 0:
        calc_steps.append(f"HSD Oil: ₹{hsd_oil:.2f} Cr")
    if lube_oil > 0:
        calc_steps.append(f"Lube Oil (Hydel Stations): ₹{lube_oil:.2f} Cr")
    if lubricants_consumables > 0:
        calc_steps.append(f"Lubricants & Consumables: ₹{lubricants_consumables:.2f} Cr")
    
    calc_steps.extend([
        "",
        f"Total Calculated: ₹{calculated_total:.2f} Cr",
        f"KSEB Claimed: ₹{total_claimed_fuel_cost:.2f} Cr",
        f"Variance: {variance_abs:+.4f} Cr ({variance_pct:+.2f}%)",
        ""
    ])
    
    # Add year-over-year comparison if available
    if previous_year_fuel_cost > 0:
        calc_steps.extend([
            "═══ YEAR-OVER-YEAR TREND ═══",
            f"Previous Year (2022-23): ₹{previous_year_fuel_cost:.2f} Cr",
            f"Current Year (2023-24): ₹{total_claimed_fuel_cost:.2f} Cr",
            f"Change: {yoy_change:+.2f} Cr ({yoy_change_pct:+.1f}%)",
            ""
        ])
        
        if trend_note:
            calc_steps.append(trend_note)
            calc_steps.append("")
    
    # Add station-wise breakdown if provided
    if station_breakdown:
        calc_steps.append("═══ STATION-WISE BREAKDOWN ═══")
        for station in station_breakdown:
            station_name = station.get('name', 'Unknown')
            station_total = station.get('total', 0.0)
            calc_steps.append(f"{station_name}: ₹{station_total:.2f} Cr")
            
            # Show fuel types for this station if available
            if station.get('heavy_fuel_oil', 0) > 0:
                calc_steps.append(f"  - Heavy Fuel Oil: ₹{station['heavy_fuel_oil']:.2f} Cr")
            if station.get('hsd_oil', 0) > 0:
                calc_steps.append(f"  - HSD Oil: ₹{station['hsd_oil']:.2f} Cr")
            if station.get('lube_oil', 0) > 0:
                calc_steps.append(f"  - Lube Oil: ₹{station['lube_oil']:.2f} Cr")
            if station.get('lubricants', 0) > 0:
                calc_steps.append(f"  - Lubricants: ₹{station['lubricants']:.2f} Cr")
        calc_steps.append("")
    
    calc_steps.extend([
        "Regulatory Basis:",
        "- Essential operational consumables for plant maintenance",
        "- Hydraulic oil for governor control systems",
        "- Lube oils for equipment reliability and lifespan",
        "- Approved as per audited accounts (Regulation 51)"
    ])
    
    # Fuel breakdown for reference
    fuel_breakdown = {
        'heavy_fuel_oil': heavy_fuel_oil,
        'hsd_oil': hsd_oil,
        'lube_oil': lube_oil,
        'lubricants_consumables': lubricants_consumables,
        'calculated_total': calculated_total,
        'previous_year': previous_year_fuel_cost,
        'yoy_change': yoy_change,
        'yoy_change_pct': yoy_change_pct
    }
    
    return {
        # Identification
        'heuristic_id': 'FUEL-01',
        'heuristic_name': 'Fuel Costs Validation',
        'line_item': 'Fuel Costs',
        
        # Calculation Results
        'claimed_value': total_claimed_fuel_cost,
        'allowable_value': calculated_total,
        'variance_absolute': variance_abs,
        'variance_percentage': variance_pct,
        
        # Tool's Assessment
        'flag': flag,
        'recommended_amount': calculated_total,
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 51, Tariff Regulations 2021 (Operational Consumables)',
        
        # Calculation Details
        'calculation_steps': calc_steps,
        
        # Detailed breakdown
        'fuel_breakdown': fuel_breakdown,
        'station_breakdown': station_breakdown if station_breakdown else [],
        
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
        'is_primary': True,  # PRIMARY HEURISTIC - determines approved fuel cost
        'output_type': 'approved_amount',
        'note': 'Pass-through item - no MYT baseline, approved as actual from audited accounts'
    }