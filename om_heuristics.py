"""
O&M Expenses Heuristics for SBU-G
Contains: OM-INFL-01, OM-NORM-01, OM-APPORT-01, EMP-PAYREV-01
"""

from datetime import datetime
from typing import Dict, List, Optional

def heuristic_OM_INFL_01(cpi_old: float, cpi_new: float, 
                          wpi_old: float, wpi_new: float) -> Dict:
    """
    OM-INFL-01: Inflation Calculation
    
    Calculates weighted average inflation using CPI (70%) and WPI (30%)
    This is a foundational heuristic - its output is used by OM-NORM-01
    
    Args:
        cpi_old: Consumer Price Index for previous year
        cpi_new: Consumer Price Index for current year
        wpi_old: Wholesale Price Index for previous year
        wpi_new: Wholesale Price Index for current year
    
    Returns:
        Heuristic result dictionary with calculated inflation
    """
    # Calculate individual increases
    cpi_increase = ((cpi_new - cpi_old) / cpi_old) * 100
    wpi_increase = ((wpi_new - wpi_old) / wpi_old) * 100
    
    # Weighted average: 70% CPI + 30% WPI
    weighted_inflation = (cpi_increase * 0.70) + (wpi_increase * 0.30)
    
    # Calculation steps for display
    calc_steps = [
        f"CPI Previous Year: {cpi_old}",
        f"CPI Current Year: {cpi_new}",
        f"CPI Increase: {cpi_increase:.2f}%",
        f"WPI Previous Year: {wpi_old}",
        f"WPI Current Year: {wpi_new}",
        f"WPI Increase: {wpi_increase:.2f}%",
        f"Formula: (CPI × 70%) + (WPI × 30%)",
        f"Calculation: ({cpi_increase:.2f}% × 0.70) + ({wpi_increase:.2f}% × 0.30)",
        f"Weighted Inflation: {weighted_inflation:.2f}%"
    ]
    
    return {
        # Identification
        'heuristic_id': 'OM-INFL-01',
        'heuristic_name': 'O&M Inflation Calculation',
        'line_item': 'O&M Expenses',
        
        # Calculation Results (this is a calculation-only heuristic)
        'claimed_value': None,  # Not applicable
        'allowable_value': weighted_inflation,  # The calculated inflation %
        'variance_absolute': None,
        'variance_percentage': None,
        
        # Tool's Assessment (always GREEN if calculation succeeds)
        'flag': 'GREEN',
        'recommended_amount': None,  # This doesn't determine final amount
        'recommendation_text': 'Inflation calculated per regulation',
        'regulatory_basis': 'Annexure-7, Para 1, Tariff Regulations 2021',
        
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
        'depends_on': [],  # Independent calculation
        
        # Metadata
        'is_primary': False,  # Supporting heuristic
        'output_type': 'calculated_value',  # Returns inflation % for use by others
        'output_value': weighted_inflation
    }


def heuristic_OM_NORM_01(base_year_om: float, 
                          inflation_2022_23: float,
                          inflation_2023_24: float,
                          inflation_2024_25: float,
                          claimed_existing: float,
                          new_stations_allowable: float = 0.0) -> Dict:
    """
    OM-NORM-01: Normative O&M Comparison for Existing Stations
    
    Primary heuristic that determines the approved O&M amount.
    Recalculates base year O&M with actual inflation rates.
    
    Args:
        base_year_om: Base year (2021-22) O&M = 156.16 Cr
        inflation_2022_23: Actual inflation for 2022-23 (7.06%)
        inflation_2023_24: Actual inflation for 2023-24 (3.41%)
        inflation_2024_25: Actual inflation for 2024-25 (from OM-INFL-01)
        claimed_existing: O&M claimed by KSEB for existing stations
        new_stations_allowable: Allowable O&M for new stations (calculated separately)
    
    Returns:
        Heuristic result with allowable O&M and variance analysis
    """
    # Step-by-step escalation from base year
    om_2022_23 = base_year_om * (1 + inflation_2022_23 / 100)
    om_2023_24 = om_2022_23 * (1 + inflation_2023_24 / 100)
    om_2024_25 = om_2023_24 * (1 + inflation_2024_25 / 100)
    
    # Total allowable = existing + new stations
    total_allowable = om_2024_25 + new_stations_allowable
    
    # Variance calculation
    variance_abs = claimed_existing - om_2024_25
    variance_pct = (variance_abs / om_2024_25) * 100 if om_2024_25 > 0 else 0
    
    # Flag determination
    if abs(variance_pct) <= 0.5:
        flag = 'GREEN'
        recommendation = 'Approve as claimed - within normative'
    elif abs(variance_pct) <= 10:
        flag = 'YELLOW'
        recommendation = 'Conditional approval - minor variance, justify excess'
    else:
        flag = 'RED'
        recommendation = 'Reject excess - allow only normative amount'
    
    # Calculation steps
    calc_steps = [
        f"Base Year O&M (2021-22): {base_year_om:.2f} Cr",
        f"Apply inflation 2022-23 ({inflation_2022_23:.2f}%): {om_2022_23:.2f} Cr",
        f"Apply inflation 2023-24 ({inflation_2023_24:.2f}%): {om_2023_24:.2f} Cr",
        f"Apply inflation 2024-25 ({inflation_2024_25:.2f}%): {om_2024_25:.2f} Cr",
        f"Add new stations allowable: {new_stations_allowable:.2f} Cr",
        f"Total Allowable O&M: {total_allowable:.2f} Cr",
        "",
        f"KSEB Claimed (Existing): {claimed_existing:.2f} Cr",
        f"Variance: {variance_abs:+.2f} Cr ({variance_pct:+.2f}%)",
        "",
        "Threshold: ±0% = GREEN, ±10% = YELLOW, >10% = RED"
    ]
    
    return {
        'heuristic_id': 'OM-NORM-01',
        'heuristic_name': 'Normative O&M Comparison (Existing Stations)',
        'line_item': 'O&M Expenses',
        
        'claimed_value': claimed_existing,
        'allowable_value': total_allowable,
        'variance_absolute': variance_abs,
        'variance_percentage': variance_pct,
        
        'flag': flag,
        'recommended_amount': total_allowable,  # This determines final O&M amount
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 45, Annexure-7 Table 3, Tariff Regulations 2021',
        
        'calculation_steps': calc_steps,
        
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        
        'depends_on': ['OM-INFL-01'],  # Needs inflation calculation first
        
        'is_primary': True,  # PRIMARY HEURISTIC - determines approved amount
        'output_type': 'approved_amount'
    }


