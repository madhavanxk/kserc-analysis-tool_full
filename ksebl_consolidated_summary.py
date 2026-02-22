"""
KSEBL Consolidated Summary — All Three SBUs
============================================
Aggregates SBU-G, SBU-T, SBU-D heuristic results into a single
company-level ARR view for KSERC staff.

Called by integration_pipeline.py after all three SBU analyses complete.
Can also run standalone if passed pre-built results dicts.
"""

from typing import Dict, List, Optional

# =============================================================================
# CONSTANTS — KSEBL company-level totals from petition (ARR tables G6/T6/D89)
# =============================================================================

# MYT approved ARR by SBU (Rs Cr)
MYT_ARR = {
    'SBU-G':  734.63,    # Cost of generation (as seen in D89 approved)
    'SBU-T':  1763.72,   # From T6 approved total
    'SBU-D':  20591.41,  # From D89 approved total
}

# MYT approved ERC (Revenue) by SBU
MYT_ERC = {
    'SBU-G':  None,       # Generation costs passed to D via inter-SBU charge
    'SBU-T':  None,       # Transmission costs passed to D via inter-SBU charge
    'SBU-D':  17571.11,   # From D89 ERC approved
}


# =============================================================================
# LINE ITEM MAPPING — common items across SBUs for aggregation
# =============================================================================

# Map heuristic names → canonical line item for cross-SBU comparison
CANONICAL_MAP = {
    # SBU-G names
    'Return on Equity':                           'roe',
    'Depreciation':                               'depreciation',
    'O&M Expenses':                               'om_expenses',
    'Interest & Finance Charges':                 'ifc',
    'Interest on Master Trust Bonds':             'master_trust',
    'Non-Tariff Income':                          'nti',
    'Intangible Assets Amortization':             'intangibles',
    'Exceptional Items':                          'exceptional',
    # SBU-T names
    'Return on Equity (14%) — SBU-T':            'roe',
    'Depreciation (Normative) — SBU-T':          'depreciation',
    'Normative O&M Expenses - Transmission':     'om_expenses',
    'ifc':                                        'ifc',
    'Interest on Master Trust Bonds':             'master_trust',
    'Non-Tariff Income Validation':              'nti',
    'Intangible Assets Amortization':            'intangibles',
    'Exceptional Items':                          'exceptional',
    # SBU-D names
    'Power Purchase Cost':                        'power_purchase',
    'Normative O&M Expenses':                     'om_expenses',
    'Depreciation (Normative)':                   'depreciation',
    'Return on Equity (14%)':                     'roe',
    'Interest & Finance Charges':                 'ifc',
    'Master Trust Contribution':                  'master_trust',
    'Non-Tariff Income':                          'nti',
    'T&D Loss Reduction Gain':                    'td_loss_gain',
    'Intangible Assets Amortization':             'intangibles',
    'Exceptional Items':                          'exceptional',
    'Solar Registration Refund':                  'solar_reg',
    'Liquidated Damages Refund':                  'liq_damages',
    'Other Expenses':                             'other_expenses',
}

CANONICAL_LABELS = {
    'power_purchase': 'Power Purchase (SBU-D only)',
    'roe':            'Return on Equity (14%)',
    'depreciation':   'Depreciation (Normative)',
    'om_expenses':    'O&M Expenses (Normative)',
    'ifc':            'Interest & Finance Charges',
    'master_trust':   'Master Trust (Bonds + Contribution)',
    'nti':            'Non-Tariff Income',
    'td_loss_gain':   'T&D Loss Reduction Gain (D only)',
    'intangibles':    'Intangible Assets Amortization',
    'exceptional':    'Exceptional Items',
    'solar_reg':      'Solar Registration Refund',
    'liq_damages':    'Liquidated Damages Refund',
    'other_expenses': 'Other Expenses',
    'fuel':           'Fuel Costs (SBU-G only)',
}


# =============================================================================
# AGGREGATION LOGIC
# =============================================================================

