"""
Data Mapper + Heuristics for SBU-D (Distribution) - KSERC Truing-Up
=====================================================================
Maps parsed SBU-D data to heuristic inputs and runs analysis.
Called by integration_pipeline.py — not standalone.

Heuristics:
  PP-01     Power Purchase Cost
  OM-D-01   Normative O&M Expenses
  DEP-D-01  Depreciation
  ROE-D-01  Return on Equity
  IFC-D-01  Interest & Finance Charges (total, with breakdown)
  MT-D-01   Master Trust Bond Interest
  NTI-D-01  Non-Tariff Income
  TDL-D-01  T&D Loss Reduction Gain
  INT-D-01  Intangible Assets Amortization
  EXC-D-01  Exceptional Items
  SOL-D-01  Solar Registration Refund
  LID-D-01  Liquidated Damages Refund
  OTH-D-01  Other Expenses
"""

from kserc_constants import (
    CURRENT_FY,
    PP_APPROVED_SBU_D,
    MYT_APPROVED_OM_SBU_D,
    IFC_APPROVED_SBU_D,
    DEP_APPROVED_SBU_D,
    ROE_APPROVED_SBU_D,
    NTI_APPROVED_SBU_D,
    MT_APPROVED_SBU_D,
    BOND_REPAYMENT_SBU_D,
    TD_LOSS_TARGET_SBU_D,
    SBU_D_GPF_RATIO,
    SBU_D_MT_RATIO,
    IWC_RATE_APPROVED,
    IWC_RATE_ACTUAL_SBU_D,
    TD_LOSS_GAIN_SHARE_PCT,
)


# =============================================================================
# HEURISTIC FUNCTIONS
# =============================================================================

def h_pp(m: dict) -> dict:
    """
    PP-01: Power Purchase Cost — Sourcewise Deep-Dive
    Strategy:
      - Compare total claimed vs MYT approved → overall flag
      - Break down by source with implied rate (Rs/unit)
      - Flag high-cost discretionary sources (exchanges, short-term)
      - ISTS charges are pass-through (transmission, not energy)
      - Swap credits reduce total cost — verify netting
    KSERC staff action: verify each source against PPA/CERC/exchange records.
    """
    claimed  = m.get('pp_total_claimed')
    approved = PP_APPROVED_SBU_D
    sources  = m.get('pp_sources', {})

    if claimed is None:
        return {'flag': 'GREY', 'note': 'PP not extracted'}

    var     = claimed - approved
    var_pct = (var / approved * 100) if approved else 0

    # Overall flag
    if abs(var_pct) < 1.0:
        flag = 'GREEN'
    elif abs(var_pct) < 5.0:
        flag = 'YELLOW'
    else:
        flag = 'RED'

    # --- Sourcewise analysis ---
    SOURCE_LABELS = {
        'cgs':         'Central Generating Stations (CGS)',
        'maithon_dvc': 'Maithon & DVC (Long-Term)',
        'dbfoo':       'DBFOO Contracts',
        'medium_term': 'Medium-Term Contracts',
        're_purchase': 'Renewable Energy (Wind/Solar IPPs)',
        'short_term':  'Short-Term Contracts',
        'rgccpp':      'RGCCPP Kayamkulam (Gas)',
        'exchange':    'Power Exchanges (IEX/PXIL)',
        'ists':        'Inter-State Transmission (ISTS)',
        'swap':        'Banking/Swap (Net Credit)',
        'dsm':         'Deviation Settlement (DSM)',
        'solar':       'Solar/Captive (Net Metering)',
        'other':       'Other Charges',
        'total':       'Total Power Purchase',
    }

    # Cost thresholds for flagging (Rs/unit)
    RATE_THRESHOLDS = {
        'RED':    60.0,   # > 60 Rs/unit → expensive, discretionary
        'YELLOW': 45.0,   # 45-60 Rs/unit → elevated, scrutinize
        # < 45 Rs/unit → acceptable
    }

    # Sources that are pass-through (not discretionary)
    PASSTHROUGH_SOURCES = {'ists', 'rgccpp', 'other', 'swap', 'dsm'}

    sourcewise = {}
    for key, data in sources.items():
        if key == 'total':
            continue
        mu     = data.get('quantum_mu')
        cost   = data.get('claimed')
        if cost is None:
            continue

        rate = (cost * 100 / mu) if (mu and mu > 0 and cost > 0) else None

        # Rate-based flag for discretionary sources
        if key in PASSTHROUGH_SOURCES:
            src_flag = 'GREY'   # pass-through, no rate flag
        elif rate is None:
            src_flag = 'GREY'
        elif cost < 0:
            src_flag = 'GREEN'  # swap credit — good
        elif rate >= RATE_THRESHOLDS['RED']:
            src_flag = 'RED'
        elif rate >= RATE_THRESHOLDS['YELLOW']:
            src_flag = 'YELLOW'
        else:
            src_flag = 'GREEN'

        sourcewise[key] = {
            'label':    SOURCE_LABELS.get(key, key),
            'quantum_mu': mu,
            'cost_cr':  cost,
            'rate_per_unit': rate,
            'flag':     src_flag,
        }

    # Identify top cost drivers (sorted by cost descending)
    sorted_sources = sorted(
        [(k, v) for k, v in sourcewise.items()],
        key=lambda x: abs(x[1].get('cost_cr', 0)),
        reverse=True
    )

    # Build notes
    notes = [
        f"Total PP variance={var:+.2f} Cr ({var_pct:+.1f}%) over MYT approved ₹{approved:.2f} Cr.",
        f"Top cost drivers by source:",
    ]
    for key, s in sorted_sources[:5]:
        rate_str = f"@ ₹{s['rate_per_unit']:.2f}/unit" if s['rate_per_unit'] else "(pass-through)"
        flag_str = s['flag']
        notes.append(f"  [{flag_str}] {s['label']}: ₹{s['cost_cr']:.2f} Cr {rate_str}")

    notes.append(
        "KSERC staff must verify: (a) CGS fixed+variable charges vs CERC tariff orders, "
        "(b) exchange purchases vs IEX DAM rates (D59), "
        "(c) short-term contracts vs approved volumes (D65), "
        "(d) ISTS charges vs CTU billing statements."
    )

    return {
        'flag':      flag,
        'claimed':   claimed,
        'allowable': approved,
        'variance':  var,
        'var_pct':   var_pct,
        'sourcewise': sourcewise,
        'note':      '\n'.join(notes),
    }


