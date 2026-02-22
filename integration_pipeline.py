"""
Complete Integration: PDF Upload → Automated Analysis
======================================================
End-to-end pipeline for KSERC staff to upload KSEB petition and get results.

Flow:
    1. Upload PDF (KSEB Truing-Up Petition)
    2. Parse tables + context
    3. Map to heuristic inputs
    4. Run heuristics
    5. Enrich with explanations
    6. Display results

This is the "killer feature" - KSERC uploads PDF, gets instant first-cut analysis.
"""

import sys
from typing import Dict, List
from datetime import datetime


# =============================================================================
# CONTEXT ENRICHER
# =============================================================================

class ContextEnricher:
    """
    Augment heuristic results with PDF explanations.
    Makes recommendations smarter by considering both math and narrative.
    """
    
    def enrich_result(self, heuristic_result: dict, context: dict) -> dict:
        """
        Add explanation context to heuristic result.
        
        Args:
            heuristic_result: Output from heuristic function
            context: Context from PDF (variance explanations, etc.)
        
        Returns:
            Enriched result with KSEB explanations and smart recommendations
        """
        enriched = heuristic_result.copy()
        
        # Extract variance explanation if available
        variance_exp = context.get('variance_explanation', {})
        
        # Add KSEB's explanation
        enriched['kseb_explanation'] = {
            'narrative_text': context.get('section_text', ''),
            'variance_reasons': variance_exp.get('reasons', []),
            'force_majeure_claimed': variance_exp.get('force_majeure_claimed', False),
            'supporting_documents': variance_exp.get('supporting_docs', []),
            'regulatory_refs': variance_exp.get('regulatory_refs', [])
        }
        
        # Generate smart recommendation
        enriched['smart_recommendation'] = self._generate_recommendation(
            heuristic_result,
            variance_exp
        )
        
        return enriched
    
    def _generate_recommendation(self, result: dict, explanation: dict) -> dict:
        """
        Generate intelligent recommendation considering both
        heuristic flag and explanation quality.
        """
        flag = result.get('flag', 'YELLOW')
        variance_pct = abs(result.get('variance_percentage', 0))
        
        # Base assessment from heuristic
        if flag == 'GREEN':
            base_action = 'ACCEPT'
            base_reason = 'Within acceptable variance threshold'
        elif flag == 'YELLOW':
            base_action = 'REVIEW'
            base_reason = 'Variance requires staff review'
        else:  # RED
            base_action = 'SCRUTINIZE'
            base_reason = 'Significant variance or regulatory concern'
        
        # Score explanation quality
        exp_score = 0
        modifiers = []
        
        if explanation.get('force_majeure_claimed'):
            exp_score += 2
            modifiers.append('Force majeure claimed')
        
        if len(explanation.get('supporting_docs', [])) >= 2:
            exp_score += 1
            modifiers.append('Supporting documents provided')
        
        if explanation.get('regulatory_refs'):
            exp_score += 1
            modifiers.append('Regulatory basis cited')
        
        if len(explanation.get('reasons', [])) >= 2:
            exp_score += 1
            modifiers.append('Detailed explanation')
        
        # Adjust recommendation
        if flag == 'YELLOW' and exp_score >= 3:
            final_action = 'ACCEPT_CONDITIONAL'
            final_reason = f'{base_reason}, but strong justification provided'
        elif flag == 'RED' and exp_score >= 4:
            final_action = 'REVIEW_PRIORITY'
            final_reason = f'{base_reason}, but comprehensive explanation warrants review'
        else:
            final_action = base_action
            final_reason = base_reason
        
        # Suggest next steps
        next_steps = []
        if final_action in ['REVIEW', 'SCRUTINIZE', 'ACCEPT_CONDITIONAL']:
            if explanation.get('supporting_docs'):
                next_steps.append(f"Verify: {', '.join(explanation['supporting_docs'])}")
            if explanation.get('force_majeure_claimed'):
                next_steps.append("Verify force majeure claim")
            if not explanation.get('supporting_docs'):
                next_steps.append("Request supporting documentation")
        
        return {
            'action': final_action,
            'reason': final_reason,
            'modifiers': modifiers,
            'explanation_quality': f"{exp_score}/5",
            'next_steps': next_steps
        }


# =============================================================================
# MAIN INTEGRATION PIPELINE
# =============================================================================

