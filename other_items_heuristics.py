# other_items_heuristics.py
"""
Other Items Heuristics for KSERC Truing-Up Tool
Contains 2 heuristics: OTHER-EXP-01, EXC-01
"""

from datetime import datetime
from typing import Dict, Optional


def heuristic_OTHER_EXP_01(
    claimed_discount_to_consumers: float,
    claimed_flood_losses: float,
    claimed_misc_writeoffs: float,
    flood_supporting_docs: bool,
    writeoff_appeal_orders: bool,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    OTHER-EXP-01: Other Expenses
    
    Three components:
    1. Discount to consumers (advance payment): Legitimate expense
    2. Loss on flood/cyclone: Approved with documentation
    3. Miscellaneous write-offs: Prior period adjustments, appeal authority orders
    
    Args:
        claimed_discount_to_consumers: Discount for advance payment (Cr)
        claimed_flood_losses: Losses due to flood/cyclone (Cr)
        claimed_misc_writeoffs: Miscellaneous write-offs and prior period adjustments (Cr)
        flood_supporting_docs: Whether flood loss documentation provided (True/False)
        writeoff_appeal_orders: Whether appeal authority orders provided for write-offs (True/False)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with other expenses breakdown
        
    Flags:
        GREEN: All components properly documented
        YELLOW: Missing documentation for some components
        RED: No supporting evidence
    """
    
    heuristic_id = "OTHER-EXP-01"
    heuristic_name = "Other Expenses"
    line_item = "Other Expenses"
    
    notes = []
    flags = []
    
    # Component 1: Discount to consumers (always approve if claimed)
    allowable_discount = claimed_discount_to_consumers
    if claimed_discount_to_consumers > 0:
        flags.append('GREEN')
        notes.append(f"Discount to consumers (₹{claimed_discount_to_consumers:.2f} Cr) approved - benefits both licensee and consumers.")
    
    # Component 2: Flood/cyclone losses
    if flood_supporting_docs:
        allowable_flood = claimed_flood_losses
        flags.append('GREEN')
        notes.append(f"Flood/cyclone losses (₹{claimed_flood_losses:.2f} Cr) approved - compensation for injuries, death, damages verified.")
    else:
        allowable_flood = 0.0
        flags.append('YELLOW')
        notes.append(f"Flood/cyclone losses (₹{claimed_flood_losses:.2f} Cr) require supporting documentation.")
    
    # Component 3: Miscellaneous write-offs
    if writeoff_appeal_orders:
        allowable_writeoffs = claimed_misc_writeoffs
        flags.append('GREEN')
        notes.append(f"Miscellaneous write-offs (₹{claimed_misc_writeoffs:.2f} Cr) approved - prior period adjustments per appeal authority orders.")
    else:
        allowable_writeoffs = 0.0
        flags.append('YELLOW')
        notes.append(f"Miscellaneous write-offs (₹{claimed_misc_writeoffs:.2f} Cr) require appeal authority orders or error documentation.")
    
    # Total allowable
    total_allowable = allowable_discount + allowable_flood + allowable_writeoffs
    total_claimed = claimed_discount_to_consumers + claimed_flood_losses + claimed_misc_writeoffs
    
    # Overall flag (worst among components)
    if 'RED' in flags:
        overall_flag = 'RED'
    elif 'YELLOW' in flags:
        overall_flag = 'YELLOW'
    else:
        overall_flag = 'GREEN'
    
    # Variance
    variance_absolute = total_claimed - total_allowable
    variance_percentage = (variance_absolute / total_allowable * 100) if total_allowable != 0 else 0
    
    # Recommendation
    if overall_flag == 'GREEN':
        recommendation_text = f"Approve total other expenses of ₹{total_allowable:.2f} Cr. " + " ".join(notes)
    else:
        recommendation_text = f"Approve ₹{total_allowable:.2f} Cr (out of ₹{total_claimed:.2f} Cr claimed). " + " ".join(notes)
    
    # Calculation steps
    calculation_steps = [
        "=== Component 1: Discount to Consumers ===",
        f"Claimed: ₹{claimed_discount_to_consumers:.2f} Cr",
        f"Allowable: ₹{allowable_discount:.2f} Cr",
        "",
        "=== Component 2: Flood/Cyclone Losses ===",
        f"Claimed: ₹{claimed_flood_losses:.2f} Cr",
        f"Supporting Docs: {'YES' if flood_supporting_docs else 'NO'}",
        f"Allowable: ₹{allowable_flood:.2f} Cr",
        "",
        "=== Component 3: Miscellaneous Write-offs ===",
        f"Claimed: ₹{claimed_misc_writeoffs:.2f} Cr",
        f"Appeal Authority Orders: {'YES' if writeoff_appeal_orders else 'NO'}",
        f"Allowable: ₹{allowable_writeoffs:.2f} Cr",
        "",
        "=== Total Other Expenses ===",
        f"Total Claimed: ₹{total_claimed:.2f} Cr",
        f"Total Allowable: ₹{total_allowable:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)"
    ]
    
    regulatory_basis = "Note 38 of audited accounts; Prudence check on operational expenses; Prior period adjustments per appeal authority directions"
    
    # Staff review
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - total_allowable) < 0.1:
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


def heuristic_EXC_01(
    claimed_calamity_rm: float,
    claimed_govt_loss_takeover: float,
    separate_account_code: bool,
    calamity_supporting_docs: bool,
    staff_name: str = "",
    staff_approved_amount: Optional[float] = None,
    staff_justification: str = ""
) -> Dict:
    """
    EXC-01: Exceptional Items
    
    Two components:
    1. Natural Calamity R&M: One-time expenses for disaster restoration
       - Approved ONLY if separate account codes used and documentation provided
    
    2. Government Loss Takeover: ALWAYS EXCLUDED
       - Reason: Already counted in previous year's truing-up to avoid double counting
       - Example FY 2023-24: Rs 767.72 Cr (75% of FY 2022-23 loss) already trued up
    
    Args:
        claimed_calamity_rm: Natural calamity R&M expenses (Cr)
        claimed_govt_loss_takeover: Government loss takeover amount (typically negative) (Cr)
        separate_account_code: Whether separate account codes used for calamity expenses (True/False)
        calamity_supporting_docs: Whether calamity documentation provided (True/False)
        staff_name: Name of staff reviewing this heuristic
        staff_approved_amount: Amount approved by staff (overrides recommended)
        staff_justification: Staff justification for override
    
    Returns:
        Heuristic result dictionary with exceptional items breakdown
        
    Flags:
        GREEN: Calamity R&M properly documented, no govt takeover claimed
        YELLOW: Calamity R&M needs better documentation
        RED: No separate coding OR govt loss takeover included (double counting)
    """
    
    heuristic_id = "EXC-01"
    heuristic_name = "Exceptional Items"
    line_item = "Exceptional Items"
    
    notes = []
    
    # Component 1: Natural Calamity R&M
    if separate_account_code and calamity_supporting_docs:
        allowable_calamity = claimed_calamity_rm
        flag_calamity = 'GREEN'
        notes.append(f"Natural calamity R&M (₹{claimed_calamity_rm:.2f} Cr) approved with separate account coding verification.")
    elif separate_account_code and not calamity_supporting_docs:
        allowable_calamity = claimed_calamity_rm
        flag_calamity = 'YELLOW'
        notes.append(f"Natural calamity R&M (₹{claimed_calamity_rm:.2f} Cr) approved but requires detailed supporting documents.")
    elif not separate_account_code and calamity_supporting_docs:
        allowable_calamity = 0.0
        flag_calamity = 'RED'
        notes.append(f"Natural calamity R&M (₹{claimed_calamity_rm:.2f} Cr) requires separate account codes to prevent mixing with normal O&M.")
    else:
        allowable_calamity = 0.0
        flag_calamity = 'RED'
        notes.append(f"Natural calamity R&M (₹{claimed_calamity_rm:.2f} Cr) disallowed - insufficient evidence and no separate coding.")
    
    # Component 2: Government Loss Takeover (ALWAYS EXCLUDE)
    allowable_govt_takeover = 0.0
    if claimed_govt_loss_takeover != 0:
        flag_govt = 'RED'
        notes.append(f"Government loss takeover (₹{abs(claimed_govt_loss_takeover):.2f} Cr) EXCLUDED to avoid double counting. This amount was already considered while truing up accounts for the previous year per Order Para 6.105.")
    else:
        flag_govt = 'GREEN'
    
    # Total allowable
    total_allowable = allowable_calamity + allowable_govt_takeover
    total_claimed = claimed_calamity_rm + claimed_govt_loss_takeover
    
    # Overall flag
    if flag_calamity == 'RED' or flag_govt == 'RED':
        overall_flag = 'RED'
    elif flag_calamity == 'YELLOW':
        overall_flag = 'YELLOW'
    else:
        overall_flag = 'GREEN'
    
    # Variance
    variance_absolute = total_claimed - total_allowable
    variance_percentage = (variance_absolute / total_allowable * 100) if total_allowable != 0 else 0
    
    # Recommendation
    if overall_flag == 'GREEN':
        recommendation_text = f"Approve exceptional items of ₹{total_allowable:.2f} Cr. " + " ".join(notes)
    else:
        recommendation_text = f"Approve ₹{total_allowable:.2f} Cr (out of ₹{total_claimed:.2f} Cr claimed). " + " ".join(notes)
    
    # Calculation steps
    calculation_steps = [
        "=== Component 1: Natural Calamity R&M ===",
        f"Claimed: ₹{claimed_calamity_rm:.2f} Cr",
        f"Separate Account Code: {'YES' if separate_account_code else 'NO'}",
        f"Supporting Documents: {'YES' if calamity_supporting_docs else 'NO'}",
        f"Allowable: ₹{allowable_calamity:.2f} Cr",
        "",
        "=== Component 2: Government Loss Takeover ===",
        f"Claimed: ₹{claimed_govt_loss_takeover:.2f} Cr",
        "Status: ALWAYS EXCLUDED (avoid double counting)",
        f"Allowable: ₹{allowable_govt_takeover:.2f} Cr",
        "",
        "=== Total Exceptional Items ===",
        f"Total Claimed: ₹{total_claimed:.2f} Cr",
        f"Total Allowable: ₹{total_allowable:.2f} Cr",
        f"Variance: ₹{variance_absolute:.2f} Cr ({variance_percentage:+.2f}%)",
        "",
        "=== Regulatory Note ===",
        "Natural calamity expenses are one-time operational costs",
        "Must be coded separately from routine O&M to prevent inflation of normative costs",
        "Government loss takeover excluded per Order Para 6.105 to prevent double counting across years"
    ]
    
    regulatory_basis = "Prudence assessment; One-time exceptional expenses; Order Para 6.101-6.106"
    
    # Staff review
    staff_override_flag = None
    staff_review_status = "Pending"
    reviewed_by = None
    reviewed_at = None
    
    if staff_approved_amount is not None:
        if abs(staff_approved_amount - total_allowable) < 0.1:
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
        'output_type': 'discretionary'
    }