def h_om_d(m: dict) -> dict:
    """
    OM-D-01: Normative O&M Expenses (Distribution)
    KSEB claims normative amount per TR 2021 — compare vs MYT approved.
    Normative > approved is expected due to inflation escalation.
    """
    claimed  = m.get('om_claimed')
    approved = MYT_APPROVED_OM_SBU_D

    if claimed is None:
        return {'flag': 'GREY', 'note': 'O&M not extracted'}

    var     = claimed - approved
    var_pct = (var / approved * 100) if approved else 0

    if abs(var_pct) < 2.0:
        flag = 'GREEN'
    elif abs(var_pct) < 8.0:
        flag = 'YELLOW'
    else:
        flag = 'RED'

    return {
        'flag':      flag,
        'claimed':   claimed,
        'allowable': approved,
        'variance':  var,
        'var_pct':   var_pct,
        'note': (f"Normative O&M per TR 2021 with actual escalation 3.05%. "
                 f"Variance={var:+.2f} Cr ({var_pct:+.1f}%).")
    }


def h_dep_d(m: dict) -> dict:
    """
    DEP-D-01: Depreciation (Distribution)
    Normative depreciation per TR 2021. Compare vs MYT approved.
    """
    claimed  = m.get('depreciation_claimed')
    approved = DEP_APPROVED_SBU_D

    if claimed is None:
        return {'flag': 'GREY', 'note': 'Depreciation not extracted'}

    var     = claimed - approved
    var_pct = (var / approved * 100) if approved else 0

    if abs(var_pct) < 2.0:
        flag = 'GREEN'
    elif abs(var_pct) < 10.0:
        flag = 'YELLOW'
    else:
        flag = 'RED'

    return {
        'flag':      flag,
        'claimed':   claimed,
        'allowable': approved,
        'variance':  var,
        'var_pct':   var_pct,
        'note': f"Normative depreciation per TR 2021. Variance={var:+.2f} Cr ({var_pct:+.1f}%)."
    }


def h_roe_d(m: dict) -> dict:
    """
    ROE-D-01: Return on Equity (14%)
    Should match MYT approved exactly — equity base fixed.
    """
    claimed  = m.get('roe_claimed')
    approved = ROE_APPROVED_SBU_D

    if claimed is None:
        return {'flag': 'GREY', 'note': 'ROE not extracted'}

    var = claimed - approved

    flag = 'GREEN' if abs(var) < 0.5 else ('YELLOW' if abs(var) < 5 else 'RED')

    return {
        'flag':      flag,
        'claimed':   claimed,
        'allowable': approved,
        'variance':  var,
        'note': f"ROE at 14% on approved equity base. Variance={var:+.2f} Cr."
    }