def _extract_sbu_g_items(sbu_g_results: Dict) -> List[Dict]:
    """Extract line items from SBU-G results (dict-of-dicts format)."""
    items = []
    line_items = sbu_g_results.get('line_items', {})

    # SBU-G stores line items as dict with enriched heuristic format
    FLAG_MAP = {
        'GREEN': 'GREEN', 'YELLOW': 'YELLOW', 'RED': 'RED',
        'GREY': 'GREY', 'ERROR': 'ERROR',
    }

    # Key items we know about from SBU-G
    SBU_G_ITEMS = {
        'roe':              ('Return on Equity', 'roe'),
        'depreciation':     ('Depreciation', 'depreciation'),
        'fuel_costs':       ('Fuel Costs', 'fuel'),
        'om_expenses':      ('O&M Expenses', 'om_expenses'),
        'ifc':              ('Interest & Finance Charges', 'ifc'),
        'master_trust':     ('Interest on Master Trust Bonds', 'master_trust'),
        'nti':              ('Non-Tariff Income', 'nti'),
        'intangibles':      ('Intangible Assets Amortization', 'intangibles'),
        'other_expenses':   ('Other Expenses', 'other_expenses'),
        'exceptional_items':('Exceptional Items', 'exceptional'),
    }

    for key, (name, canonical) in SBU_G_ITEMS.items():
        data = line_items.get(key, {})
        if not data or data.get('status') in ('skipped', 'error'):
            continue

        flag = data.get('flag', 'GREY')

        # IFC is stored as a nested dict with 'claimed_value'/'allowable_value' at top
        # O&M chain stores primary_heuristic sub-dict
        claimed = (
            data.get('claimed_value')
            or data.get('claimed')
            or data.get('primary_heuristic', {}).get('claimed_value')
            or 0
        )
        allow = (
            data.get('allowable_value')
            or data.get('allowable')
            or data.get('primary_heuristic', {}).get('allowable_value')
            or 0
        )

        items.append({
            'name':      name,
            'canonical': canonical,
            'sbu':       'G',
            'flag':      flag,
            'claimed':   float(claimed),
            'allowable': float(allow),
            'variance':  float(claimed) - float(allow),
        })

    return items


def _extract_sbu_t_items(sbu_t_results: Dict) -> List[Dict]:
    """Extract line items from SBU-T results (list format from run_sbu_t_heuristics)."""
    items = []
    line_items = sbu_t_results.get('line_items', {})

    if isinstance(line_items, list):
        for r in line_items:
            name = r.get('name', '')
            # Skip balance sheet items — bond repayment is not an expense
            if 'repayment' in name.lower():
                continue
            canonical = CANONICAL_MAP.get(name, name.lower().replace(' ', '_'))
            claimed   = r.get('claimed', 0) or 0
            allow     = r.get('allowable', 0) or 0
            items.append({
                'name':      name,
                'canonical': canonical,
                'sbu':       'T',
                'flag':      r.get('flag', 'GREY'),
                'claimed':   claimed,
                'allowable': allow,
                'variance':  claimed - allow,
            })
    elif isinstance(line_items, dict):
        for name, data in line_items.items():
            if not isinstance(data, dict):
                continue
            # Skip balance sheet items
            if 'repayment' in name.lower():
                continue
            canonical = CANONICAL_MAP.get(name, name.lower().replace(' ', '_'))
            claimed   = data.get('claimed_value', data.get('claimed', 0)) or 0
            allow     = data.get('allowable_value', data.get('allowable', 0)) or 0
            items.append({
                'name':      name,
                'canonical': canonical,
                'sbu':       'T',
                'flag':      data.get('flag', 'GREY'),
                'claimed':   claimed,
                'allowable': allow,
                'variance':  claimed - allow,
            })

    return items


def _extract_sbu_d_items(sbu_d_results: Dict) -> List[Dict]:
    """Extract line items from SBU-D results (list format)."""
    items = []
    line_items = sbu_d_results.get('line_items', [])

    for r in line_items:
        name      = r.get('name', '')
        canonical = CANONICAL_MAP.get(name, name.lower().replace(' ', '_'))
        claimed   = r.get('claimed', 0) or 0
        allow     = r.get('allowable', 0) or 0
        items.append({
            'name':      name,
            'canonical': canonical,
            'sbu':       'D',
            'flag':      r.get('flag', 'GREY'),
            'claimed':   claimed,
            'allowable': allow,
            'variance':  claimed - allow,
            # PP sourcewise if available
            'sourcewise': r.get('sourcewise', {}),
        })

    return items


# =============================================================================
# CONSOLIDATED REPORT
# =============================================================================

