"""
SBU-T Heuristics Runner
=======================
Runs all heuristics for the Transmission business unit.

Architecture:
  - Called by integration_pipeline.py after SBU-G analysis
  - Receives ch5 (Chapter 5 data already extracted by SBU-G parser)
  - Receives heuristic_fns dict of already-imported functions
  - Reuses same shared heuristic functions as SBU-G with SBU-T constants
  - Only 3 new heuristics: OM-TRANS-NORM-01, TRANS-COMP-01, TRANS-INCENT-01

Usage (from integration_pipeline.py):
    from data_mapper_sbu_t import run_sbu_t_heuristics
    sbu_t_results = run_sbu_t_heuristics(parsed_data_t, ch5, heuristic_fns, enricher)
"""

from typing import Dict, Optional


def run_sbu_t_heuristics(
    parsed_data_t: Dict,
    ch5: Dict,
    heuristic_fns: Dict,
    enricher=None,
) -> Dict:
    """
    Run all SBU-T heuristics.

    Args:
        parsed_data_t: output of SBUTPDFParser.extract_all()
        ch5:           chapter5_tables from SBU-G parser (already extracted, shared)
        heuristic_fns: dict with keys matching heuristic function names
                       e.g. {'IFC_LTL': heuristic_IFC_LTL_01, ...}
        enricher:      ContextEnricher instance from integration_pipeline

    Returns:
        dict of {line_item_key: heuristic_result}
    """
    from kserc_constants import (
        CURRENT_FY, GPF_INTEREST_RATE, GPF_OPENING_BALANCE, GPF_CLOSING_BALANCE,
        MT_BOND_TOTAL_COMPANY, SBI_EBLR_RATE, WEIGHTED_INFLATION_PCT,
        LOAN_OPENING_SBU_T, LOAN_ADDITIONS_SBU_T, LOAN_AVG_RATE_SBU_T,
        SBU_T_GPF_RATIO, SBU_T_MT_RATIO,
        OPENING_GFA_EXCL_LAND_SBU_T, MYT_APPROVED_OM_SBU_T,
        NTI_BASELINE_SBU_T,
        TRANS_AVAILABILITY_TARGET, TRANS_INCENTIVE_DEFERRAL_GAP,
        UNBRIDGED_REVENUE_GAP_2024_25,
        SBU_T_BASE_YEAR_NORMS,
        SBU_T_NORM_PER_BAY, SBU_T_NORM_PER_MVA, SBU_T_NORM_PER_CKTKM,
        EDAMON_KOCHI_DISBURSEMENTS, TRANS_COMP_AVG_INTEREST,
    )

    print("\n" + "="*70)
    print("SBU-T HEURISTIC ANALYSIS")
    print("="*70)

    results = {}
    arr    = parsed_data_t.get('arr_table', {}).get('rows', {})
    raw    = parsed_data_t.get('raw', {})
    mapped = parsed_data_t.get('mapped', {})

    def arr_tu(key):
        return (arr.get(key) or {}).get('tu_sought')

    def arr_appr(key):
        return (arr.get(key) or {}).get('approved')

    def m(key, fallback=None):
        v = mapped.get(key)
        return v if v is not None else fallback

    def enrich(result, context=None):
        if enricher:
            return enricher.enrich_result(result, context or {})
        return result

    # =========================================================================
    # ROE
    # =========================================================================
    print(f"\n Analyzing SBU-T roe...")
    claimed_roe  = m('roe_claimed') or arr_tu('roe') or 0
    approved_roe = m('roe_approved') or arr_appr('roe') or claimed_roe
    var_roe      = claimed_roe - approved_roe
    results['roe'] = enrich({
        'heuristic_id': 'ROE-01-T',
        'heuristic_name': 'Return on Equity (14%) — SBU-T',
        'line_item': 'Return on Equity',
        'claimed_value': claimed_roe,
        'allowable_value': round(approved_roe, 2),
        'variance_absolute': round(var_roe, 2),
        'variance_percentage': round(var_roe / approved_roe * 100 if approved_roe else 0, 2),
        'flag': 'GREEN' if abs(var_roe) < 0.5 else 'YELLOW',
        'recommended_amount': round(approved_roe, 2),
        'recommendation_text': (
            f'ROE matches MYT approved ₹{approved_roe:.2f} Cr. Approve as claimed.'
            if abs(var_roe) < 0.5 else
            f'ROE variance ₹{var_roe:+.2f} Cr — verify equity base.'
        ),
        'staff_review_status': 'Pending',
    })
    print(f"    Flag: {results['roe']['flag']} | Claimed: {claimed_roe:.2f} | "
          f"Approved: {approved_roe:.2f}")

    # =========================================================================
    # Depreciation
    # =========================================================================
    print(f"\n Analyzing SBU-T depreciation...")
    claimed_dep  = m('depreciation_claimed') or arr_tu('depreciation') or 0
    approved_dep = m('depreciation_approved') or arr_appr('depreciation') or 331.52
    var_dep      = claimed_dep - approved_dep
    results['depreciation'] = enrich({
        'heuristic_id': 'DEP-GEN-01-T',
        'heuristic_name': 'Depreciation (Normative) — SBU-T',
        'line_item': 'Depreciation',
        'claimed_value': claimed_dep,
        'allowable_value': round(approved_dep, 2),
        'variance_absolute': round(var_dep, 2),
        'variance_percentage': round(var_dep / approved_dep * 100 if approved_dep else 0, 2),
        'flag': 'GREEN' if abs(var_dep) < 1.0 else 'YELLOW',
        'recommended_amount': round(claimed_dep, 2),
        'recommendation_text': (
            f'Dep claimed ₹{claimed_dep:.2f} Cr vs MYT ₹{approved_dep:.2f} Cr. '
            f'Normative per regulation; verify Chapter 5 asset schedule.'
        ),
        'staff_review_status': 'Pending',
    })
    print(f"    Flag: {results['depreciation']['flag']} | "
          f"Claimed: {claimed_dep:.2f} | MYT Approved: {approved_dep:.2f}")

    # =========================================================================
    # IFC chain — same 4 functions, SBU-T constants
    # =========================================================================
    print(f"\n Analyzing SBU-T ifc (chain: LTL → WC → GPF → OTH)...")
    claimed_ltl = m('ifc_loan_claimed')  or arr_tu('ifc_loan')  or 0
    claimed_wc  = m('ifc_wc_claimed')   or arr_tu('ifc_wc')    or 0
    claimed_gpf = m('ifc_gpf_claimed')  or arr_tu('ifc_gpf')   or 0
    claimed_oth = m('ifc_other_claimed') or arr_tu('ifc_other') or 0

    try:
        ltl = heuristic_fns['IFC_LTL'](
            opening_normative_loan=LOAN_OPENING_SBU_T,
            gfa_additions=LOAN_ADDITIONS_SBU_T,
            depreciation=claimed_dep,
            opening_interest_rate=LOAN_AVG_RATE_SBU_T,
            claimed_interest=claimed_ltl,
        )
        wc = heuristic_fns['IFC_WC'](
            approved_om_expenses=MYT_APPROVED_OM_SBU_T,
            opening_gfa_excl_land=OPENING_GFA_EXCL_LAND_SBU_T,
            sbi_eblr_rate=SBI_EBLR_RATE,
            claimed_wc_interest=claimed_wc,
        )
        gpf = heuristic_fns['IFC_GPF'](
            opening_gpf_balance_company=GPF_OPENING_BALANCE.get(CURRENT_FY, 3364.32),
            closing_gpf_balance_company=GPF_CLOSING_BALANCE.get(CURRENT_FY, 3454.32),
            gpf_interest_rate=GPF_INTEREST_RATE,
            sbu_allocation_ratio=SBU_T_GPF_RATIO,
            claimed_gpf_interest_sbu=claimed_gpf,
        )
        oth = heuristic_fns['IFC_OTH'](
            claimed_gbi=0.0,
            claimed_bank_charges=claimed_oth,
        )
        ifc_allowable    = sum(filter(None, [
            ltl.get('allowable_value'), wc.get('allowable_value'),
            gpf.get('allowable_value'), oth.get('allowable_value'),
        ]))
        claimed_ifc_tot  = m('ifc_total_claimed') or arr_tu('ifc_total') or 0
        ifc_flags        = [r.get('flag') for r in [ltl, wc, gpf, oth]]
        ifc_flag         = ('RED' if 'RED' in ifc_flags else
                            'YELLOW' if 'YELLOW' in ifc_flags else 'GREEN')
        ifc_var          = claimed_ifc_tot - ifc_allowable
        results['ifc'] = {
            'status': 'complete', 'flag': ifc_flag,
            'claimed_value': claimed_ifc_tot,
            'allowable_value': round(ifc_allowable, 2),
            'variance_absolute': round(ifc_var, 2),
            'variance_percentage': round(ifc_var / ifc_allowable * 100
                                         if ifc_allowable else 0, 2),
            'primary_heuristic': enrich({
                'heuristic_id': 'IFC-CHAIN-T', 'flag': ifc_flag,
                'claimed_value': claimed_ifc_tot,
                'allowable_value': round(ifc_allowable, 2),
                'variance_absolute': round(ifc_var, 2),
                'recommendation_text': (
                    f'IFC claimed ₹{claimed_ifc_tot:.2f} Cr vs allowable '
                    f'₹{ifc_allowable:.2f} Cr.'
                ),
            }),
            'supporting': {
                'long_term_loan': ltl, 'working_capital': wc,
                'gpf': gpf, 'other_charges': oth,
            },
        }
        for label, r in [('LTL', ltl), ('WC', wc), ('GPF', gpf), ('OTH', oth)]:
            print(f"    IFC-{label}: flag={r.get('flag')} | "
                  f"allowable={r.get('allowable_value', 0):.2f} Cr")
        print(f"    IFC Total: flag={ifc_flag} | "
              f"claimed={claimed_ifc_tot:.2f} | allowable={ifc_allowable:.2f}")
    except Exception as e:
        print(f"    IFC error: {e}")
        import traceback; traceback.print_exc()
        results['ifc'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # Master Trust Bonds — SBU-T allocation ratio
    # =========================================================================
    print(f"\n Analyzing SBU-T master_trust...")
    claimed_mt  = m('ifc_master_trust_claimed') or arr_tu('ifc_master_trust') or 0
    total_bonds = MT_BOND_TOTAL_COMPANY.get(CURRENT_FY, 529.36)
    try:
        mt = heuristic_fns['MT_BOND'](
            total_bond_interest=total_bonds,
            sbu_allocation_ratio=SBU_T_MT_RATIO,
            claimed_bond_interest_sbu=claimed_mt,
        )
        results['master_trust'] = enrich(mt)
        print(f"    Flag: {mt.get('flag')} | Claimed: {claimed_mt:.2f} | "
              f"Allowable: {mt.get('allowable_value', 0):.2f} Cr")
    except Exception as e:
        print(f"    MT error: {e}")
        results['master_trust'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # NTI — SBU-T baseline from constants
    # =========================================================================
    print(f"\n Analyzing SBU-T nti...")
    claimed_nti = m('nti_claimed') or arr_tu('nti') or 0
    try:
        nti = heuristic_fns['NTI'](
            myt_baseline_nti=NTI_BASELINE_SBU_T.get(CURRENT_FY, 57.60),
            base_income_from_accounts=claimed_nti,
            claimed_nti=claimed_nti,
        )
        results['nti'] = enrich(nti)
        print(f"    Flag: {nti.get('flag')} | Claimed: {claimed_nti:.2f} | "
              f"Allowable: {nti.get('allowable_value', 0):.2f} Cr")
    except Exception as e:
        print(f"    NTI error: {e}")
        results['nti'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # Intangibles
    # =========================================================================
    print(f"\n Analyzing SBU-T intangibles...")
    # Row 14 = software intangibles amortization (1.32 Cr)
    # NOT T20 total (9.04) which is line compensation — already in edamon/pugalur heuristics
    claimed_intang = arr_tu('intangibles') or 0
    try:
        intang = heuristic_fns['INTANG'](
            software_amortization_claimed=claimed_intang,
            software_supporting_docs_provided=False,
            software_employees_additional_to_norms=False,
            total_claimed_amortization=claimed_intang,
        )
        results['intangibles'] = enrich(intang)
        print(f"    Flag: {intang.get('flag')} | Claimed: {claimed_intang:.2f} | "
              f"Allowable: {intang.get('allowable_value', 0):.2f} Cr")
    except Exception as e:
        print(f"    Intangibles error: {e}")
        results['intangibles'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # Exceptional Items
    # =========================================================================
    print(f"\n Analyzing SBU-T exceptional_items...")
    claimed_exc = m('exceptional_claimed') or arr_tu('exceptional_items') or 0
    try:
        exc = heuristic_fns['EXC'](
            claimed_calamity_rm=claimed_exc,
            claimed_govt_loss_takeover=0.0,
            separate_account_code=False,
            calamity_supporting_docs=False,
        )
        results['exceptional_items'] = enrich(exc)
        print(f"    Flag: {exc.get('flag')} | Claimed: {claimed_exc:.2f} Cr")
    except Exception as e:
        print(f"    Exceptional error: {e}")
        results['exceptional_items'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # O&M Transmission (SBU-T specific — OM-TRANS-NORM-01)
    # =========================================================================
    print(f"\n Analyzing SBU-T om_transmission (OM-TRANS-NORM-01)...")
    stats         = raw.get('transmission_statistics', {})
    cd            = raw.get('om_details', {}).get('cost_drivers', {})
    adds          = raw.get('additions', {})
    opening_bays  = cd.get('bays')  or stats.get('opening_bays')  or 2929
    opening_mva   = cd.get('mva')   or stats.get('opening_mva')   or 26373
    # T1/T5 captures only one voltage level (~1486 ckt-km) — wrong for O&M norms
    # T11 total across all voltages (66kV+) = 10800.96 ckt-km — this is the correct figure
    # cd.get('cktkm') would return T1/T5 value, so we hardcode T11 total here
    opening_cktkm = 10800.96
    added_bays    = adds.get('added_bays', 0)
    added_mva     = adds.get('added_mva', 0.0)
    added_cktkm   = 0.0   # T1/T5 closing figures — additions pending Chapter 5 verification
    claimed_om    = m('om_claimed') or arr_tu('om_expenses') or 659.03
    actual_om     = (arr.get('om_expenses') or {}).get('actual') or 591.93

    try:
        from Transmission_heuristics import heuristic_OM_TRANS_NORM_01
        om_t = heuristic_OM_TRANS_NORM_01(
            norm_per_bay=SBU_T_NORM_PER_BAY,
            norm_per_mva=SBU_T_NORM_PER_MVA,
            norm_per_cktkm=SBU_T_NORM_PER_CKTKM,
            opening_bays=int(opening_bays),
            opening_mva=float(opening_mva),
            opening_cktkm=float(opening_cktkm),
            added_bays=int(added_bays),
            added_mva=float(added_mva),
            added_cktkm=float(added_cktkm),
            myt_approved_om=MYT_APPROVED_OM_SBU_T,
            actual_om_accounts=actual_om,
            claimed_om=claimed_om,
            base_year_norms=SBU_T_BASE_YEAR_NORMS,
            escalation_2022_23=WEIGHTED_INFLATION_PCT['2022-23'] / 100,
            escalation_2023_24=WEIGHTED_INFLATION_PCT['2023-24'] / 100,
        )
        results['om_transmission'] = enrich(om_t)
        print(f"    Flag: {om_t.get('flag')} | Claimed: {claimed_om:.2f} | "
              f"Normative: {om_t.get('allowable_value', 0):.2f} Cr")
    except Exception as e:
        print(f"    OM-TRANS error: {e}")
        import traceback; traceback.print_exc()
        results['om_transmission'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # Compensation — Edamon-Kochi (TRANS-COMP-01)
    # =========================================================================
    print(f"\n Analyzing SBU-T edamon_kochi (TRANS-COMP-01)...")
    comp_raw    = raw.get('compensation', {})
    claimed_ek  = (comp_raw.get('edamon_kochi', {}).get('claimed')
                   or arr_tu('edamon_kochi_compensation') or 7.68)
    myt_appr_ek = arr_appr('edamon_kochi_compensation') or 19.02

    try:
        from Transmission_heuristics import heuristic_TRANS_COMP_01
        ek = heuristic_TRANS_COMP_01(
            line_name='Edamon-Kochi 400kV',
            compensation_entries=EDAMON_KOCHI_DISBURSEMENTS,
            avg_interest_rate=TRANS_COMP_AVG_INTEREST,
            claimed_compensation=claimed_ek,
            myt_approved=myt_appr_ek,
            assessment_year=CURRENT_FY,
        )
        results['edamon_kochi'] = enrich(ek)
        print(f"    Flag: {ek.get('flag')} | Claimed: {claimed_ek:.2f} | "
              f"Allowable: {ek.get('allowable_value', 0):.2f} Cr")
    except Exception as e:
        print(f"    Edamon-Kochi error: {e}")
        import traceback; traceback.print_exc()
        results['edamon_kochi'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # Compensation — Pugalur-Thrissur (TRANS-COMP-01)
    # =========================================================================
    print(f"\n Analyzing SBU-T pugalur_thrissur (TRANS-COMP-01)...")
    claimed_pt  = (comp_raw.get('pugalur_thrissur', {}).get('claimed')
                   or arr_tu('pugalur_thrissur_compensation') or 1.36)
    myt_appr_pt = arr_appr('pugalur_thrissur_compensation') or 0.0

    try:
        pt_disb = comp_raw.get('pugalur_thrissur', {}).get('disbursements') or [
            {'total_compensation_cr': 0.000602638,
             'year_of_disbursement': '2021-22',
             'kseb_share_50pct': 0.000301319,
             'amortization_period': 12},
        ]
        pt = heuristic_TRANS_COMP_01(
            line_name='Pugalur-Thrissur 320kV HVDC',
            compensation_entries=pt_disb,
            avg_interest_rate=TRANS_COMP_AVG_INTEREST,
            claimed_compensation=claimed_pt,
            myt_approved=myt_appr_pt,
            assessment_year=CURRENT_FY,
        )
        results['pugalur_thrissur'] = enrich(pt)
        print(f"    Flag: {pt.get('flag')} | Claimed: {claimed_pt:.2f} | "
              f"Allowable: {pt.get('allowable_value', 0):.2f} Cr")
    except Exception as e:
        print(f"    Pugalur-Thrissur error: {e}")
        results['pugalur_thrissur'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # Transmission Incentive (TRANS-INCENT-01)
    # =========================================================================
    print(f"\n Analyzing SBU-T transmission_incentive (TRANS-INCENT-01)...")
    incentive_raw   = raw.get('incentive', {})
    actual_avail    = incentive_raw.get('actual_availability')
    claimed_incent  = m('trans_incentive_claimed') or arr_tu('transmission_incentive') or 11.52
    arr_total_tu    = arr_tu('arr_total') or 1735.22
    arr_ex_incent   = arr_total_tu - claimed_incent

    try:
        from Transmission_heuristics import heuristic_TRANS_INCENT_01
        if actual_avail is None:
            print("      NOTE: actual_availability not extracted — "
                  "using 99.0% placeholder. KSERC staff must verify from SLDC cert.")
            actual_avail = 99.0
        incent = heuristic_TRANS_INCENT_01(
            target_availability=TRANS_AVAILABILITY_TARGET,
            actual_availability=actual_avail,
            sldc_certified=True,
            arr_excluding_incentive=arr_ex_incent,
            claimed_incentive=claimed_incent,
            unbridged_revenue_gap=UNBRIDGED_REVENUE_GAP_2024_25,
            revenue_gap_threshold=TRANS_INCENTIVE_DEFERRAL_GAP,
        )
        results['transmission_incentive'] = enrich(incent)
        print(f"    Flag: {incent.get('flag')} | Claimed: {claimed_incent:.2f} | "
              f"Allowable: {incent.get('allowable_value', 0):.2f} Cr")
    except Exception as e:
        print(f"    Trans Incentive error: {e}")
        import traceback; traceback.print_exc()
        results['transmission_incentive'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # Master Trust repayment + contribution (pass-through)
    # =========================================================================
    claimed_mt_repay = arr_tu('master_trust_repayment')    or 45.79
    claimed_mt_cont  = arr_tu('master_trust_contribution') or 44.98
    results['master_trust_repayment'] = {
        'heuristic_id': 'MT-REPAY-T', 'flag': 'GREY',
        'claimed_value': claimed_mt_repay + claimed_mt_cont,
        'recommendation_text': (
            'Master Trust repayment/contribution (₹'
            f'{claimed_mt_repay:.2f} + ₹{claimed_mt_cont:.2f} Cr) — '
            'actuary-determined. Approve pending actuarial verification.'
        ),
        'staff_review_status': 'Pending',
    }

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "─"*70)
    print("SBU-T HEURISTIC SUMMARY")
    print("─"*70)
    total_claimed = 0; total_allowable = 0; total_excess = 0
    sym = {'GREEN': '✅', 'YELLOW': '⚠️ ', 'RED': '🔴', 'GREY': '⬜'}
    for key, h in results.items():
        flag      = h.get('flag', '?')
        claimed   = h.get('claimed_value')   or 0
        allowable = h.get('allowable_value') or 0
        variance  = h.get('variance_absolute') or 0
        name      = h.get('heuristic_name', key)
        print(f"  {sym.get(flag,'?')} {name:<44} "
              f"Claimed={claimed:>8.2f}  Allowable={allowable:>8.2f}  "
              f"Var={variance:>+8.2f}")
        total_claimed   += claimed
        total_allowable += allowable
        total_excess    += max(0, variance)
    print(f"{'─'*70}")
    print(f"  {'TOTAL':<46} "
          f"Claimed={total_claimed:>8.2f}  Allowable={total_allowable:>8.2f}  "
          f"Excess={total_excess:>+8.2f}")
    print("─"*70)

    return results
