"""
Return on Equity (ROE) Heuristic for SBU-G
Contains: ROE-01
"""

from typing import Dict, Optional

def heuristic_ROE_01(equity_capital: float,
                     roe_rate: float,
                     claimed_roe: float,
                     equity_infusion_during_year: float = 0.0,
                     equity_infusion_details: Optional[Dict] = None) -> Dict:
    """
    ROE-01: Return on Equity Calculation
    
    Simple calculation: ROE = Equity Capital × ROE Rate
    Equity capital is fixed unless there's new infusion during the year.
    
    Args:
        equity_capital: Opening equity capital (831.27 Cr for SBU-G)
        roe_rate: Fixed ROE rate (14% = 0.14)
        claimed_roe: ROE claimed by KSEB
        equity_infusion_during_year: Additional equity infused (if any)
        equity_infusion_details: Dict with keys: date, amount, govt_approval_ref
    
    Returns:
        Heuristic result with calculated ROE
    """
    # Adjust equity if there was infusion
    adjusted_equity = equity_capital + equity_infusion_during_year
    
    # Calculate allowable ROE
    allowable_roe = adjusted_equity * roe_rate
    
    # Variance calculation
    variance_abs = claimed_roe - allowable_roe
    variance_pct = (variance_abs / allowable_roe) * 100 if allowable_roe > 0 else 0
    
    # Flag determination (ROE is strictly calculated - no tolerance)
    if abs(variance_abs) < 0.01:  # Less than 1 lakh difference (rounding)
        flag = 'GREEN'
        recommendation = 'Approve as calculated'
    else:
        flag = 'RED'
        recommendation = 'Claimed ROE does not match calculation - allow only calculated amount'
    
    # Calculation steps
    calc_steps = [
        "ROE Calculation (Regulation 47, Tariff Regulations 2021):",
        "",
        f"Opening Equity Capital: {equity_capital:.2f} Cr"
    ]
    
    if equity_infusion_during_year > 0:
        calc_steps.extend([
            f"Equity Infusion During Year: {equity_infusion_during_year:.2f} Cr",
            f"Adjusted Equity Capital: {adjusted_equity:.2f} Cr"
        ])
        if equity_infusion_details:
            calc_steps.extend([
                f"  Infusion Date: {equity_infusion_details.get('date', 'Not provided')}",
                f"  Govt Approval: {equity_infusion_details.get('govt_approval_ref', 'Not provided')}"
            ])
    else:
        calc_steps.append("No equity infusion during the year")
    
    calc_steps.extend([
        "",
        f"ROE Rate (Fixed): {roe_rate*100:.2f}%",
        f"Calculation: {adjusted_equity:.2f} Cr × {roe_rate*100:.2f}%",
        f"Allowable ROE: {allowable_roe:.2f} Cr",
        "",
        f"KSEB Claimed: {claimed_roe:.2f} Cr",
        f"Variance: {variance_abs:+.2f} Cr ({variance_pct:+.2f}%)",
        "",
        "Note: ROE is a normative calculation with zero tolerance.",
        "Any variance requires justification or correction."
    ])
    
    return {
        # Identification
        'heuristic_id': 'ROE-01',
        'heuristic_name': 'Return on Equity Calculation',
        'line_item': 'Return on Equity',
        
        # Calculation Results
        'claimed_value': claimed_roe,
        'allowable_value': allowable_roe,
        'variance_absolute': variance_abs,
        'variance_percentage': variance_pct,
        
        # Tool's Assessment
        'flag': flag,
        'recommended_amount': allowable_roe,
        'recommendation_text': recommendation,
        'regulatory_basis': 'Regulation 47, Tariff Regulations 2021',
        
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
        'is_primary': True,  # PRIMARY HEURISTIC - determines approved ROE
        'output_type': 'approved_amount',
        
        # Additional context
        'equity_details': {
            'opening_equity': equity_capital,
            'infusion_during_year': equity_infusion_during_year,
            'adjusted_equity': adjusted_equity,
            'roe_rate': roe_rate
        }
    }