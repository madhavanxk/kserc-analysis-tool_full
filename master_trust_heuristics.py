# master_trust_heuristics.py
"""
Master Trust Heuristics for KSERC Truing-Up Tool
Contains 3 heuristics: MT-BOND-01, MT-REPAY-01, MT-ADD-01
"""

from datetime import datetime
from typing import Dict, Optional


def heuristic_MT_BOND_01(
    total_bond_interest: float,
    sbu_allocation_ratio: float,
    claimed_bond_interest_sbu: float,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    MT-BOND-01: Interest on Master Trust Bonds
    
    20-year bond @ 10% p.a. issued to Master Trust (Rs 8144 Cr initially)
    Interest schedule is fixed per bond terms
    SBU allocation based on employee strength ratio
    
    For FY 2023-24:
    - Total Interest: Rs 570.08 Cr (Year 7 of 20)
    - SBU-G Ratio: 5.59% (31.88/570.08)
    
    Args:
        total_bond_interest: Total bond interest for the year (company-wide) (Cr)
        sbu_allocation_ratio: SBU allocation based on employee strength (%)
        claimed_bond_interest_sbu: Bond interest claimed for this SBU (Cr)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with bond interest allocation
        
    Flags:
        GREEN: Claimed matches allocation (≤1% variance)
        YELLOW: Minor variance (1-3%) - verify allocation ratio
        RED: Variance >3% - recalculate allocation
    """
    
    heuristic_id = "MT-BOND-01"
    heuristic_name = "Interest on Master Trust Bonds"
    line_item = "Master Trust Obligations"
    
    # Calculate SBU share
    allowable_bond_interest_sbu = total_bond_interest * sbu_allocation_ratio / 100
    
    # Calculate variance
    variance_absolute = claimed_bond_interest_sbu - allowable_bond_interest_sbu
    variance_percentage = (variance_absolute / allowable_bond_interest_sbu * 100) if allowable_bond_interest_sbu != 0 else 0
    
    # Determine flag — for Master Trust, under-claiming is favorable (GREEN)
    abs_variance_pct = abs(variance_percentage)
    notes = []

    if variance_percentage <= 0:
        # KSEB claimed less than or equal to allowable — always GREEN
        flag = 'GREEN'
        recommendation_text = f"Approve claimed amount of ₹{claimed_bond_interest_sbu:.2f} Cr (within normative ₹{allowable_bond_interest_sbu:.2f} Cr)."
    elif abs_variance_pct <= 3:
        flag = 'YELLOW'
        notes.append(f"Minor over-claim of {variance_percentage:+.2f}%. Verify SBU allocation ratio.")
        recommendation_text = f"Approve ₹{allowable_bond_interest_sbu:.2f} Cr. " + " ".join(notes)
    else:
        flag = 'RED'
        notes.append(f"Over-claim of {variance_percentage:+.2f}%. Recalculate SBU allocation based on actual employee strength ratio.")
        recommendation_text = f"Approve ₹{allowable_bond_interest_sbu:.2f} Cr. " + " ".join(notes)
    
    # Calculation steps
    calculation_steps = [
        "=== 20-Year Bond Details (Issued 01.04.2017) ===",
        "Original Principal: ₹8144.00 Cr",
        "Coupon Rate: 10% p.a.",
        "Annual Principal Repayment: ₹407.20 Cr",
        "",
        "=== FY 2023-24 (Year 7 of 20) ===",
        f"Total Bond Interest (Company): ₹{total_bond_interest:.2f} Cr",
        f"SBU Allocation Ratio (employee strength): {sbu_allocation_ratio:.2f}%",
        f"Allowable SBU Bond Interest: ₹{allowable_bond_interest_sbu:.2f} Cr",
        f"KSEB Claimed (SBU): ₹{claimed_bond_interest_sbu:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)"
    ]
    
    regulatory_basis = "Regulation 30, Regulation 34; Transfer Scheme notified vide GO(P) 46/2013/PD dated 31.10.2013 and GO(P) 3/2015/PD dated 28.01.2015"
    
    # Staff review
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - allowable_bond_interest_sbu) < 0.5:
            staff_review_status = "Accepted"
        else:
            staff_review_status = "Overridden"
            staff_override_flag = "STAFF_OVERRIDE"
        reviewed_by = staff_name if staff_name else None
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_approved_amount = staff_approved_amount if staff_approved_amount is not None else allowable_bond_interest_sbu
    
    return {
        'heuristic_id': heuristic_id,
        'heuristic_name': heuristic_name,
        'line_item': line_item,
        'claimed_value': claimed_bond_interest_sbu,
        'allowable_value': allowable_bond_interest_sbu,
        'variance_absolute': variance_absolute,
        'variance_percentage': variance_percentage,
        'flag': flag,
        'recommended_amount': allowable_bond_interest_sbu,
        'recommendation_text': recommendation_text,
        'regulatory_basis': regulatory_basis,
        'calculation_steps': calculation_steps,
        'staff_override_flag': staff_override_flag,
        'staff_approved_amount': final_approved_amount,
        'staff_justification': staff_justification,
        'staff_review_status': staff_review_status,
        'reviewed_by': reviewed_by,
        'reviewed_at': reviewed_at,
        'depends_on': [],
        'is_primary': True,
        'output_type': 'pass_through'
    }


def heuristic_MT_REPAY_01(
    annual_principal_repayment: float,
    sbu_allocation_ratio: float,
    claimed_principal_repayment_sbu: float,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    MT-REPAY-01: Repayment of Master Trust Bond Principal
    
    Fixed annual repayment: Rs 407.20 Cr for 20 years
    SBU allocation based on employee strength ratio
    
    Legal Note: Regulation 34(iv) was challenged in Kerala HC WP(C) 19205/2023
    but reinstated via KSERC Second Amendment Regulations 2024 (dated 27.02.2024)
    
    Args:
        annual_principal_repayment: Fixed annual repayment (company-wide) (Cr)
        sbu_allocation_ratio: SBU allocation based on employee strength (%)
        claimed_principal_repayment_sbu: Principal repayment claimed for this SBU (Cr)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with principal repayment allocation
        
    Flags:
        GREEN: Claimed matches allocation (≤1% variance)
        YELLOW: Variance 1-3%
        RED: Variance >3%
    """
    
    heuristic_id = "MT-REPAY-01"
    heuristic_name = "Repayment of Master Trust Bond Principal"
    line_item = "Master Trust Obligations"
    
    # Calculate SBU share
    allowable_principal_repayment_sbu = annual_principal_repayment * sbu_allocation_ratio / 100
    
    # Calculate variance
    variance_absolute = claimed_principal_repayment_sbu - allowable_principal_repayment_sbu
    variance_percentage = (variance_absolute / allowable_principal_repayment_sbu * 100) if allowable_principal_repayment_sbu != 0 else 0
    
    # Determine flag
    abs_variance_pct = abs(variance_percentage)
    notes = []
    
    if abs_variance_pct <= 1:
        flag = 'GREEN'
        recommendation_text = f"Approve Master Trust bond principal repayment of ₹{allowable_principal_repayment_sbu:.2f} Cr."
    elif abs_variance_pct <= 3:
        flag = 'YELLOW'
        notes.append(f"Minor variance of {variance_percentage:+.2f}%. Verify SBU allocation methodology.")
        recommendation_text = f"Approve ₹{allowable_principal_repayment_sbu:.2f} Cr. " + " ".join(notes)
    else:
        flag = 'RED'
        notes.append(f"Variance of {variance_percentage:+.2f}%. Recalculate allocation using employee strength ratio from audited accounts.")
        recommendation_text = f"Approve ₹{allowable_principal_repayment_sbu:.2f} Cr. " + " ".join(notes)
    
    # Calculation steps
    calculation_steps = [
        "=== Bond Repayment Schedule ===",
        "Annual Principal Repayment (Fixed): ₹407.20 Cr",
        "Repayment Period: 20 years (2017-18 to 2036-37)",
        "",
        "=== SBU Allocation ===",
        f"Total Principal Repayment (Company): ₹{annual_principal_repayment:.2f} Cr",
        f"SBU Allocation Ratio (employee strength): {sbu_allocation_ratio:.2f}%",
        f"Allowable SBU Principal Repayment: ₹{allowable_principal_repayment_sbu:.2f} Cr",
        f"KSEB Claimed (SBU): ₹{claimed_principal_repayment_sbu:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)",
        "",
        "=== Legal Status ===",
        "Regulation 34(iv) challenged in Kerala HC WP(C) 19205/2023 (judgment dated 07.09.2023)",
        "Reinstated via KSERC Second Amendment Regulations 2024 (notified 27.02.2024)"
    ]
    
    regulatory_basis = "Regulation 34(iv) as amended by KSERC (Terms and Conditions for Determination of Tariff) (Second Amendment) Regulations, 2024; Transfer Scheme provisions"
    
    # Staff review
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - allowable_principal_repayment_sbu) < 0.5:
            staff_review_status = "Accepted"
        else:
            staff_review_status = "Overridden"
            staff_override_flag = "STAFF_OVERRIDE"
        reviewed_by = staff_name if staff_name else None
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_approved_amount = staff_approved_amount if staff_approved_amount is not None else allowable_principal_repayment_sbu
    
    return {
        'heuristic_id': heuristic_id,
        'heuristic_name': heuristic_name,
        'line_item': line_item,
        'claimed_value': claimed_principal_repayment_sbu,
        'allowable_value': allowable_principal_repayment_sbu,
        'variance_absolute': variance_absolute,
        'variance_percentage': variance_percentage,
        'flag': flag,
        'recommended_amount': allowable_principal_repayment_sbu,
        'recommendation_text': recommendation_text,
        'regulatory_basis': regulatory_basis,
        'calculation_steps': calculation_steps,
        'staff_override_flag': staff_override_flag,
        'staff_approved_amount': final_approved_amount,
        'staff_justification': staff_justification,
        'staff_review_status': staff_review_status,
        'reviewed_by': reviewed_by,
        'reviewed_at': reviewed_at,
        'depends_on': [],
        'is_primary': True,
        'output_type': 'pass_through'
    }