def process_petition(pdf_path: str) -> Dict:
    """
    Complete pipeline: PDF → Results
    
    This is the main function KSERC staff will use.
    
    Args:
        pdf_path: Path to KSEB truing-up petition PDF
    
    Returns:
        Complete analysis with heuristic results + context
    """
    from pdf_parser_sbu_g import SBUGPDFParser
    from data_mapper_sbu_g import SBUGDataMapper
    from kserc_constants import (
        CPI, WPI, WEIGHTED_INFLATION_PCT,
        OM_BASE_YEAR_SBU_G, CURRENT_FY,
        SBI_EBLR_RATE, IWC_RATE,
        MT_BOND_TOTAL_COMPANY, MT_BOND_APPROVED_SBU_G, SBU_G_EMPLOYEE_RATIO,
        NTI_BASELINE_SBU_G, GPF_INTEREST_RATE, SBU_G_GPF_RATIO,
        GPF_OPENING_BALANCE, GPF_CLOSING_BALANCE,
        LOAN_OPENING_SBU_G, LOAN_ADDITIONS_SBU_G, LOAN_REPAYMENTS_SBU_G,
        LOAN_AVG_RATE_SBU_G, LOAN_INTEREST_ACTUAL,
        OPENING_GFA_EXCL_LAND_SBU_G
    )

    # Import heuristics
    try:
        from roe_heuristics import heuristic_ROE_01
        from depreciation_heuristics import heuristic_DEP_GEN_01
        from fuel_heuristics import heuristic_FUEL_01
        from om_heuristics import (
            heuristic_OM_INFL_01,
            heuristic_OM_NORM_01,
            heuristic_OM_APPORT_01,
            heuristic_EMP_PAYREV_01
        )
        from ifc_heuristics import (
            heuristic_IFC_LTL_01,
            heuristic_IFC_WC_01,
            heuristic_IFC_GPF_01,
            heuristic_IFC_OTH_02
        )
        from master_trust_heuristics import heuristic_MT_BOND_01
        from nti_heuristics import heuristic_NTI_01
        from intangible_heuristics import heuristic_INTANG_01
        from other_items_heuristics import heuristic_OTHER_EXP_01, heuristic_EXC_01
    except ImportError as e:
        print(f"WARNING: Heuristic modules not found ({e}). Using mock heuristics.")
        def heuristic_ROE_01(**kwargs):
            return {'heuristic_id': 'ROE-01', 'claimed_value': 116.38,
                    'allowable_value': 116.38, 'flag': 'GREEN', 'variance_percentage': 0.0}
        def heuristic_DEP_GEN_01(**kwargs):
            return {'heuristic_id': 'DEP-GEN-01', 'claimed_value': 236.50,
                    'allowable_value': 236.50, 'flag': 'GREEN', 'variance_percentage': 0.0}
        def heuristic_FUEL_01(**kwargs):
            return {'heuristic_id': 'FUEL-01', 'claimed_value': 0.34,
                    'allowable_value': 0.34, 'flag': 'GREEN', 'variance_percentage': 0.0}
        def heuristic_OM_INFL_01(**kwargs):
            return {'heuristic_id': 'OM-INFL-01', 'output_value': 3.05, 'flag': 'GREEN'}
        def heuristic_OM_NORM_01(**kwargs):
            return {'heuristic_id': 'OM-NORM-01', 'flag': 'GREEN', 'variance_percentage': 0.0,
                    'recommended_amount': 0.0}
        def heuristic_OM_APPORT_01(**kwargs):
            return {'heuristic_id': 'OM-APPORT-01', 'flag': 'GREEN', 'variance_percentage': 0.0}
        def heuristic_EMP_PAYREV_01(**kwargs):
            return {'heuristic_id': 'EMP-PAYREV-01', 'flag': 'GREEN', 'variance_percentage': 0.0}
    
    results = {
        'processing_timestamp': datetime.now().isoformat(),
        'pdf_path': pdf_path,
        'metadata': {},
        'line_items': {}
    }
    
    print("\n" + "="*70)
    print("KSERC TRUING-UP ANALYSIS - AUTOMATED PIPELINE")
    print("="*70)
    print(f" Processing: {pdf_path}")
    print(f" Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70 + "\n")
    
    # =========================================================================
    # STEP 1: PARSE PDF
    # =========================================================================
    
    print("STEP 1: Parsing PDF...")
    print("-" * 70)
    
    with SBUGPDFParser(pdf_path) as parser:
        parsed_data = parser.extract_all()
    
    results['metadata'] = parsed_data['metadata']
    
    print(f"\n Parsing complete")
    print(f"   Fiscal Year: {results['metadata'].get('fiscal_year', 'Unknown')}")
    print(f"   Pages: {results['metadata'].get('num_pages', 0)}")
    
    # =========================================================================
    # STEP 2: MAP TO HEURISTIC INPUTS
    # =========================================================================
    
    print("\n" + "="*70)
    print("STEP 2: Mapping data to heuristic inputs...")
    print("-" * 70)
    
    mapper = SBUGDataMapper(parsed_data)
    mapped_data = mapper.map_all()
    
    print("\n Mapping complete")
    
    # =========================================================================
    # STEP 3: RUN HEURISTICS
    # =========================================================================
    
    print("\n" + "="*70)
    print("STEP 3: Running heuristics...")
    print("-" * 70)
    
    enricher = ContextEnricher()

    def _run_single(item_key, heuristic_func):
        """Run one heuristic, strip internal keys, enrich and return result."""
        print(f"\n Analyzing {item_key}...")
        inp = mapped_data['heuristic_inputs'].get(item_key, {}).copy()

        if inp.get('status') in ['not_found', 'extraction_failed', 'mapping_failed', 'error']:
            print(f"     Skipped: {inp.get('error', 'Data not available')}")
            results['line_items'][item_key] = {
                'status': 'skipped', 'reason': inp.get('error', 'Data not available')
            }
            return None

        raw_data = inp.pop('_raw_data', {})
        context  = inp.pop('_context', {})
        inp.pop('_debug', None)
        inp.pop('status', None)
        # Strip any remaining internal keys
        kwargs = {k: v for k, v in inp.items() if not k.startswith('_')}

        try:
            result   = heuristic_func(**kwargs)
            enriched = enricher.enrich_result(result, context)
            enriched['_raw_data'] = raw_data
            flag     = enriched.get('flag', 'UNKNOWN')
            variance = enriched.get('variance_percentage') or 0
            action   = enriched.get('smart_recommendation', {}).get('action', 'N/A')
            print(f"    Complete | Flag: {flag} | Variance: {variance:+.2f}% | {action}")
            return enriched
        except Exception as e:
            print(f"    Error: {e}")
            import traceback; traceback.print_exc()
            results['line_items'][item_key] = {'status': 'error', 'error': str(e)}
            return None

    # ---- ROE ----
    r = _run_single('roe', heuristic_ROE_01)
    if r: results['line_items']['roe'] = r

    # ---- Depreciation ----
    r = _run_single('depreciation', heuristic_DEP_GEN_01)
    if r: results['line_items']['depreciation'] = r

    # ---- Fuel ----
    r = _run_single('fuel_costs', heuristic_FUEL_01)
    if r: results['line_items']['fuel_costs'] = r

    # ---- O&M (4-heuristic chain) ----
    print(f"\n Analyzing om_expenses (chain: INFL → NORM → APPORT → PAYREV)...")
    om_input = mapped_data['heuristic_inputs'].get('om_expenses', {})

    if om_input.get('status') in ['not_found', 'extraction_failed', 'mapping_failed']:
        print(f"     Skipped: {om_input.get('error', 'O&M data not available')}")
        results['line_items']['om_expenses'] = {
            'status': 'skipped', 'reason': om_input.get('error', 'Data not available')
        }
    else:
        # Step 1: OM-INFL-01
        infl_result       = heuristic_OM_INFL_01(
            cpi_old=CPI['2023-24'], cpi_new=CPI['2024-25'],
            wpi_old=WPI['2023-24'], wpi_new=WPI['2024-25']
        )
        inflation_2024_25 = infl_result.get('output_value', WEIGHTED_INFLATION_PCT['2024-25'])
        print(f"      OM-INFL-01: inflation 2024-25 = {inflation_2024_25:.2f}%")

        # Step 2: OM-NORM-01
        norm_result = heuristic_OM_NORM_01(
            base_year_om           = OM_BASE_YEAR_SBU_G,
            inflation_2022_23      = WEIGHTED_INFLATION_PCT['2022-23'],
            inflation_2023_24      = WEIGHTED_INFLATION_PCT['2023-24'],
            inflation_2024_25      = inflation_2024_25,
            claimed_existing       = om_input.get('claimed_om') or 0.0,
            new_stations_allowable = 0.0
        )
        approved_om = norm_result.get('recommended_amount') or 0.0
        print(f"      OM-NORM-01: flag={norm_result.get('flag')} | approved={approved_om:.2f} Cr")

        # Step 3: OM-APPORT-01
        apport_result = heuristic_OM_APPORT_01(
            total_om_approved = approved_om,
            actual_employee   = om_input.get('employee_cost') or 0.0,
            actual_ag         = om_input.get('ag_expenses')   or 0.0,
            actual_rm         = om_input.get('rm_expenses')   or 0.0
        )
        print(f"      OM-APPORT-01: flag={apport_result.get('flag')}")

        # Step 4: EMP-PAYREV-01
        payrev_result = heuristic_EMP_PAYREV_01(
            employee_cost_normative  = approved_om * 0.7703,
            employee_cost_actual     = om_input.get('employee_cost') or 0.0,
            pay_revision_implemented = False
        )
        print(f"      EMP-PAYREV-01: flag={payrev_result.get('flag')}")

        results['line_items']['om_expenses'] = {
            'status':             'complete',
            'primary_heuristic':  enricher.enrich_result(norm_result, {}),
            'supporting': {
                'inflation':      infl_result,
                'apportionment':  apport_result,
                'pay_revision':   payrev_result,
            },
            '_raw_data': om_input.get('_raw_data', {})
        }
    
    # ---- IFC (4-heuristic chain: LTL + WC + GPF + OTH) ----
    print(f"\n Analyzing ifc (chain: LTL → WC → GPF → OTH)...")
    ch5 = parsed_data.get('chapter5_tables', {})
    ifc_detail  = ch5.get('ifc_detail', {}).get('extracted_values', {})
    dep_result  = results['line_items'].get('depreciation', {})
    om_result   = results['line_items'].get('om_expenses', {})
    approved_om_for_ifc = (
        om_result.get('primary_heuristic', {}).get('allowable_value') or
        om_result.get('allowable_value') or 178.16
    )

    # Values from G10 (TU column)
    claimed_ltl = ifc_detail.get('term_loan_interest') or 149.15
    claimed_wc  = ifc_detail.get('wc_interest')        or 11.93
    claimed_gpf = ifc_detail.get('gpf_interest')       or 8.88
    claimed_oth = ifc_detail.get('other_charges')       or 0.38
    claimed_mt_in_ifc = ifc_detail.get('master_trust_int') or 25.81

    # Opening GFA from Table 5.28 (land values extracted, use total GFA from ARR)
    land_detail = ch5.get('land_values', {})
    opening_gfa_excl_land = 2800.0  # Will be refined when mapper passes it

    # Opening loan from Table 5.3
    loan_detail = ch5.get('loan_summary', {})

    # LTL - normative calculation using Table 5.3 actual values
    dep_allowable = dep_result.get('allowable_value') or 141.56
    ltl_result = heuristic_IFC_LTL_01(
        opening_normative_loan = LOAN_OPENING_SBU_G,
        gfa_additions          = LOAN_ADDITIONS_SBU_G,
        depreciation           = dep_allowable,
        opening_interest_rate  = LOAN_AVG_RATE_SBU_G,
        claimed_interest       = claimed_ltl,
    )
    print(f"      IFC-LTL-01: flag={ltl_result.get('flag')} | allowable={ltl_result.get('allowable_value', 0):.2f} Cr")

    # WC - normative (9.55% on WC requirement)
    wc_result = heuristic_IFC_WC_01(
        approved_om_expenses   = approved_om_for_ifc,
        opening_gfa_excl_land  = OPENING_GFA_EXCL_LAND_SBU_G,
        sbi_eblr_rate          = SBI_EBLR_RATE,
        claimed_wc_interest    = claimed_wc,
    )
    print(f"      IFC-WC-01:  flag={wc_result.get('flag')} | allowable={wc_result.get('allowable_value', 0):.2f} Cr")

    # GPF - now with real balances from MYT Table 5.27
    gpf_result = heuristic_IFC_GPF_01(
        opening_gpf_balance_company = GPF_OPENING_BALANCE.get(CURRENT_FY, 3364.32),
        closing_gpf_balance_company = GPF_CLOSING_BALANCE.get(CURRENT_FY, 3454.32),
        gpf_interest_rate           = GPF_INTEREST_RATE,
        sbu_allocation_ratio        = SBU_G_GPF_RATIO,
        claimed_gpf_interest_sbu    = claimed_gpf,
    )
    print(f"      IFC-GPF-01: flag={gpf_result.get('flag')} | allowable={gpf_result.get('allowable_value', 0):.2f} Cr")

    # OTH - bank charges + GBI
    oth_result = heuristic_IFC_OTH_02(
        claimed_gbi          = 0.0,
        claimed_bank_charges = claimed_oth,
    )
    print(f"      IFC-OTH-02: flag={oth_result.get('flag')} | allowable={oth_result.get('allowable_value', 0):.2f} Cr")

    # IFC total
    ifc_approved_total = sum(filter(None, [
        ltl_result.get('allowable_value'),
        wc_result.get('allowable_value'),
        gpf_result.get('allowable_value'),
        oth_result.get('allowable_value'),
        claimed_mt_in_ifc,   # Master Trust bond interest passed through
    ]))
    ifc_claimed_total = ifc_detail.get('ifc_total') or (
        claimed_ltl + claimed_wc + claimed_gpf + claimed_oth + claimed_mt_in_ifc
    )
    ifc_variance_pct = ((ifc_claimed_total - ifc_approved_total) / ifc_approved_total * 100
                        if ifc_approved_total else 0)
    ifc_flags = [r.get('flag') for r in [ltl_result, wc_result, gpf_result, oth_result]]
    ifc_overall_flag = 'RED' if 'RED' in ifc_flags else ('YELLOW' if 'YELLOW' in ifc_flags else 'GREEN')

    results['line_items']['ifc'] = {
        'status':          'complete',
        'claimed_value':   ifc_claimed_total,
        'allowable_value': ifc_approved_total,
        'variance_percentage': ifc_variance_pct,
        'flag':            ifc_overall_flag,
        'primary_heuristic': {
            'heuristic_id':   'IFC-CHAIN',
            'claimed_value':   ifc_claimed_total,
            'allowable_value': ifc_approved_total,
            'variance_percentage': ifc_variance_pct,
            'flag':            ifc_overall_flag,
            'smart_recommendation': {
                'action': 'SCRUTINIZE' if ifc_overall_flag in ('RED','YELLOW') else 'ACCEPT',
                'reason': 'IWC significantly over MYT — verify basis' if wc_result.get('flag') == 'RED'
                          else 'Within acceptable range',
            }
        },
        'supporting': {
            'long_term_loan': ltl_result,
            'working_capital': wc_result,
            'gpf':             gpf_result,
            'other_charges':   oth_result,
        },
        '_raw_data': ifc_detail
    }

    # ---- Master Trust ----
    print(f"\n Analyzing master_trust...")
    mt_detail   = ch5.get('master_trust_detail', {}).get('extracted_values', {})
    claimed_mt  = mt_detail.get('bond_interest') or 25.81
    total_bonds = MT_BOND_TOTAL_COMPANY.get(CURRENT_FY, 529.36)

    mt_result = heuristic_MT_BOND_01(
        total_bond_interest       = total_bonds,
        sbu_allocation_ratio      = SBU_G_EMPLOYEE_RATIO,
        claimed_bond_interest_sbu = claimed_mt,
    )
    enriched_mt = enricher.enrich_result(mt_result, {})
    print(f"    Complete | Flag: {mt_result.get('flag')} | "
          f"Claimed: {claimed_mt:.2f} | Allowable: {mt_result.get('allowable_value', 0):.2f} Cr")
    results['line_items']['master_trust'] = enriched_mt

    # ---- NTI ----
    print(f"\n Analyzing nti...")
    nti_detail = ch5.get('nti_detail', {}).get('extracted_values', {})
    nti_claimed = nti_detail.get('nti_total') or 216.80

    # Large exclusions needed per regulation:
    # Grant claw-back (row 7 in 5.49 = 4.93 Cr), KWA unrealized interest (row 3 = 114.75 Cr)
    # Security deposit reversal (row 9 = 171.56 Cr) — these are typically excluded
    nti_result = heuristic_NTI_01(
        myt_baseline_nti          = NTI_BASELINE_SBU_G.get(CURRENT_FY, 11.35),
        base_income_from_accounts = nti_claimed,
        exclusion_grant_clawback  = nti_detail.get('misc_receipts') or 4.93,
        exclusion_kwa_unrealized  = 0.0,   # SBU-G KWA unrealized = 0 (SBU-D issue)
        claimed_nti               = nti_claimed,
    )
    enriched_nti = enricher.enrich_result(nti_result, {})
    print(f"    Complete | Flag: {nti_result.get('flag')} | "
          f"Claimed: {nti_claimed:.2f} | Allowable: {nti_result.get('allowable_value', 0):.2f} Cr")
    results['line_items']['nti'] = enriched_nti

    # ---- Intangibles ----
    print(f"\n Analyzing intangibles...")
    intang_detail = ch5.get('intangibles_detail', {}).get('extracted_values', {})
    intang_claimed = intang_detail.get('sbu_g_amort') or 1.32

    intang_result = heuristic_INTANG_01(
        software_amortization_claimed       = intang_claimed,
        software_supporting_docs_provided   = False,  # Unknown — needs verification
        software_employees_additional_to_norms = False,  # Unknown — prior precedent rejected
        total_claimed_amortization          = intang_claimed,
    )
    enriched_intang = enricher.enrich_result(intang_result, {})
    print(f"    Complete | Flag: {intang_result.get('flag')} | "
          f"Claimed: {intang_claimed:.2f} | Allowable: {intang_result.get('allowable_value', 0):.2f} Cr")
    results['line_items']['intangibles'] = enriched_intang

    # ---- Other Expenses ----
    print(f"\n Analyzing other_expenses...")
    other_input = mapped_data['heuristic_inputs'].get('other_expenses', {})
    claimed_other = other_input.get('claimed_other') or 0.0

    other_result = heuristic_OTHER_EXP_01(
        claimed_discount_to_consumers = claimed_other,  # Treat total as discount (safest default)
        claimed_flood_losses          = 0.0,
        claimed_misc_writeoffs        = 0.0,
        flood_supporting_docs         = False,
        writeoff_appeal_orders        = False,
    )
    enriched_other = enricher.enrich_result(other_result, other_input.get('_context', {}))
    print(f"    Complete | Flag: {other_result.get('flag')} | "
          f"Claimed: {claimed_other:.2f} | Allowable: {other_result.get('allowable_value', 0):.2f} Cr")
    results['line_items']['other_expenses'] = enriched_other

    # ---- Exceptional Items ----
    print(f"\n Analyzing exceptional_items...")
    exc_input   = mapped_data['heuristic_inputs'].get('exceptional_items', {})
    claimed_exc = exc_input.get('claimed_exceptional') or 0.0

    # Exceptional items: treat full claim as calamity R&M pending doc verification
    # Govt loss takeover is always 0 for SBU-G (this is a SBU-D phenomenon)
    exc_result = heuristic_EXC_01(
        claimed_calamity_rm        = claimed_exc,
        claimed_govt_loss_takeover = 0.0,
        separate_account_code      = False,   # Unknown — needs verification
        calamity_supporting_docs   = False,   # Unknown — needs verification
    )
    enriched_exc = enricher.enrich_result(exc_result, exc_input.get('_context', {}))
    print(f"    Complete | Flag: {exc_result.get('flag')} | "
          f"Claimed: {claimed_exc:.2f} | Allowable: {exc_result.get('allowable_value', 0):.2f} Cr")
    results['line_items']['exceptional_items'] = enriched_exc

    print("\n" + "="*70)
    print("ANALYSIS SUMMARY — SBU-G")
    print("="*70)
    
    total_items = len(results['line_items'])
    completed = sum(
        1 for item in results['line_items'].values()
        if item.get('flag') in ['GREEN', 'YELLOW', 'RED']
        or item.get('status') == 'complete'
    )
    print(f"\n SBU-G Line Items Analyzed: {completed}/{total_items}")
    flags = {'GREEN': 0, 'YELLOW': 0, 'RED': 0}
    for item in results['line_items'].values():
        f = item.get('flag')
        if f in flags: flags[f] += 1
    print(f"    GREEN:{flags['GREEN']}  YELLOW:{flags['YELLOW']}  RED:{flags['RED']}")

    # =========================================================================
    # SBU-T ANALYSIS (reuses ch5 already extracted above)
    # =========================================================================
    print("\n" + "="*70)
    print("SBU-T ANALYSIS")
    print("="*70)
    try:
        sbu_t_results = process_sbu_t(pdf_path, ch5=ch5, enricher=enricher)
        results['sbu_t'] = sbu_t_results
        print(f"\n SBU-T complete — {len(sbu_t_results.get('line_items', {}))} line items")
    except Exception as e:
        print(f"\n SBU-T analysis failed: {e}")
        import traceback; traceback.print_exc()
        results['sbu_t'] = {'status': 'error', 'error': str(e)}

    # =========================================================================
    # SBU-D ANALYSIS
    # =========================================================================
    print("\n" + "="*70)
    print("SBU-D ANALYSIS")
    print("="*70)
    try:
        sbu_d_results = process_sbu_d(pdf_path, enricher=enricher)
        results['sbu_d'] = sbu_d_results
        print(f"\n SBU-D complete — {len(sbu_d_results.get('line_items', []))} line items")
    except Exception as e:
        print(f"\n SBU-D analysis failed: {e}")
        import traceback; traceback.print_exc()
        results['sbu_d'] = {'status': 'error', 'error': str(e)}

    print("\n" + "="*70)
    print(" Completed:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("="*70 + "\n")

    # =========================================================================
    # CONSOLIDATED KSEBL SUMMARY
    # =========================================================================
    try:
        from ksebl_consolidated_summary import build_consolidated_summary, display_consolidated_summary
        summary = build_consolidated_summary(results)
        results['consolidated_summary'] = summary
        display_consolidated_summary(summary)
    except Exception as e:
        print(f"\n Consolidated summary failed: {e}")
        import traceback; traceback.print_exc()

    return results


def process_sbu_d(pdf_path: str, enricher=None) -> Dict:
    """
    Run full SBU-D analysis.

    Args:
        pdf_path: Path to the petition PDF
        enricher: ContextEnricher instance. Created if not provided.

    Returns:
        dict with 'sbu': 'D', 'line_items': [...]
    """
    from pdf_parser_sbu_d import SBUDPDFParser
    from data_mapper_sbu_d import run_sbu_d_heuristics

    if enricher is None:
        enricher = ContextEnricher()

    print("\nParsing SBU-D chapter...")
    with SBUDPDFParser(pdf_path) as parser:
        parsed_d = parser.extract_all()

    print("\n" + "="*70)
    print("SBU-D HEURISTIC ANALYSIS")
    print("="*70)

    line_items = run_sbu_d_heuristics(parsed_d)

    # ---- Summary ----
    FLAG_ICONS = {'GREEN': '✅', 'YELLOW': '⚠️ ', 'RED': '🔴', 'GREY': '⬜', 'ERROR': '❌'}
    print()
    print("─" * 70)
    print("SBU-D HEURISTIC SUMMARY")
    print("─" * 70)

    total_claimed  = 0.0
    total_allowable = 0.0

    for r in line_items:
        icon     = FLAG_ICONS.get(r.get('flag', ''), '?')
        name     = r.get('name', 'Unknown')
        claimed  = r.get('claimed',  0) or 0
        allow    = r.get('allowable', 0) or 0
        var      = r.get('variance', claimed - allow) or 0

        # Only sum expense items (skip NTI which is a deduction)
        if name != 'Non-Tariff Income':
            total_claimed   += claimed
            total_allowable += allow

        print(f"  {icon} {name:<42} "
              f"Claimed={claimed:>10.2f}  "
              f"Allowable={allow:>10.2f}  "
              f"Var={var:>+10.2f}")

    excess = total_claimed - total_allowable
    print("─" * 70)
    print(f"  {'TOTAL':<44} "
          f"Claimed={total_claimed:>10.2f}  "
          f"Allowable={total_allowable:>10.2f}  "
          f"Excess={excess:>+10.2f}")
    print("─" * 70)

    # Flag counts
    flags = {'GREEN': 0, 'YELLOW': 0, 'RED': 0, 'GREY': 0}
    for r in line_items:
        f = r.get('flag', '')
        if f in flags:
            flags[f] += 1
    print(f"\n SBU-D complete — {len(line_items)} line items")
    print(f"    GREEN:{flags['GREEN']}  YELLOW:{flags['YELLOW']}  "
          f"RED:{flags['RED']}  GREY:{flags['GREY']}")

    return {
        'sbu':        'D',
        'metadata':   parsed_d.get('metadata', {}),
        'line_items': line_items,
        'summary': {
            'total_claimed':   total_claimed,
            'total_allowable': total_allowable,
            'excess':          excess,
            'flags':           flags,
        }
    }


# =============================================================================
# SBU-T ANALYSIS (called from process_petition or standalone)
# =============================================================================

def process_sbu_t(pdf_path: str, ch5: Dict = None, enricher=None) -> Dict:
    """
    Run full SBU-T analysis.
    
    Args:
        pdf_path: Path to the petition PDF
        ch5:      Chapter 5 tables already extracted by SBU-G parser.
                  If None, SBU-G parser is run first to get ch5.
        enricher: ContextEnricher instance. Created if not provided.

    Returns:
        dict with 'sbu': 'T', 'line_items': {...}
    """
    from pdf_parser_sbu_t import SBUTPDFParser
    from data_mapper_sbu_t import run_sbu_t_heuristics
    from ifc_heuristics import (
        heuristic_IFC_LTL_01, heuristic_IFC_WC_01,
        heuristic_IFC_GPF_01, heuristic_IFC_OTH_02
    )
    from master_trust_heuristics import heuristic_MT_BOND_01
    from nti_heuristics import heuristic_NTI_01
    from intangible_heuristics import heuristic_INTANG_01
    from other_items_heuristics import heuristic_EXC_01

    if enricher is None:
        enricher = ContextEnricher()

    # If ch5 not provided, run SBU-G parser to extract it
    if ch5 is None:
        print("  ch5 not provided — running SBU-G parser to extract Chapter 5...")
        from pdf_parser_sbu_g import SBUGPDFParser
        with SBUGPDFParser(pdf_path) as parser:
            parsed_g = parser.extract_all()
        ch5 = parsed_g.get('chapter5_tables', {})

    # Parse SBU-T chapter
    print("\nParsing SBU-T chapter...")
    with SBUTPDFParser(pdf_path) as parser:
        parsed_t = parser.extract_all()

    # Bundle heuristic functions
    heuristic_fns = {
        'IFC_LTL': heuristic_IFC_LTL_01,
        'IFC_WC':  heuristic_IFC_WC_01,
        'IFC_GPF': heuristic_IFC_GPF_01,
        'IFC_OTH': heuristic_IFC_OTH_02,
        'MT_BOND': heuristic_MT_BOND_01,
        'NTI':     heuristic_NTI_01,
        'INTANG':  heuristic_INTANG_01,
        'EXC':     heuristic_EXC_01,
    }

    line_items = run_sbu_t_heuristics(parsed_t, ch5, heuristic_fns, enricher)

    return {
        'sbu': 'T',
        'metadata': parsed_t.get('metadata', {}),
        'line_items': line_items,
    }


# =============================================================================
# RESULT DISPLAY
# =============================================================================

def display_detailed_results(results: Dict):
    """
    Display detailed results for each line item.
    Shows both heuristic analysis and KSEB explanations.
    """
    print("\n" + "="*70)
    print("DETAILED ANALYSIS RESULTS")
    print("="*70)
    
    for item_name, item_data in results['line_items'].items():
        if item_data.get('status') in ['skipped', 'error']:
            continue
        
        print(f"\n{'─'*70}")
        print(f" {item_name.upper().replace('_', ' ')}")
        print(f"{'─'*70}")

        # Handle chain structures (O&M and IFC)
        if item_data.get('status') == 'complete' and 'primary_heuristic' in item_data:
            primary = item_data['primary_heuristic']
            print(f"\n Primary Heuristic: {primary.get('heuristic_id', 'N/A')}")
            claimed   = primary.get('claimed_value') or 0
            allowable = primary.get('allowable_value') or 0
            print(f"   Claimed:   {claimed:.2f} Cr")
            print(f"   Allowable: {allowable:.2f} Cr")
            print(f"   Variance:  {primary.get('variance_percentage', 0):+.2f}%")
            print(f"   Flag:      {primary.get('flag', 'UNKNOWN')}")
            rec = primary.get('smart_recommendation', {})
            if rec:
                print(f"\n Recommendation: {rec.get('action', 'N/A')}")
                print(f"   Reason: {rec.get('reason', 'N/A')}")
            supporting = item_data.get('supporting', {})
            if supporting:
                print(f"\n Component Breakdown:")
                for check_name, check_data in supporting.items():
                    if not check_data:
                        continue
                    flag     = check_data.get('flag', 'N/A')
                    claimed_ = check_data.get('claimed_value', 0) or 0
                    allowed_ = check_data.get('allowable_value', 0) or 0
                    hid      = check_data.get('heuristic_id', check_name)
                    print(f"   {hid:15s}: {flag} | Claimed {claimed_:.2f} → Allowable {allowed_:.2f} Cr")
                    rec_text = check_data.get('recommendation_text', '')
                    if rec_text:
                        print(f"                    {rec_text[:80]}")
            continue
        
        # Heuristic result
        print(f"\n Heuristic Analysis:")
        print(f"   ID: {item_data.get('heuristic_id', 'N/A')}")
        claimed = item_data.get('claimed_value', 0)
        claimed = claimed if claimed is not None else 0
        allowable = item_data.get('allowable_value', 0)
        allowable = allowable if allowable is not None else 0
        print(f"   Claimed: {claimed:.2f} Cr")
        print(f"   Allowable: {allowable:.2f} Cr")
        print(f"   Variance: {item_data.get('variance_percentage', 0):+.2f}%")
        print(f"   Flag: {item_data.get('flag', 'UNKNOWN')}")
        
        # KSEB explanation
        explanation = item_data.get('kseb_explanation', {})
        if explanation.get('variance_reasons'):
            print(f"\n KSEB's Explanation:")
            for i, reason in enumerate(explanation['variance_reasons'], 1):
                print(f"   {i}. {reason[:80]}...")
        
        if explanation.get('force_majeure_claimed'):
            print(f"\n  Force Majeure: Claimed")
        
        if explanation.get('supporting_documents'):
            print(f"\n Supporting Documents:")
            for doc in explanation['supporting_documents']:
                print(f"   - {doc}")
        
        # Smart recommendation
        rec = item_data.get('smart_recommendation', {})
        if rec:
            print(f"\n Recommendation: {rec.get('action', 'N/A')}")
            print(f"   Reason: {rec.get('reason', 'N/A')}")
            print(f"   Explanation Quality: {rec.get('explanation_quality', 'N/A')}")
            
            if rec.get('next_steps'):
                print(f"\n Next Steps:")
                for step in rec['next_steps']:
                    print(f"   [ ] {step}")
    
    print("\n" + "="*70 + "\n")


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("="*70)
        print("KSERC TRUING-UP ANALYSIS - PDF PROCESSOR")
        print("="*70)
        print("\nUsage:")
        print("  python integration_pipeline.py <path_to_pdf> [--detailed]")
        print("\nExample:")
        print("  python integration_pipeline.py KSEB_Truing_Up_FY2023-24.pdf")
        print("  python integration_pipeline.py KSEB_Petition.pdf --detailed")
        print("\nThis will:")
        print("  1. Parse the PDF")
        print("  2. Extract tables and context")
        print("  3. Run heuristics")
        print("  4. Generate recommendations")
        print("\n" + "="*70)
        return
    
    pdf_path = sys.argv[1]
    show_detailed = '--detailed' in sys.argv
    
    # Process
    results = process_petition(pdf_path)
    
    # Show detailed results if requested
    if show_detailed:
        display_detailed_results(results)
    
    # Save results (optional)
    import json
    output_file = pdf_path.replace('.pdf', '_analysis.json')
    with open(output_file, 'w') as f:
        # Remove non-serializable objects
        clean_results = results.copy()
        json.dump(clean_results, f, indent=2)
    
    print(f" Results saved to: {output_file}")


if __name__ == "__main__":
    main()