def heuristic_OM_APPORT_01(total_om_approved: float,
                            actual_employee: float,
                            actual_ag: float,
                            actual_rm: float) -> Dict:
    """
    OM-APPORT-01: O&M Component Apportionment (Prudence Check)
    
    Supporting heuristic that checks if actual expenditure components
    are within normative limits. Does NOT affect final approved amount.
    
    Args:
        total_om_approved: Total O&M approved (from OM-NORM-01)
        actual_employee: Actual employee cost from audited accounts
        actual_ag: Actual A&G expenses from audited accounts
        actual_rm: Actual R&M expenses from audited accounts
    
    Returns:
        Heuristic result with prudence check flags for each component
    """
    # Fixed component ratios (MYT Order 2022, Table 4.23)
    RATIOS = {
        'Employee': 0.7703,
        'A&G': 0.0432,
        'R&M': 0.1865
    }
    
    # Calculate normative limits
    normative_employee = total_om_approved * RATIOS['Employee']
    normative_ag = total_om_approved * RATIOS['A&G']
    normative_rm = total_om_approved * RATIOS['R&M']
    
    # Component analysis
    components = []
    overall_flag = 'GREEN'
    
    for name, actual, normative, ratio in [
        ('Employee Cost', actual_employee, normative_employee, RATIOS['Employee']),
        ('A&G Expenses', actual_ag, normative_ag, RATIOS['A&G']),
        ('R&M Expenses', actual_rm, normative_rm, RATIOS['R&M'])
    ]:
        var_abs = actual - normative
        var_pct = (var_abs / normative) * 100 if normative > 0 else 0
        
        if abs(var_pct) <= 5:
            comp_flag = 'GREEN'
            comment = 'Within normative limits'
        elif abs(var_pct) <= 15:
            comp_flag = 'YELLOW'
            comment = 'Minor deviation - monitor'
            if overall_flag == 'GREEN':
                overall_flag = 'YELLOW'
        else:
            comp_flag = 'RED'
            comment = 'Exceeds normative - requires justification'
            overall_flag = 'RED'
        
        components.append({
            'component': name,
            'ratio': f"{ratio*100:.2f}%",
            'normative_limit': f"{normative:.2f} Cr",
            'actual_expenditure': f"{actual:.2f} Cr",
            'variance': f"{var_pct:+.2f}%",
            'flag': comp_flag,
            'comment': comment
        })
    
    # Total actual vs normative
    total_actual = actual_employee + actual_ag + actual_rm
    total_var = total_actual - total_om_approved
    total_var_pct = (total_var / total_om_approved) * 100 if total_om_approved > 0 else 0
    
    calc_steps = [
        "Component Apportionment (MYT Order 2022, Para 4.52):",
        "",
        f"Total O&M Approved: {total_om_approved:.2f} Cr",
        f"Total Actual Expenditure: {total_actual:.2f} Cr",
        f"Overall Variance: {total_var:+.2f} Cr ({total_var_pct:+.2f}%)",
        "",
        "Component Breakdown:",
    ]
    
    for comp in components:
        calc_steps.append(
            f"  {comp['component']}: {comp['normative_limit']} (norm) vs "
            f"{comp['actual_expenditure']} (actual) = {comp['variance']} [{comp['flag']}]"
        )
    
    recommendation = (
        'Prudence check only - does not affect approved amount. '
        'Staff should note deviations for future monitoring.'
    )
    
    return {
        'heuristic_id': 'OM-APPORT-01',
        'heuristic_name': 'O&M Component Apportionment (Prudence Check)',
        'line_item': 'O&M Expenses',
        
        'claimed_value': total_actual,
        'allowable_value': total_om_approved,
        'variance_absolute': total_var,
        'variance_percentage': total_var_pct,
        
        'flag': overall_flag,
        'recommended_amount': None,  # Supporting heuristic - no amount impact
        'recommendation_text': recommendation,
        'regulatory_basis': 'MYT Order 2022, Table 4.23 (Component Ratios)',
        
        'calculation_steps': calc_steps,
        'component_details': components,  # Additional detail for UI
        
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        
        'depends_on': ['OM-NORM-01'],  # Needs approved total first
        
        'is_primary': False,  # Supporting heuristic
        'output_type': 'prudence_check'
    }