def build_consolidated_summary(results: Dict) -> Dict:
    """
    Build consolidated KSEBL-level summary from pipeline results.

    Args:
        results: Full pipeline results dict.
                 SBU-G: results['line_items'] (top-level)
                 SBU-T: results['sbu_t']['line_items']
                 SBU-D: results['sbu_d']['line_items']

    Returns:
        dict with consolidated totals, flag counts, and line-by-line cross-SBU view.
    """
    # SBU-G data lives at top level (legacy structure from original pipeline)
    sbu_g_items_raw = results.get('line_items', {})
    sbu_g = {'line_items': sbu_g_items_raw}

    sbu_t = results.get('sbu_t', {})
    sbu_d = results.get('sbu_d', {})

    # Extract items from each SBU
    g_items = _extract_sbu_g_items(sbu_g) if sbu_g.get('status') != 'error' else []
    t_items = _extract_sbu_t_items(sbu_t) if sbu_t.get('status') != 'error' else []
    d_items = _extract_sbu_d_items(sbu_d) if sbu_d.get('status') != 'error' else []

    all_items = g_items + t_items + d_items

    # --- Aggregate by canonical key ---
    canonical_totals: Dict[str, Dict] = {}
    for item in all_items:
        key = item['canonical']
        if key not in canonical_totals:
            canonical_totals[key] = {
                'label':        CANONICAL_LABELS.get(key, key),
                'sbu_g_claimed': 0, 'sbu_g_allow': 0, 'sbu_g_flag': '—',
                'sbu_t_claimed': 0, 'sbu_t_allow': 0, 'sbu_t_flag': '—',
                'sbu_d_claimed': 0, 'sbu_d_allow': 0, 'sbu_d_flag': '—',
                'total_claimed': 0, 'total_allow': 0,
            }
        sbu = item['sbu'].lower()
        canonical_totals[key][f'sbu_{sbu}_claimed'] += item['claimed']
        canonical_totals[key][f'sbu_{sbu}_allow']   += item['allowable']
        canonical_totals[key][f'sbu_{sbu}_flag']     = item['flag']
        canonical_totals[key]['total_claimed']       += item['claimed']
        canonical_totals[key]['total_allow']         += item['allowable']

    # Add variance
    for key, data in canonical_totals.items():
        data['total_variance'] = data['total_claimed'] - data['total_allow']

    # --- Company totals ---
    total_claimed  = sum(i['claimed']   for i in all_items if i['canonical'] != 'nti')
    total_allow    = sum(i['allowable'] for i in all_items if i['canonical'] != 'nti')
    total_excess   = total_claimed - total_allow

    # ARR from D89 (most reliable for distribution-level)
    arr_d89_claimed = None
    arr_d89_approved = None
    erc_d89_claimed  = None
    revenue_gap      = None

    d_line_items = sbu_d.get('line_items', [])
    for r in d_line_items:
        # These come from ARR sub-items in summary — but gap is in D89
        pass
    # Pull from sbu_d summary if available
    d_summary = sbu_d.get('summary', {})

    # Flag counts
    all_flags = [i['flag'] for i in all_items]
    flag_counts = {
        'GREEN':  all_flags.count('GREEN'),
        'YELLOW': all_flags.count('YELLOW'),
        'RED':    all_flags.count('RED'),
        'GREY':   all_flags.count('GREY'),
    }

    return {
        'canonical_totals': canonical_totals,
        'all_items':        all_items,
        'company_totals': {
            'total_claimed':  total_claimed,
            'total_allow':    total_allow,
            'total_excess':   total_excess,
        },
        'flag_counts': flag_counts,
        'sbu_summaries': {
            'G': {'claimed': sum(i['claimed'] for i in g_items),
                  'allow':   sum(i['allowable'] for i in g_items)},
            'T': {'claimed': sum(i['claimed'] for i in t_items),
                  'allow':   sum(i['allowable'] for i in t_items)},
            'D': {'claimed': sum(i['claimed'] for i in d_items),
                  'allow':   sum(i['allowable'] for i in d_items)},
        },
    }


# =============================================================================
# DISPLAY
# =============================================================================

FLAG_ICONS = {'GREEN': '✅', 'YELLOW': '⚠️ ', 'RED': '🔴', 'GREY': '⬜', '—': '  '}

def _flag_icon(f: str) -> str:
    return FLAG_ICONS.get(f, '  ')

