# ifc_heuristics.py
"""
Interest & Finance Charges Heuristics for KSERC Truing-Up Tool
Contains 4 heuristics: IFC-LTL-01, IFC-WC-01, IFC-GPF-01, IFC-OTH-02
"""

from datetime import datetime
from typing import Dict, Optional


def heuristic_IFC_LTL_01(
    opening_normative_loan: float,
    gfa_additions: float,
    depreciation: float,
    opening_interest_rate: float,
    claimed_interest: float,
    disputed_claims: float = 0.0,
    highest_loan_rate: Optional[float] = None,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    IFC-LTL-01: Interest on Long-Term Loans
    
    Calculates normative interest on long-term loans based on:
    - Opening normative loan balance
    - GFA additions (qualifying for loan)
    - Depreciation (acts as loan repayment)
    - Opening weighted average interest rate
    
    Args:
        opening_normative_loan: Opening loan balance as on 01.04.YYYY (Cr)
        gfa_additions: GFA additions during the year (Cr)
        depreciation: Depreciation for the year from DEP-GEN-01 (Cr)
        opening_interest_rate: Weighted average interest rate at opening (%)
        claimed_interest: Interest on long-term loans claimed by KSEB (Cr)
        disputed_claims: Disputed claims included in opening loan, if any (Cr)
        highest_loan_rate: Highest individual loan rate in portfolio (%)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with normative interest calculation
        
    Flags:
        GREEN: Claimed matches calculated (≤2% variance)
        YELLOW: Disputed claims OR wrong rate suspected (2-15% variance) OR high-cost loans
        RED: Large variance (>15%)
    """
    
    heuristic_id = "IFC-LTL-01"
    heuristic_name = "Interest on Long-Term Loans"
    line_item = "Interest & Finance Charges"
    
    # Step 1: Calculate closing normative loan
    closing_normative_loan = opening_normative_loan + gfa_additions - depreciation
    
    # Step 2: Calculate average normative loan
    average_normative_loan = (opening_normative_loan + closing_normative_loan) / 2
    
    # Step 3: Calculate allowable interest
    allowable_interest = (average_normative_loan * opening_interest_rate) / 100
    
    # Step 4: Calculate variance
    variance_absolute = claimed_interest - allowable_interest
    variance_percentage = (variance_absolute / allowable_interest * 100) if allowable_interest != 0 else 0
    
    # Step 5: Determine flag and recommendation
    flag = 'GREEN'
    notes = []
    
    # Check 1: Disputed claims
    if disputed_claims > 0:
        flag = 'YELLOW'
        notes.append(f"KSEB included ₹{disputed_claims:.2f} Cr disputed claims in opening loan. Verify APTEL status before allowing.")
    
    # Check 2: Variance analysis (interest rate validation)
    abs_variance_pct = abs(variance_percentage)
    if abs_variance_pct > 15:
        if flag != 'YELLOW':
            flag = 'YELLOW'
        notes.append(f"Large variance ({variance_percentage:.2f}%) suggests KSEB may have used incorrect interest rate (e.g., previous year average instead of opening rate).")
    elif abs_variance_pct > 5:
        flag = 'RED'
        notes.append(f"Significant variance ({variance_percentage:.2f}%). Verify interest rate and loan calculation methodology.")
    elif abs_variance_pct <= 2:
        if flag != 'YELLOW':
            flag = 'GREEN'
    
    # Check 3: High-cost loan alert
    if highest_loan_rate is not None and highest_loan_rate > 9.0:
        if flag == 'GREEN':
            flag = 'YELLOW'
        notes.append(f"High-cost loan detected ({highest_loan_rate:.2f}%). Verify refinancing efforts as per Commission directives.")
    
    # Build recommendation text
    if flag == 'GREEN':
        recommendation_text = f"Approve normative interest of ₹{allowable_interest:.2f} Cr. Calculation verified."
    else:
        recommendation_text = f"Approve normative interest of ₹{allowable_interest:.2f} Cr. " + " ".join(notes)
    
    # Calculation steps for transparency
    calculation_steps = [
        f"Opening Normative Loan (01.04.YYYY): ₹{opening_normative_loan:.2f} Cr",
        f"Add: GFA Additions (FY): ₹{gfa_additions:.2f} Cr",
        f"Less: Depreciation (FY): ₹{depreciation:.2f} Cr",
        f"Closing Normative Loan (31.03.YYYY): ₹{closing_normative_loan:.2f} Cr",
        f"Average Normative Loan: ₹{average_normative_loan:.2f} Cr",
        f"Opening Interest Rate: {opening_interest_rate:.2f}%",
        f"Allowable Interest: ₹{allowable_interest:.2f} Cr",
        f"KSEB Claimed: ₹{claimed_interest:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)"
    ]
    
    if disputed_claims > 0:
        calculation_steps.insert(1, f"Note: Disputed claims of ₹{disputed_claims:.2f} Cr detected")
    
    # Regulatory basis
    regulatory_basis = "Regulation 29, Tariff Regulations 2021; Normative loan methodology per MYT framework"
    
    # Staff review handling
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - allowable_interest) < 0.01:
            staff_review_status = "Accepted"
        else:
            staff_review_status = "Overridden"
            staff_override_flag = "STAFF_OVERRIDE"
        reviewed_by = staff_name if staff_name else None
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_approved_amount = staff_approved_amount if staff_approved_amount is not None else allowable_interest
    
    return {
        'heuristic_id': heuristic_id,
        'heuristic_name': heuristic_name,
        'line_item': line_item,
        'claimed_value': claimed_interest,
        'allowable_value': allowable_interest,
        'variance_absolute': variance_absolute,
        'variance_percentage': variance_percentage,
        'flag': flag,
        'recommended_amount': allowable_interest,
        'recommendation_text': recommendation_text,
        'regulatory_basis': regulatory_basis,
        'calculation_steps': calculation_steps,
        'staff_override_flag': staff_override_flag,
        'staff_approved_amount': final_approved_amount,
        'staff_justification': staff_justification,
        'staff_review_status': staff_review_status,
        'reviewed_by': reviewed_by,
        'reviewed_at': reviewed_at,
        'depends_on': ['DEP-GEN-01'],
        'is_primary': True,
        'output_type': 'normative'
    }


def heuristic_IFC_WC_01(
    approved_om_expenses: float,
    opening_gfa_excl_land: float,
    sbi_eblr_rate: float,
    claimed_wc_interest: float,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    IFC-WC-01: Interest on Working Capital
    
    Formula: WC = [(Approved O&M ÷ 12) + (1% × GFA excl. land)] × (SBI EBLR + 2%)
    
    CRITICAL: Uses KSERC-approved O&M from OM-NORM-01, NOT KSEB's claim.
    Common error: KSEB includes Master Trust items in O&M (NOT allowed).
    
    Args:
        approved_om_expenses: O&M approved from OM-NORM-01 (Cr)
        opening_gfa_excl_land: GFA excluding land as on 01.04.YYYY (Cr)
        sbi_eblr_rate: SBI EBLR rate as on 01.04.YYYY (%)
        claimed_wc_interest: WC interest claimed by KSEB (Cr)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with normative WC interest
        
    Flags:
        GREEN: Claimed matches calculated (≤5% variance)
        YELLOW: Variance 5-15% (verify O&M source)
        RED: Variance >15% (likely included Master Trust or other non-O&M items)
    """
    
    heuristic_id = "IFC-WC-01"
    heuristic_name = "Interest on Working Capital"
    line_item = "Interest & Finance Charges"
    
    # Step 1: Calculate working capital components
    one_month_om = approved_om_expenses / 12
    one_percent_spares = opening_gfa_excl_land * 0.01
    working_capital = one_month_om + one_percent_spares
    
    # Step 2: Calculate interest rate (SBI EBLR + 2%)
    wc_interest_rate = sbi_eblr_rate + 2.0
    
    # Step 3: Calculate allowable WC interest
    allowable_wc_interest = (working_capital * wc_interest_rate) / 100
    
    # Step 4: Calculate variance
    variance_absolute = claimed_wc_interest - allowable_wc_interest
    variance_percentage = (variance_absolute / allowable_wc_interest * 100) if allowable_wc_interest != 0 else 0
    
    # Step 5: Determine flag
    abs_variance_pct = abs(variance_percentage)
    notes = []
    
    if abs_variance_pct <= 5:
        flag = 'GREEN'
        recommendation_text = f"Approve normative WC interest of ₹{allowable_wc_interest:.2f} Cr."
    elif abs_variance_pct <= 15:
        flag = 'YELLOW'
        notes.append(f"Variance of {variance_percentage:+.2f}% detected. Verify that KSEB used KSERC-approved O&M (not MYT baseline).")
        recommendation_text = f"Approve normative WC interest of ₹{allowable_wc_interest:.2f} Cr. " + " ".join(notes)
    else:
        flag = 'RED'
        notes.append(f"Large variance ({variance_percentage:+.2f}%) suggests KSEB included non-O&M items (e.g., Master Trust Bond repayment, Additional Master Trust contribution).")
        notes.append("Per Regulation 32, WC comprises ONLY: (1) O&M for 1 month, (2) 1% spares. No receivables for internal generation.")
        recommendation_text = f"Approve normative WC interest of ₹{allowable_wc_interest:.2f} Cr. " + " ".join(notes)
    
    # Calculation steps
    calculation_steps = [
        f"Approved O&M Expenses (from OM-NORM-01): ₹{approved_om_expenses:.2f} Cr",
        f"One Month O&M (÷12): ₹{one_month_om:.2f} Cr",
        f"Opening GFA (excl. land): ₹{opening_gfa_excl_land:.2f} Cr",
        f"1% Spares: ₹{one_percent_spares:.2f} Cr",
        f"Total Working Capital: ₹{working_capital:.2f} Cr",
        f"SBI EBLR Rate (01.04.YYYY): {sbi_eblr_rate:.2f}%",
        f"WC Interest Rate (EBLR + 2%): {wc_interest_rate:.2f}%",
        f"Allowable WC Interest: ₹{allowable_wc_interest:.2f} Cr",
        f"KSEB Claimed: ₹{claimed_wc_interest:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)"
    ]
    
    regulatory_basis = "Regulation 32, Tariff Regulations 2021; Regulation 3(12) (Base rate = SBI EBLR)"
    
    # Staff review
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - allowable_wc_interest) < 0.01:
            staff_review_status = "Accepted"
        else:
            staff_review_status = "Overridden"
            staff_override_flag = "STAFF_OVERRIDE"
        reviewed_by = staff_name if staff_name else None
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_approved_amount = staff_approved_amount if staff_approved_amount is not None else allowable_wc_interest
    
    return {
        'heuristic_id': heuristic_id,
        'heuristic_name': heuristic_name,
        'line_item': line_item,
        'claimed_value': claimed_wc_interest,
        'allowable_value': allowable_wc_interest,
        'variance_absolute': variance_absolute,
        'variance_percentage': variance_percentage,
        'flag': flag,
        'recommended_amount': allowable_wc_interest,
        'recommendation_text': recommendation_text,
        'regulatory_basis': regulatory_basis,
        'calculation_steps': calculation_steps,
        'staff_override_flag': staff_override_flag,
        'staff_approved_amount': final_approved_amount,
        'staff_justification': staff_justification,
        'staff_review_status': staff_review_status,
        'reviewed_by': reviewed_by,
        'reviewed_at': reviewed_at,
        'depends_on': ['OM-NORM-01'],
        'is_primary': True,
        'output_type': 'normative'
    }