def h_ifc_d(m: dict) -> dict:
    """
    IFC-D-01: Interest & Finance Charges (Distribution)
    Total from D89. Sub-components from D83 for breakdown.
    Key concern: carrying cost (₹382 Cr) and WC interest (claimed at 11.15% vs approved 9.55%).
    """
    claimed  = m.get('ifc_total_claimed')
    approved = IFC_APPROVED_SBU_D

    if claimed is None:
        return {'flag': 'GREY', 'note': 'IFC not extracted'}

    var     = claimed - approved
    var_pct = (var / approved * 100) if approved else 0

    if abs(var_pct) < 2.0:
        flag = 'GREEN'
    elif abs(var_pct) < 10.0:
        flag = 'YELLOW'
    else:
        flag = 'RED'

    # IFC sub-component breakdown from D83
    ltl           = m.get('ifc_ltl')
    wc            = m.get('ifc_wc')
    gpf           = m.get('ifc_gpf')
    other         = m.get('ifc_other')
    mt_int        = m.get('ifc_master_trust')
    carrying_cost = m.get('ifc_carrying_cost')

    notes = [f"Total IFC variance={var:+.2f} Cr ({var_pct:+.1f}%)."]

    # Carrying cost flag — this is a new item, large amount
    if carrying_cost and carrying_cost > 0:
        notes.append(f"Carrying cost ₹{carrying_cost:.2f} Cr claimed — "
                     f"verify against approved revenue gap and applicable interest rate.")

    # WC interest rate check
    if wc and wc > 0:
        # WC at 11.15% vs approved 9.55%
        notes.append(f"Security Deposit interest ₹{wc:.2f} Cr — "
                     f"KSEB used actual rate; KSERC may cap at approved rate.")

    return {
        'flag':           flag,
        'claimed':        claimed,
        'allowable':      approved,
        'variance':       var,
        'var_pct':        var_pct,
        'components': {
            'term_loan':      ltl,
            'security_dep':   wc,
            'gpf':            gpf,
            'other':          other,
            'master_trust':   mt_int,
            'carrying_cost':  carrying_cost,
        },
        'note': ' '.join(notes),
    }


def h_mt_d(m: dict) -> dict:
    """
    MT-D-01: Additional Contribution to Master Trust
    Should match MYT approved — actuary-determined.
    """
    claimed  = m.get('master_trust_claimed')
    approved = MT_APPROVED_SBU_D

    if claimed is None:
        return {'flag': 'GREY', 'note': 'Master Trust not extracted'}

    var = claimed - approved
    flag = 'GREEN' if abs(var) < 0.5 else 'YELLOW'

    return {
        'flag':      flag,
        'claimed':   claimed,
        'allowable': approved,
        'variance':  var,
        'note': f"Additional contribution to Master Trust. Variance={var:+.2f} Cr."
    }


def h_nti_d(m: dict) -> dict:
    """
    NTI-D-01: Non-Tariff Income (Distribution)
    NTI is a deduction from ARR. Higher NTI = lower revenue gap.
    Compare vs MYT approved — flag if significantly below approved.
    """
    claimed  = m.get('nti_claimed')
    approved = NTI_APPROVED_SBU_D

    if claimed is None:
        return {'flag': 'GREY', 'note': 'NTI not extracted'}

    var     = claimed - approved
    var_pct = (var / approved * 100) if approved else 0

    # NTI: under-reporting is the risk (reduces deduction, inflates gap)
    if var >= 0 or abs(var_pct) < 2.0:
        flag = 'GREEN'
    elif abs(var_pct) < 10.0:
        flag = 'YELLOW'
    else:
        flag = 'RED'

    return {
        'flag':      flag,
        'claimed':   claimed,
        'allowable': approved,
        'variance':  var,
        'var_pct':   var_pct,
        'note': f"NTI deducted from ARR. Claimed={claimed:.2f}, Approved={approved:.2f}. Variance={var:+.2f} Cr."
    }