def display_consolidated_summary(summary: Dict) -> None:
    """Print the consolidated KSEBL summary to console."""

    WIDTH = 110

    print()
    print("=" * WIDTH)
    print("  KSEBL CONSOLIDATED ARR ANALYSIS — FY 2024-25")
    print("  All three Strategic Business Units")
    print("=" * WIDTH)

    # --- SBU totals header ---
    sbu_s = summary['sbu_summaries']
    ct    = summary['company_totals']

    print()
    print(f"  {'SBU':<10} {'Claimed (Cr)':>15} {'Allowable (Cr)':>15} {'Excess (Cr)':>13}")
    print(f"  {'-'*55}")
    for sbu_key, label in [('G', 'SBU-G (Generation)'), ('T', 'SBU-T (Transmission)'), ('D', 'SBU-D (Distribution)')]:
        s = sbu_s[sbu_key]
        excess = s['claimed'] - s['allow']
        print(f"  {label:<30} {s['claimed']:>15,.2f} {s['allow']:>15,.2f} {excess:>+13,.2f}")
    print(f"  {'-'*55}")
    print(f"  {'KSEBL TOTAL':<30} {ct['total_claimed']:>15,.2f} "
          f"{ct['total_allow']:>15,.2f} {ct['total_excess']:>+13,.2f}")
    print()

    # --- Flag counts ---
    fc = summary['flag_counts']
    print(f"  Overall Risk Profile: "
          f"✅ GREEN={fc['GREEN']}  "
          f"⚠️  YELLOW={fc['YELLOW']}  "
          f"🔴 RED={fc['RED']}  "
          f"⬜ GREY={fc['GREY']}")
    print()

    # --- Cross-SBU line item table ---
    print("─" * WIDTH)
    print(f"  {'Line Item':<36} "
          f"{'SBU-G':>10} {'SBU-T':>10} {'SBU-D':>12} "
          f"{'TOTAL Claimed':>14} {'TOTAL Allow':>13} {'Excess':>10}")
    print("─" * WIDTH)

    DISPLAY_ORDER = [
        'power_purchase', 'fuel', 'om_expenses', 'depreciation', 'roe',
        'ifc', 'master_trust', 'td_loss_gain', 'nti',
        'intangibles', 'exceptional', 'solar_reg', 'liq_damages', 'other_expenses',
    ]

    for key in DISPLAY_ORDER:
        data = summary['canonical_totals'].get(key)
        if not data:
            continue

        label = data['label'][:35]
        gc    = data['sbu_g_claimed'] or 0
        tc_   = data['sbu_t_claimed'] or 0
        dc    = data['sbu_d_claimed'] or 0
        tot_c = data['total_claimed']
        tot_a = data['total_allow']
        excess = data['total_variance']

        # Composite flag — worst of the three
        flags = [data['sbu_g_flag'], data['sbu_t_flag'], data['sbu_d_flag']]
        if 'RED' in flags:
            row_flag = '🔴'
        elif 'YELLOW' in flags:
            row_flag = '⚠️ '
        elif 'GREEN' in flags:
            row_flag = '✅'
        else:
            row_flag = '⬜'

        gc_str  = f"{gc:>10,.1f}"  if gc  else f"{'—':>10}"
        tc_str  = f"{tc_:>10,.1f}" if tc_ else f"{'—':>10}"
        dc_str  = f"{dc:>12,.1f}"  if dc  else f"{'—':>12}"

        print(f"  {row_flag} {label:<35} "
              f"{gc_str} {tc_str} {dc_str} "
              f"{tot_c:>14,.2f} {tot_a:>13,.2f} {excess:>+10,.2f}")

    print("─" * WIDTH)
    print(f"  {'TOTAL (excl. NTI deduction)':<36} "
          f"{'':>10} {'':>10} {'':>12} "
          f"{ct['total_claimed']:>14,.2f} {ct['total_allow']:>13,.2f} "
          f"{ct['total_excess']:>+10,.2f}")
    print("─" * WIDTH)

    # --- Top issues ---
    print()
    print("  TOP ISSUES REQUIRING KSERC ATTENTION:")
    print()

    # Sort all items by variance desc, show top 8 RED/YELLOW
    actionable = [
        i for i in summary['all_items']
        if i['flag'] in ('RED', 'YELLOW') and i['variance'] > 1.0
    ]
    actionable.sort(key=lambda x: x['variance'], reverse=True)

    for rank, item in enumerate(actionable[:8], 1):
        icon = _flag_icon(item['flag'])
        print(f"  {rank}. {icon} [SBU-{item['sbu']}] {item['name']}")
        print(f"       Claimed=₹{item['claimed']:,.2f} Cr  "
              f"Allowable=₹{item['allowable']:,.2f} Cr  "
              f"Excess=₹{item['variance']:+,.2f} Cr")

    print()
    print("=" * WIDTH)


# =============================================================================
# STANDALONE ENTRY POINT (for testing)
# =============================================================================

if __name__ == '__main__':
    import json, sys

    if len(sys.argv) < 2:
        print("Usage: python ksebl_consolidated_summary.py <analysis_json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        results = json.load(f)

    summary = build_consolidated_summary(results)
    display_consolidated_summary(summary)