def heuristic_IFC_GPF_01(
    opening_gpf_balance_company: float,
    closing_gpf_balance_company: float,
    gpf_interest_rate: float,
    sbu_allocation_ratio: float,
    claimed_gpf_interest_sbu: float,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    IFC-GPF-01: Interest on GPF/Pension Funds
    
    Formula (Company-wide): [(Opening + Closing GPF) ÷ 2] × GPF Rate (7.10%)
    SBU Allocation: Total GPF Interest × SBU Ratio (based on employee strength)
    
    For SBU-G: Ratio = 5.40% (as of FY 2023-24)
    
    Args:
        opening_gpf_balance_company: Company-wide opening GPF balance (Cr)
        closing_gpf_balance_company: Company-wide closing GPF balance (Cr)
        gpf_interest_rate: GPF interest rate, typically 7.10% (%)
        sbu_allocation_ratio: SBU allocation ratio based on employee strength (%)
        claimed_gpf_interest_sbu: GPF interest claimed for this SBU (Cr)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with GPF interest calculation
        
    Flags:
        GREEN: Claimed matches calculated (≤2% variance)
        YELLOW: Minor variance (2-5%) - verify allocation ratio or balances
        RED: Variance >5% - verify GPF balances and allocation methodology
    """
    
    heuristic_id = "IFC-GPF-01"
    heuristic_name = "Interest on GPF/Pension Funds"
    line_item = "Interest & Finance Charges"
    
    # Step 1: Calculate average GPF balance (company-wide)
    average_gpf_balance = (opening_gpf_balance_company + closing_gpf_balance_company) / 2
    
    # Step 2: Calculate total GPF interest (company-wide)
    total_gpf_interest = (average_gpf_balance * gpf_interest_rate) / 100
    
    # Step 3: Calculate SBU share
    allowable_gpf_interest_sbu = total_gpf_interest * sbu_allocation_ratio / 100
    
    # Step 4: Calculate variance
    variance_absolute = claimed_gpf_interest_sbu - allowable_gpf_interest_sbu
    variance_percentage = (variance_absolute / allowable_gpf_interest_sbu * 100) if allowable_gpf_interest_sbu != 0 else 0
    
    # Step 5: Determine flag — under-claiming is favorable (GREEN)
    abs_variance_pct = abs(variance_percentage)
    notes = []

    if variance_percentage <= 0:
        # KSEB claimed less than normative — favorable to consumers
        flag = 'GREEN'
        recommendation_text = f"Approve claimed amount ₹{claimed_gpf_interest_sbu:.2f} Cr (normative is ₹{allowable_gpf_interest_sbu:.2f} Cr — KSEB under-claiming)."
    elif abs_variance_pct <= 2:
        flag = 'GREEN'
        recommendation_text = f"Approve GPF interest of ₹{allowable_gpf_interest_sbu:.2f} Cr."
    elif abs_variance_pct <= 5:
        flag = 'YELLOW'
        notes.append(f"Minor over-claim of {variance_percentage:+.2f}%. Verify SBU allocation ratio or GPF balances from audited accounts.")
        recommendation_text = f"Approve ₹{allowable_gpf_interest_sbu:.2f} Cr. " + " ".join(notes)
    else:
        flag = 'RED'
        notes.append(f"Over-claim of {variance_percentage:+.2f}%. Verify: (1) Opening/closing GPF balances from Note 23 of audited accounts, (2) SBU allocation ratio based on employee strength.")
        recommendation_text = f"Approve ₹{allowable_gpf_interest_sbu:.2f} Cr. " + " ".join(notes)
    
    # Calculation steps
    calculation_steps = [
        "=== Company-wide Calculation ===",
        f"Opening GPF Balance (01.04.YYYY): ₹{opening_gpf_balance_company:.2f} Cr",
        f"Closing GPF Balance (31.03.YYYY): ₹{closing_gpf_balance_company:.2f} Cr",
        f"Average GPF Balance: ₹{average_gpf_balance:.2f} Cr",
        f"GPF Interest Rate: {gpf_interest_rate:.2f}%",
        f"Total GPF Interest (Company): ₹{total_gpf_interest:.2f} Cr",
        "",
        "=== SBU Allocation ===",
        f"SBU Allocation Ratio (employee strength): {sbu_allocation_ratio:.2f}%",
        f"Allowable SBU GPF Interest: ₹{allowable_gpf_interest_sbu:.2f} Cr",
        f"KSEB Claimed (SBU): ₹{claimed_gpf_interest_sbu:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)"
    ]
    
    regulatory_basis = "Established practice for low-cost internal funding; GPF interest allowed as actuals per audited accounts; SBU allocation per employee strength ratio"
    
    # Staff review
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - allowable_gpf_interest_sbu) < 0.01:
            staff_review_status = "Accepted"
        else:
            staff_review_status = "Overridden"
            staff_override_flag = "STAFF_OVERRIDE"
        reviewed_by = staff_name if staff_name else None
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_approved_amount = staff_approved_amount if staff_approved_amount is not None else allowable_gpf_interest_sbu
    
    return {
        'heuristic_id': heuristic_id,
        'heuristic_name': heuristic_name,
        'line_item': line_item,
        'claimed_value': claimed_gpf_interest_sbu,
        'allowable_value': allowable_gpf_interest_sbu,
        'variance_absolute': variance_absolute,
        'variance_percentage': variance_percentage,
        'flag': flag,
        'recommended_amount': allowable_gpf_interest_sbu,
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


def heuristic_IFC_OTH_02(
    claimed_gbi: float,
    claimed_bank_charges: float,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    IFC-OTH-02: Other Interest & Charges
    
    Two components:
    1. Generation-Based Incentive (GBI): Always disallowed (no scheme in force)
    2. Other Bank Charges: Approved if reasonable (<₹0.5 Cr typically acceptable)
    
    Args:
        claimed_gbi: GBI amount claimed by KSEB (Cr)
        claimed_bank_charges: Bank charges claimed by KSEB (Cr)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with other charges breakdown
        
    Flags:
        GREEN: No GBI claimed, bank charges reasonable
        YELLOW: Bank charges elevated (₹0.5-1.0 Cr), needs review
        RED: GBI claimed OR excessive bank charges (>₹1.0 Cr)
    """
    
    heuristic_id = "IFC-OTH-02"
    heuristic_name = "Other Interest & Charges (GBI + Bank Charges)"
    line_item = "Interest & Finance Charges"
    
    # Component 1: GBI (always disallowed)
    allowable_gbi = 0.0
    
    # Component 2: Bank Charges (approve if reasonable)
    if claimed_bank_charges <= 0.5:
        allowable_bank_charges = claimed_bank_charges
        flag_bank = 'GREEN'
        note_bank = ""
    elif claimed_bank_charges <= 1.0:
        allowable_bank_charges = claimed_bank_charges
        flag_bank = 'YELLOW'
        note_bank = f"Bank charges of ₹{claimed_bank_charges:.2f} Cr flagged for staff review (elevated but may be justified)."
    else:
        allowable_bank_charges = 0.0
        flag_bank = 'RED'
        note_bank = f"Bank charges of ₹{claimed_bank_charges:.2f} Cr appear excessive. Require detailed justification and supporting documents."
    
    # Total allowable
    total_allowable = allowable_gbi + allowable_bank_charges
    total_claimed = claimed_gbi + claimed_bank_charges
    
    # Overall flag
    if claimed_gbi > 0:
        overall_flag = 'RED'
    else:
        overall_flag = flag_bank
    
    # Variance
    variance_absolute = total_claimed - total_allowable
    variance_percentage = (variance_absolute / total_allowable * 100) if total_allowable != 0 else (-100.0 if total_claimed > 0 else 0.0)
    
    # Build recommendation
    notes = []
    if claimed_gbi > 0:
        notes.append(f"GBI of ₹{claimed_gbi:.2f} Cr disallowed (no GBI scheme in force for FY 2023-24).")
    
    if claimed_bank_charges > 0:
        if allowable_bank_charges > 0:
            notes.append(f"Bank charges of ₹{claimed_bank_charges:.2f} Cr approved as legitimate operational expense.")
        if note_bank:
            notes.append(note_bank)
    
    if overall_flag == 'GREEN':
        recommendation_text = f"Approve ₹{total_allowable:.2f} Cr. " + " ".join(notes)
    else:
        recommendation_text = f"Approve ₹{total_allowable:.2f} Cr (out of ₹{total_claimed:.2f} Cr claimed). " + " ".join(notes)
    
    # Calculation steps
    calculation_steps = [
        "=== Component 1: Generation-Based Incentive (GBI) ===",
        f"KSEB Claimed GBI: ₹{claimed_gbi:.2f} Cr",
        "GBI Scheme Status: No scheme in force for FY 2023-24",
        f"Allowable GBI: ₹{allowable_gbi:.2f} Cr (Disallowed)",
        "",
        "=== Component 2: Other Bank Charges ===",
        f"KSEB Claimed Bank Charges: ₹{claimed_bank_charges:.2f} Cr",
        f"Allowable Bank Charges: ₹{allowable_bank_charges:.2f} Cr",
        "",
        "=== Total Other Charges ===",
        f"Total Claimed: ₹{total_claimed:.2f} Cr",
        f"Total Allowable: ₹{total_allowable:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)"
    ]
    
    regulatory_basis = "No applicable GBI scheme for the year; Bank charges allowed as legitimate operational expenses subject to prudence check"
    
    # Staff review
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - total_allowable) < 0.01:
            staff_review_status = "Accepted"
        else:
            staff_review_status = "Overridden"
            staff_override_flag = "STAFF_OVERRIDE"
        reviewed_by = staff_name if staff_name else None
        reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    final_approved_amount = staff_approved_amount if staff_approved_amount is not None else total_allowable
    
    return {
        'heuristic_id': heuristic_id,
        'heuristic_name': heuristic_name,
        'line_item': line_item,
        'claimed_value': total_claimed,
        'allowable_value': total_allowable,
        'variance_absolute': variance_absolute,
        'variance_percentage': variance_percentage,
        'flag': overall_flag,
        'recommended_amount': total_allowable,
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
        'output_type': 'mixed'
    }