def h_tdl_d(m: dict) -> dict:
    """
    TDL-D-01: T&D Loss Reduction Gain Sharing
    Per Regulation 37, TR 2021: 50% of gains to KSEB if actual loss < approved target.
    KSEB claims ₹131.85 Cr. Verify from D9/D10/D12.
    Without actual/approved loss%, cannot recompute — flag YELLOW for staff review.
    """
    claimed       = m.get('td_loss_gain_claimed')
    approved_pct  = m.get('td_loss_approved_pct')
    actual_pct    = m.get('td_loss_actual_pct')

    if claimed is None:
        return {'flag': 'GREY', 'note': 'T&D loss gain not extracted'}

    if claimed <= 0:
        return {
            'flag':    'GREEN',
            'claimed': claimed,
            'note':    'No T&D gain claimed or penalty applied.'
        }

    # If we have both percentages, verify
    if approved_pct is not None and actual_pct is not None:
        if actual_pct < approved_pct:
            flag = 'YELLOW'  # Gain is plausible but quantum needs verification
            note = (f"Actual T&D loss {actual_pct:.2f}% < target {approved_pct:.2f}%. "
                    f"Gain sharing per Reg 37 (50%). KSERC staff to verify quantum ₹{claimed:.2f} Cr.")
        else:
            flag = 'RED'
            note = (f"Actual T&D loss {actual_pct:.2f}% >= target {approved_pct:.2f}%. "
                    f"Gain claim of ₹{claimed:.2f} Cr not justified.")
    else:
        flag = 'YELLOW'
        note = (f"T&D loss % not extracted from D10. "
                f"KSERC staff to verify ₹{claimed:.2f} Cr gain from D9/D10/D12.")

    return {
        'flag':           flag,
        'claimed':        claimed,
        'approved_pct':   approved_pct,
        'actual_pct':     actual_pct,
        'note':           note,
    }


def h_intangibles_d(m: dict) -> dict:
    """
    INT-D-01: Intangible Assets Amortization (Distribution)
    Software development costs. No regulatory precedent for auto-approval.
    Flag RED — needs KSERC discretion.
    """
    claimed = m.get('intangibles_claimed')

    if claimed is None or claimed == 0:
        return {'flag': 'GREEN', 'claimed': 0, 'allowable': 0, 'variance': 0,
                'note': 'No intangibles claimed.'}

    return {
        'flag':      'RED',
        'claimed':   claimed,
        'allowable': 0.0,
        'variance':  claimed,
        'note': (f"Software amortization ₹{claimed:.2f} Cr. "
                 f"No explicit provision in TR 2021 for automatic approval. "
                 f"KSERC discretion required.")
    }


def h_exceptional_d(m: dict) -> dict:
    """
    EXC-D-01: Exceptional Items
    Flag RED — needs supporting documentation for each item.
    """
    claimed = m.get('exceptional_claimed')

    if claimed is None or claimed == 0:
        return {'flag': 'GREEN', 'claimed': 0, 'allowable': 0, 'variance': 0,
                'note': 'No exceptional items claimed.'}

    return {
        'flag':      'RED',
        'claimed':   claimed,
        'allowable': 0.0,
        'variance':  claimed,
        'note': (f"Exceptional items ₹{claimed:.2f} Cr. "
                 f"Requires supporting documentation and KSERC case-by-case approval.")
    }


def h_solar_registration(m: dict) -> dict:
    """
    SOL-D-01: Solar Registration Charges Refund
    KSEB claims ₹24.18 Cr refunded to consumers per KSERC RE Regulations 2020, Reg 19(3)(vii).
    Pass-through — verify against registration records.
    """
    claimed = m.get('solar_registration_claimed')

    if claimed is None or claimed == 0:
        return {'flag': 'GREEN', 'claimed': 0, 'note': 'No solar registration refund claimed.'}

    return {
        'flag':      'YELLOW',
        'claimed':   claimed,
        'allowable': claimed,  # regulatory obligation — pass-through
        'variance':  0.0,
        'note': (f"Solar registration refund ₹{claimed:.2f} Cr per Reg 19(3)(vii) of "
                 f"KSERC RE & Net Metering Regulations 2020. "
                 f"KSERC staff to verify against consumer refund records.")
    }


def h_liquidated_damages(m: dict) -> dict:
    """
    LID-D-01: Liquidated Damages Refund
    ₹16.30 Cr refunded to PSITSL per CERC/APTEL orders.
    Pass-through with regulatory order support — flag YELLOW for verification.
    """
    claimed = m.get('liquidated_damages_claimed')

    if claimed is None or claimed == 0:
        return {'flag': 'GREEN', 'claimed': 0, 'note': 'No liquidated damages claimed.'}

    return {
        'flag':      'YELLOW',
        'claimed':   claimed,
        'allowable': claimed,
        'variance':  0.0,
        'note': (f"Liquidated damages refund ₹{claimed:.2f} Cr — "
                 f"per APTEL judgment and CERC order dated 17.10.2024. "
                 f"KSERC staff to verify against court/regulatory orders.")
    }


