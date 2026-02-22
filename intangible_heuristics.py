"""
Intangible Assets Amortization Heuristics for SBU-G
Contains: INTANG-01
"""

from typing import Dict, Optional

def heuristic_INTANG_01(
    # Software development costs (employee-related)
    software_employee_costs_capitalized: float = 0.0,
    software_amortization_claimed: float = 0.0,
    software_supporting_docs_provided: bool = False,
    software_employees_additional_to_norms: bool = False,
    
    # Other intangible assets
    purchased_software_licenses: float = 0.0,
    patents_ip: float = 0.0,
    other_intangibles: float = 0.0,
    other_intangibles_amortization: float = 0.0,
    other_supporting_docs_provided: bool = False,
    
    # Total claimed
    total_claimed_amortization: float = 0.0,
    
    # Optional: Previous year amortization
    previous_year_amortization: float = 0.0
) -> Dict:
    """
    INTANG-01: Intangible Assets Amortization Validation
    
    Validates amortization claims for:
    1. In-house software development (employee costs)
    2. Purchased software licenses
    3. Patents, IP, and other intangibles
    
    Key Issue: Software development employee costs may already be 
    included in normative O&M expenses (double-counting risk).
    
    Args:
        software_employee_costs_capitalized: Employee costs for software development
        software_amortization_claimed: Amortization on software development
        software_supporting_docs_provided: Are supporting documents provided?
        software_employees_additional_to_norms: Are employees additional to O&M norms?
        purchased_software_licenses: Cost of purchased software
        patents_ip: Cost of patents/IP
        other_intangibles: Other intangible assets
        other_intangibles_amortization: Amortization on other intangibles
        other_supporting_docs_provided: Supporting docs for other intangibles
        total_claimed_amortization: Total amortization claimed
        previous_year_amortization: Previous year amortization (for trend)
    
    Returns:
        Heuristic result dictionary with validation
    """
    
    # Calculate components
    total_software_amort = software_amortization_claimed
    total_other_amort = other_intangibles_amortization
    calculated_total = total_software_amort + total_other_amort
    
    # Variance check
    variance_abs = total_claimed_amortization - calculated_total
    variance_pct = (variance_abs / calculated_total) * 100 if calculated_total > 0 else 0
    
    # Software development validation
    software_flag = 'GREEN'
    software_recommendation = ''
    software_allowable = 0.0
    
    if software_amortization_claimed > 0:
        if not software_supporting_docs_provided:
            software_flag = 'RED'
            software_recommendation = 'REJECT: No supporting documents (employee list, development timeline, cost breakdown)'
            software_allowable = 0.0
        elif not software_employees_additional_to_norms:
            software_flag = 'RED'
            software_recommendation = 'REJECT: Employee costs likely already in O&M norms (double-counting risk)'
            software_allowable = 0.0
        else:
            software_flag = 'YELLOW'
            software_recommendation = 'REVIEW: Documents provided - verify employees are additional to O&M norms'
            software_allowable = software_amortization_claimed  # Pending staff review
    
    # Other intangibles validation
    other_flag = 'GREEN'
    other_recommendation = ''
    other_allowable = 0.0
    
    if other_intangibles_amortization > 0:
        if not other_supporting_docs_provided:
            other_flag = 'YELLOW'
            other_recommendation = 'REVIEW: Verify purchase invoices and asset capitalization'
            other_allowable = other_intangibles_amortization  # Pending verification
        else:
            other_flag = 'GREEN'
            other_recommendation = 'APPROVE: Legitimate purchased assets with documentation'
            other_allowable = other_intangibles_amortization
    
    # Overall allowable
    allowable_total = software_allowable + other_allowable
    
    # Overall flag (strictest wins)
    if software_flag == 'RED' or other_flag == 'RED':
        overall_flag = 'RED'
    elif software_flag == 'YELLOW' or other_flag == 'YELLOW':
        overall_flag = 'YELLOW'
    else:
        overall_flag = 'GREEN'
    
    # Overall recommendation
    if overall_flag == 'RED':
        overall_recommendation = 'Reject or reduce - see component details'
    elif overall_flag == 'YELLOW':
        overall_recommendation = 'Requires staff review of supporting documentation'
    else:
        overall_recommendation = 'Approve as claimed'
    
    # Calculation steps
    calc_steps = [
        "INTANGIBLE ASSETS AMORTIZATION (Regulation 49, Tariff Regulations 2021)",
        "",
        "CRITICAL ISSUE: Software development employee costs may already be",
        "included in normative O&M expenses approved by Commission.",
        "Double-counting must be avoided.",
        "",
        "═══ SOFTWARE DEVELOPMENT (In-house) ═══"
    ]
    
    if software_amortization_claimed > 0:
        calc_steps.extend([
            f"Employee Costs Capitalized: ₹{software_employee_costs_capitalized:.2f} Cr",
            f"Amortization Claimed: ₹{software_amortization_claimed:.2f} Cr",
            f"Supporting Documents Provided: {'Yes' if software_supporting_docs_provided else 'No'}",
            f"Employees Additional to O&M Norms: {'Yes' if software_employees_additional_to_norms else 'No'}",
            "",
            f"Assessment: {software_flag}",
            f"Recommendation: {software_recommendation}",
            f"Allowable: ₹{software_allowable:.2f} Cr",
            ""
        ])
    else:
        calc_steps.append("No software development amortization claimed")
        calc_steps.append("")
    
    calc_steps.append("═══ OTHER INTANGIBLE ASSETS ═══")
    
    if other_intangibles_amortization > 0:
        if purchased_software_licenses > 0:
            calc_steps.append(f"Purchased Software Licenses: ₹{purchased_software_licenses:.2f} Cr")
        if patents_ip > 0:
            calc_steps.append(f"Patents/IP: ₹{patents_ip:.2f} Cr")
        if other_intangibles > 0:
            calc_steps.append(f"Other Intangibles: ₹{other_intangibles:.2f} Cr")
        
        calc_steps.extend([
            f"Total Other Amortization: ₹{other_intangibles_amortization:.2f} Cr",
            f"Supporting Documents Provided: {'Yes' if other_supporting_docs_provided else 'No'}",
            "",
            f"Assessment: {other_flag}",
            f"Recommendation: {other_recommendation}",
            f"Allowable: ₹{other_allowable:.2f} Cr",
            ""
        ])
    else:
        calc_steps.append("No other intangible assets claimed")
        calc_steps.append("")
    
    calc_steps.extend([
        "═══ TOTAL AMORTIZATION ═══",
        f"Software Development: ₹{software_allowable:.2f} Cr",
        f"Other Intangibles: ₹{other_allowable:.2f} Cr",
        f"Total Allowable: ₹{allowable_total:.2f} Cr",
        "",
        f"KSEB Claimed: ₹{total_claimed_amortization:.2f} Cr",
        f"Variance: {total_claimed_amortization - allowable_total:+.2f} Cr",
        ""
    ])
    
    # Add regulatory precedent note
    calc_steps.extend([
        "═══ REGULATORY PRECEDENT (FY 2023-24) ═══",
        "Commission rejected software amortization claim because:",
        "1. Employee costs already included in normative O&M",
        "2. Insufficient evidence that employees were additional to norms",
        "3. Risk of double-counting expenses",
        "",
        "KSEBL must provide:",
        "- List of employees engaged in software development",
        "- Proof that these employees are NOT in approved O&M headcount",
        "- Development timeline and cost breakdown",
        "- Methodology for capitalization and amortization",
        "",
        "Evidence Requirements:",
        "- Employee deployment records",
        "- Comparison with approved O&M headcount (30,321 as of 2022)",
        "- Project-wise cost allocation",
        "- Auditor's certificate on capitalization methodology"
    ])
    
    # Year-over-year if available
    if previous_year_amortization > 0:
        yoy_change = total_claimed_amortization - previous_year_amortization
        yoy_pct = (yoy_change / previous_year_amortization) * 100
        calc_steps.extend([
            "",
            "═══ YEAR-OVER-YEAR ═══",
            f"Previous Year: ₹{previous_year_amortization:.2f} Cr",
            f"Current Year: ₹{total_claimed_amortization:.2f} Cr",
            f"Change: {yoy_change:+.2f} Cr ({yoy_pct:+.1f}%)"
        ])
    
    # Breakdown for reference
    amortization_breakdown = {
        'software_development': {
            'employee_costs_capitalized': software_employee_costs_capitalized,
            'amortization_claimed': software_amortization_claimed,
            'supporting_docs': software_supporting_docs_provided,
            'employees_additional': software_employees_additional_to_norms,
            'flag': software_flag,
            'allowable': software_allowable
        },
        'other_intangibles': {
            'purchased_software': purchased_software_licenses,
            'patents_ip': patents_ip,
            'other': other_intangibles,
            'amortization_claimed': other_intangibles_amortization,
            'supporting_docs': other_supporting_docs_provided,
            'flag': other_flag,
            'allowable': other_allowable
        },
        'total_allowable': allowable_total
    }
    
    return {
        # Identification
        'heuristic_id': 'INTANG-01',
        'heuristic_name': 'Intangible Assets Amortization',
        'line_item': 'Intangible Assets Amortization',
        
        # Calculation Results
        'claimed_value': total_claimed_amortization,
        'allowable_value': allowable_total,
        'variance_absolute': total_claimed_amortization - allowable_total,
        'variance_percentage': ((total_claimed_amortization - allowable_total) / allowable_total * 100) if allowable_total > 0 else 0,
        
        # Tool's Assessment
        'flag': overall_flag,
        'recommended_amount': allowable_total,
        'recommendation_text': overall_recommendation,
        'regulatory_basis': 'Regulation 49, Tariff Regulations 2021; Truing-Up Order 2023-24 (Rejection Precedent)',
        
        # Calculation Details
        'calculation_steps': calc_steps,
        
        # Detailed breakdown
        'amortization_breakdown': amortization_breakdown,
        
        # Staff Review Section
        'staff_override_flag': None,
        'staff_approved_amount': None,
        'staff_justification': '',
        'staff_review_status': 'Pending',
        'reviewed_by': None,
        'reviewed_at': None,
        
        # Dependencies
        'depends_on': [],  # Independent, but note relationship with O&M norms
        
        # Metadata
        'is_primary': True,  # PRIMARY HEURISTIC
        'output_type': 'approved_amount',
        'note': 'High scrutiny required - risk of double-counting with O&M employee costs'
    }