def heuristic_MT_ADD_01(
    actuarial_liability_current_year: float,
    provisional_cap: float,
    sbu_allocation_ratio: float,
    claimed_additional_contribution_sbu: float,
    actuarial_report_submitted: bool,
    govt_approval_obtained: bool,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    MT-ADD-01: Additional Contribution to Master Trust
    
    Funds unfunded actuarial liability beyond the 20-year bond
    
    For FY 2023-24:
    - Actuarial liability addition: Rs 1468.96 Cr (actual)
    - KSERC provisional cap: Rs 400.00 Cr
    - Unfunded liability (31.03.2024): Rs 30,177.31 Cr (CRITICAL!)
    
    Conditional Approval Requirements (Regulation 30(3)):
    1. Actuarial report as on 31.03.YYYY
    2. Proposal approved by KSEBL Board of Directors
    3. State Government approval
    
    KSERC Directive (Para 6.82): Submit within 2 months or provisional approval may be revoked
    
    Args:
        actuarial_liability_current_year: Actuarial liability for current year (Cr)
        provisional_cap: KSERC provisional cap (typically Rs 400 Cr) (Cr)
        sbu_allocation_ratio: SBU allocation based on employee strength (%)
        claimed_additional_contribution_sbu: Additional contribution claimed for this SBU (Cr)
        actuarial_report_submitted: Whether actuarial report submitted (True/False)
        govt_approval_obtained: Whether State Govt approval obtained (True/False)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with conditional approval status
        
    Flags:
        GREEN: All approvals obtained, within actuarial liability
        YELLOW: Provisional approval (capped at Rs 400 Cr), pending documentation
        RED: No actuarial report OR exceeds cap without justification
    """
    
    heuristic_id = "MT-ADD-01"
    heuristic_name = "Additional Contribution to Master Trust"
    line_item = "Master Trust Obligations"
    
    # Determine allowable amount based on compliance
    if actuarial_report_submitted and govt_approval_obtained:
        # Full actuarial liability can be approved
        allowable_total = actuarial_liability_current_year
        flag = 'GREEN'
        note = "Actuarial report submitted and Government approval obtained. Full actuarial liability approved."
    elif actuarial_report_submitted and not govt_approval_obtained:
        # Cap at provisional amount pending govt approval
        allowable_total = min(provisional_cap, actuarial_liability_current_year)
        flag = 'YELLOW'
        note = f"Provisionally approved at ₹{provisional_cap:.2f} Cr cap. Pending State Government approval."
    elif not actuarial_report_submitted:
        # Cap at provisional amount, flag for compliance
        allowable_total = provisional_cap
        flag = 'YELLOW'
        note = f"Provisionally approved at ₹{provisional_cap:.2f} Cr. KSEBL must submit actuarial report as on 31.03.YYYY within 2 months per Regulation 30(3) and Order Para 6.82. Non-compliance may result in revocation."
    else:
        # No documentation - reject
        allowable_total = 0.0
        flag = 'RED'
        note = "Additional contribution disallowed. KSEBL must submit: (1) Actuarial valuation report, (2) Board-approved funding proposal, (3) State Government approval."
    
    # Calculate SBU share
    allowable_sbu = allowable_total * sbu_allocation_ratio / 100
    
    # Calculate variance
    variance_absolute = claimed_additional_contribution_sbu - allowable_sbu
    variance_percentage = (variance_absolute / allowable_sbu * 100) if allowable_sbu != 0 else 0
    
    # Build recommendation
    recommendation_text = f"Approve additional Master Trust contribution of ₹{allowable_sbu:.2f} Cr. {note}"
    
    # Calculation steps
    calculation_steps = [
        "=== Actuarial Liability Context ===",
        f"Actuarial Liability Addition (FY): ₹{actuarial_liability_current_year:.2f} Cr",
        f"KSERC Provisional Cap: ₹{provisional_cap:.2f} Cr",
        f"Unfunded Liability (31.03.YYYY): ₹30,177.31 Cr (CRITICAL CRISIS)",
        "",
        "=== Compliance Status ===",
        f"Actuarial Report Submitted: {'YES' if actuarial_report_submitted else 'NO'}",
        f"State Government Approval: {'YES' if govt_approval_obtained else 'NO'}",
        "",
        "=== Approved Amount ===",
        f"Total Allowable (Company): ₹{allowable_total:.2f} Cr",
        f"SBU Allocation Ratio: {sbu_allocation_ratio:.2f}%",
        f"Allowable SBU Contribution: ₹{allowable_sbu:.2f} Cr",
        f"KSEB Claimed (SBU): ₹{claimed_additional_contribution_sbu:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)",
        "",
        "=== Regulatory Requirement ===",
        "Per Regulation 30(3): Submit actuarial liability + funding proposal + Govt approval",
        "Per Order Para 6.82: Deadline is 2 months from Order date",
        "Warning: Non-compliance may result in revocation of provisional approval"
    ]
    
    regulatory_basis = "Regulation 30(3), Regulation 45(2), Regulation 58(3), Regulation 80; MYT Order dated 25.06.2022; Truing-Up Order Para 6.81-6.82"
    
    # Staff review
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - allowable_sbu) < 1.0:
            staff_review_status = "Accepted"
        else:
            staff_review_status = "Overridden"
            staff_override_flag = "STAFF_OVERRIDE"
        reviewed_by = staff_name if staff_name else None
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_approved_amount = staff_approved_amount if staff_approved_amount is not None else allowable_sbu
    
    return {
        'heuristic_id': heuristic_id,
        'heuristic_name': heuristic_name,
        'line_item': line_item,
        'claimed_value': claimed_additional_contribution_sbu,
        'allowable_value': allowable_sbu,
        'variance_absolute': variance_absolute,
        'variance_percentage': variance_percentage,
        'flag': flag,
        'recommended_amount': allowable_sbu,
        'recommendation_text': recommendation_text,
        'regulatory_basis': regulatory_basis,
        'calculation_steps': calculation_steps,
        'staff_override_flag': staff_override_flag,
        'staff_approved_amount': final_approved_amount,
        'staff_justification': staff_justification,
        'staff_review_status': staff_review_status,
        'reviewed_by': reviewed_by,
        'reviewed_at': reviewed_at,
        'depends_on': [],
        'is_primary': True,
        'output_type': 'conditional'
    }