def h_other_expenses_d(m: dict) -> dict:
    """
    OTH-D-01: Other Expenses
    ₹40.49 Cr — no MYT approval. Flag RED, needs itemized justification.
    """
    claimed = m.get('other_expenses_claimed')

    if claimed is None or claimed == 0:
        return {'flag': 'GREEN', 'claimed': 0, 'allowable': 0, 'variance': 0,
                'note': 'No other expenses claimed.'}

    return {
        'flag':      'RED',
        'claimed':   claimed,
        'allowable': 0.0,
        'variance':  claimed,
        'note': (f"Other expenses ₹{claimed:.2f} Cr with no MYT provision. "
                 f"Itemized justification and supporting accounts required.")
    }


# =============================================================================
# PIPELINE ENTRY POINT
# =============================================================================

def run_sbu_d_heuristics(parsed_data_d: dict) -> list:
    """
    Run all SBU-D heuristics.
    Args:
        parsed_data_d: output from SBUDPDFParser.extract_all()
    Returns:
        list of result dicts with keys: name, flag, claimed, allowable, variance
    """
    m = parsed_data_d.get('mapped', {})

    HEURISTICS = [
        ('Power Purchase Cost',                  h_pp,                  'pp_total_claimed'),
        ('Normative O&M Expenses',               h_om_d,                'om_claimed'),
        ('Depreciation (Normative)',              h_dep_d,               'depreciation_claimed'),
        ('Return on Equity (14%)',                h_roe_d,               'roe_claimed'),
        ('Interest & Finance Charges',           h_ifc_d,               'ifc_total_claimed'),
        ('Master Trust Contribution',            h_mt_d,                'master_trust_claimed'),
        ('Non-Tariff Income',                    h_nti_d,               'nti_claimed'),
        ('T&D Loss Reduction Gain',              h_tdl_d,               'td_loss_gain_claimed'),
        ('Intangible Assets Amortization',       h_intangibles_d,       'intangibles_claimed'),
        ('Exceptional Items',                    h_exceptional_d,       'exceptional_claimed'),
        ('Solar Registration Refund',            h_solar_registration,  'solar_registration_claimed'),
        ('Liquidated Damages Refund',            h_liquidated_damages,  'liquidated_damages_claimed'),
        ('Other Expenses',                       h_other_expenses_d,    'other_expenses_claimed'),
    ]

    results = []
    for name, fn, _ in HEURISTICS:
        try:
            r = fn(m)
            r['name'] = name
            results.append(r)
            flag    = r.get('flag', '?')
            claimed = r.get('claimed', 0) or 0
            allow   = r.get('allowable', 0) or 0
            var     = r.get('variance', claimed - allow)
            print(f"    Flag: {flag} | Claimed: {claimed:.2f} | Allowable: {allow:.2f} | Var: {var:+.2f}")

            # Print sourcewise breakdown for PP
            if name == 'Power Purchase Cost' and r.get('sourcewise'):
                FLAG_ICONS = {'GREEN': '✅', 'YELLOW': '⚠️ ', 'RED': '🔴', 'GREY': '⬜'}
                print()
                print(f"    {'Source':<42} {'MU':>10} {'Cost Cr':>10} {'Rs/unit':>9} {'Flag'}")
                print(f"    {'-'*80}")
                sorted_src = sorted(
                    r['sourcewise'].items(),
                    key=lambda x: abs(x[1].get('cost_cr', 0)), reverse=True
                )
                for key, s in sorted_src:
                    icon     = FLAG_ICONS.get(s['flag'], '?')
                    label    = s['label'][:40]
                    mu       = s.get('quantum_mu')
                    cost     = s.get('cost_cr', 0)
                    rate     = s.get('rate_per_unit')
                    mu_str   = f"{mu:>10.2f}" if mu else f"{'—':>10}"
                    rate_str = f"{rate:>9.2f}" if rate else f"{'—':>9}"
                    print(f"    {label:<42} {mu_str} {cost:>10.2f} {rate_str} {icon}")
                print(f"    {'-'*80}")
                print(f"    {'MYT Approved':42} {'':>10} {PP_APPROVED_SBU_D:>10.2f}")
                print(f"    {'Variance':42} {'':>10} {var:>+10.2f}")
                print()

        except Exception as e:
            results.append({'name': name, 'flag': 'ERROR', 'note': str(e)})
            print(f"    ERROR in {name}: {e}")

    return results