def heuristic_EMP_PAYREV_01(employee_cost_normative: float,
                             employee_cost_actual: float,
                             pay_revision_implemented: bool = False,
                             pay_revision_details: Optional[Dict] = None) -> Dict:
    """
    EMP-PAYREV-01: Pay Revision Component Check
    
    Supporting heuristic that flags when employee costs significantly
    exceed normative limits. Does NOT affect final approved amount.
    
    Args:
        employee_cost_normative: Normative employee cost (77.03% of approved O&M)
        employee_cost_actual: Actual employee cost from audited accounts
        pay_revision_implemented: Whether pay revision was implemented
        pay_revision_details: Dict with keys: date, govt_order_ref, amount
    
    Returns:
        Heuristic result flagging pay revision impact
    """
    variance_abs = employee_cost_actual - employee_cost_normative
    variance_pct = (variance_abs / employee_cost_normative) * 100 if employee_cost_normative > 0 else 0
    
    # Flag determination
    if not pay_revision_implemented:
        if abs(variance_pct) <= 5:
            flag = 'GREEN'
            recommendation = 'Employee cost within acceptable limits'
        elif abs(variance_pct) <= 15:
            flag = 'YELLOW'
            recommendation = 'Moderate variance - verify no undisclosed pay revision'
        else:
            flag = 'RED'
            recommendation = 'Significant variance with no pay revision on record - requires investigation'
    else:
        if pay_revision_details and pay_revision_details.get('govt_order_ref'):
            flag = 'YELLOW'
            recommendation = f"Pay revision verified (Order: {pay_revision_details['govt_order_ref']}) - pending prudence check"
        else:
            flag = 'RED'
            recommendation = 'Pay revision claimed but government order reference missing'
    
    calc_steps = [
        f"Normative Employee Cost: {employee_cost_normative:.2f} Cr",
        f"Actual Employee Cost: {employee_cost_actual:.2f} Cr",
        f"Variance: {variance_abs:+.2f} Cr ({variance_pct:+.2f}%)",
        "",
        f"Pay Revision Implemented: {'Yes' if pay_revision_implemented else 'No'}"
    ]
    
    if pay_revision_implemented and pay_revision_details:
        calc_steps.extend([
            f"Pay Revision Date: {pay_revision_details.get('date', 'Not provided')}",
            f"Government Order: {pay_revision_details.get('govt_order_ref', 'Not provided')}",
            f"Pay Revision Amount: {pay_revision_details.get('amount', 'Not specified')} Cr"
        ])
    
    calc_steps.extend([
        "",
        "Note: This is a prudence check only.",
        "Does not affect the approved O&M amount.",
        "Staff should note for monitoring and future reviews."
    ])
    
    return {
        'heuristic_id': 'EMP-PAYREV-01',
        'heuristic_name': 'Pay Revision Component Check',
        'line_item': 'O&M Expenses',
        
        'claimed_value': employee_cost_actual,
        'allowable_value': employee_cost_normative,
        'variance_absolute': variance_abs,
        'variance_percentage': variance_pct,
        
        'flag': flag,
        'recommended_amount': None,  # Supporting heuristic
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 14(3), Tariff Regulations 2021; APTEL Order 10.11.2014',
        
        'calculation_steps': calc_steps,
        
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        
        'depends_on': ['OM-APPORT-01'],  # Needs employee component breakdown
        
        'is_primary': False,
        'output_type': 'prudence_check'
    }