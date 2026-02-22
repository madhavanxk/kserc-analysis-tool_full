"""
PDF Parser for SBU-D (Distribution) - KSERC Truing-Up Petitions
================================================================
Extracts tables from KSEB truing-up petitions for SBU-D chapter.
Chapter 4: Pages 52-177 of the 2024-25 petition.

Key differences from SBU-G/T:
- ARR table (D89) columns: Particulars | Approved | True up | Difference
  (NO "Actual" column — True up IS the claimed amount)
- Table prefix: D1-D89 with "D" prefix (some inconsistent: D60, D571)
- New line items: Power Purchase, T&D Loss gain, Revenue gap recovery,
  Solar registration refund, Liquidated damages
- Revenue side: Tariff income, Power factor incentive, External sale, NTI

ARR Table D89 row structure (from image):
  1.  Cost of Generation (SBU-G)           -- pass-through from SBU-G
  2.  Cost of Power Purchase incl RLDC     -- KEY item, ₹12,930.60 Cr
  3.  Cost of Intra-State Transmission     -- pass-through from SBU-T
  4.  Interest & Finance Charges           -- ₹1,881.33 Cr
  5.  Additional contribution Master Trust -- ₹333.42 Cr
  6.  Depreciation                         -- ₹342.75 Cr
  7.  Normative O&M Expenses               -- ₹4,013.29 Cr
  8.  Return on equity (14%)               -- ₹253.50 Cr
  9.  Sharing of gains T&D loss reduction  -- ₹131.85 Cr
  10. Recovery of past gap                 -- blank (not claimed)
  11. Amortisation of intangible assets    -- ₹10.58 Cr
  12. Repayment of Bonds                   -- ₹339.42 Cr
  13. Other Expenses                       -- ₹40.49 Cr
  14. Exceptional Items                    -- ₹18.24 Cr
  15. Registration charges solar refunded  -- ₹24.18 Cr
  16. Refund of liquidated damages         -- ₹16.30 Cr
  17. Total ARR                            -- ₹22,704.89 Cr
  Revenue side:
  18. Tariff Income incl fuel surcharge    -- ₹20,565.20 Cr
  19. Less Power factor incentive          -- ₹55.97 Cr
  20. Revenue from external sale           -- ₹296.71 Cr
  21. Non-Tariff Income                    -- ₹845.16 Cr
  22. Total ERC                            -- ₹21,651.10 Cr
  23. Net Revenue Gap/Surplus              -- -₹1,053.79 Cr

Usage:
    parser = SBUDPDFParser('KSERC_TruingUp_2024-25_KSEB.pdf')
    results = parser.extract_all()
"""

import re
import pdfplumber
from typing import Dict, List, Optional, Tuple


# =============================================================================
# MAIN PARSER CLASS
# =============================================================================

class SBUDPDFParser:
    """
    Parse KSERC truing-up petitions for SBU-D data.
    Operates on pages 52-177 of the petition.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf = pdfplumber.open(pdf_path)
        self.num_pages = len(self.pdf.pages)

        self.metadata = {
            'fiscal_year': None,
            'sbu': 'D',
            'document_type': None,
            'num_pages': self.num_pages
        }

        self._d_start = None
        self._d_end = None

        self._detect_metadata()
        self._detect_sbu_d_boundaries()

    # =========================================================================
    # METADATA + BOUNDARY DETECTION
    # =========================================================================

    def _detect_metadata(self):
        text = ""
        for p in self.pdf.pages[:5]:
            text += p.extract_text() or ""
        fy = re.findall(r'(20\d{2})-(\d{2})', text)
        if fy:
            self.metadata['fiscal_year'] = f"{fy[0][0]}-{fy[0][1]}"
        if 'petition' in text.lower():
            self.metadata['document_type'] = 'Petition'

    def _detect_sbu_d_boundaries(self):
        """Find SBU-D chapter start and end pages (0-indexed)"""
        d_start = None
        d_end = None

        def _is_toc_page(text: str) -> bool:
            t = text.lower()
            if 'table of contents' in t or 'contents' in t[:200]:
                return True
            # TOC pages have dense dotted leaders
            if t.count('....') > 5 or t.count('…') > 5:
                return True
            # TOC pages have many short lines ending in page numbers
            lines = [l.strip() for l in t.splitlines() if l.strip()]
            if len(lines) > 5:
                num_ending_digits = sum(
                    1 for l in lines if re.search(r'\d{1,3}\s*$', l)
                )
                if num_ending_digits / len(lines) > 0.5:
                    return True
            return False

        # SBU-D cannot start before page 50 (TOC and SBU-G/T precede it)
        MIN_START_PAGE = 49   # 0-indexed → page 50+

        for i, page in enumerate(self.pdf.pages):
            if i < MIN_START_PAGE:
                continue

            text = page.extract_text() or ''
            tl = text.lower()

            if _is_toc_page(text):
                continue

            # SBU-D starts at Chapter 4 / Distribution heading
            if d_start is None:
                if (re.search(r'chapter[\s\-–]*4', tl) or
                    re.search(r'sbu[\s\-–]*[\-–]?\s*d\b', tl) or
                    re.search(r'truing.{0,10}up.*distribution', tl) or
                    re.search(r'distribution\s+business\s+unit', tl)):
                    d_start = i

            # SBU-D ends at Chapter 5 — require strong signal, not false match
            elif d_end is None:
                if (re.search(r'chapter[\s\-–]*5\b', tl) and
                    re.search(r'common\s+items|chapter\s*5.*common|'
                              r'employee.*strength|staff.*strength', tl)):
                    # Also require we're past page 130 (D89 is on page 134)
                    if i > 129:
                        d_end = i - 1
                        break

        # Fallback to known boundaries for 2024-25 petition
        if d_start is None:
            d_start = 51   # page 52 (0-indexed)
        if d_end is None:
            d_end = 176    # page 177 (0-indexed)

        self._d_start = d_start
        self._d_end = d_end
        print(f"   SBU-D starts at page {d_start + 1}")
        print(f"   SBU-D ends at page {d_end + 1}")
        print(f"   SBU-D boundary: pages {d_start + 1} to {d_end + 1}")

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def _clean_value(self, val) -> Optional[float]:
        """Convert cell text to float, return None if not parseable"""
        if val is None:
            return None
        s = str(val).strip()
        s = re.sub(r'[₹,\s]', '', s)
        s = re.sub(r'\(([0-9.]+)\)', r'-\1', s)
        if re.match(r'^\d{1,2}$', s) and len(s) <= 2:
            return None
        try:
            return float(s)
        except (ValueError, TypeError):
            return None

    def _clean_table(self, raw_table: List) -> List[List[str]]:
        cleaned = []
        for row in raw_table:
            if row is None:
                continue
            cleaned_row = [str(c).strip() if c is not None else '' for c in row]
            if any(c for c in cleaned_row):
                cleaned.append(cleaned_row)
        return cleaned

    def _find_table_in_range(
        self,
        patterns: List[str],
        start: int,
        end: int,
        multi_page: bool = False,
        max_extra_pages: int = 3
    ) -> Optional[List[List[str]]]:
        """
        Find table matching any pattern within page range.
        multi_page: continue collecting table rows from subsequent pages.
        max_extra_pages: how many additional pages to scan for continuation.
        """
        for page_num in range(start, min(end + 1, self.num_pages)):
            page = self.pdf.pages[page_num]
            text = page.extract_text() or ''

            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    tables = page.extract_tables()
                    if not tables:
                        continue

                    combined = []
                    for tbl in tables:
                        cleaned = self._clean_table(tbl)
                        if cleaned:
                            combined.extend(cleaned)

                    if multi_page:
                        for extra in range(1, max_extra_pages + 1):
                            np = page_num + extra
                            if np > end or np >= self.num_pages:
                                break
                            next_text = self.pdf.pages[np].extract_text() or ''
                            # Stop if next page has a new table heading
                            if re.search(
                                r'TABLE\s*[–\-]?\s*D\d+|Chapter\s*[–\-]?\s*\d',
                                next_text, re.IGNORECASE
                            ):
                                break
                            next_tables = self.pdf.pages[np].extract_tables()
                            if not next_tables:
                                break
                            for tbl in next_tables:
                                nd = self._clean_table(tbl)
                                if nd:
                                    first_row = nd[0]
                                    is_continuation = not any(
                                        re.search(
                                            r'table|particulars|sl\.?\s*no',
                                            str(c), re.IGNORECASE
                                        )
                                        for c in first_row if c
                                    )
                                    if is_continuation:
                                        combined.extend(nd)
                                        print(f"      Table continues on page {np + 1}")

                    if combined:
                        print(f"      Found table on page {page_num + 1}")
                        print(f"      Total rows extracted: {len(combined)}")
                        return combined

        return None

    def _nums_from_row(self, row: List[str]) -> List[float]:
        """Extract all valid numeric values from a row (skip col 0)"""
        return [
            v for i, c in enumerate(row)
            if i > 0 and (v := self._clean_value(c)) is not None
        ]

    # =========================================================================
    # ARR TABLE (D89) — MAIN EXTRACTION
    # =========================================================================

    def extract_arr_d89(self) -> Dict:
        """
        Extract Table D89: ARR & ERC of Distribution Business Unit.
        Columns: Particulars | Approved | True up | Difference
        Note: 'True up' = claimed amount (no separate 'Actual' column)
        """
        print("   Extracting Table D89: ARR (SBU-D)...")

        result = {
            'found': False,
            'rows': {},
            'arr_total': {'approved': None, 'tu': None},
            'erc_total': {'approved': None, 'tu': None},
            'revenue_gap': {'approved': None, 'tu': None},
        }

        # Row keyword → internal key mapping
        # IMPORTANT: 'non-tariff income' must appear BEFORE 'tariff income'
        # to prevent substring match ('tariff income' matches inside 'non-tariff income')
        ROW_KEYS = {
            'cost of generation':                    'cost_generation_sbu_g',
            'cost of power purchase':                'power_purchase',
            'cost of intra-state transmission':      'cost_transmission_sbu_t',
            'intra-state transmission':              'cost_transmission_sbu_t',
            'interest & finance':                    'ifc',
            'interest and finance':                  'ifc',
            'additional contribution to master':     'master_trust',
            'repayment of bonds':                    'bond_repayment',
            'depreciation':                          'depreciation',
            'normative o&m':                         'om_expenses',
            'return on equity':                      'roe',
            'sharing of gains':                      'td_loss_gain',
            't&d loss reduction':                    'td_loss_gain',
            'recovery of past gap':                  'past_gap_recovery',
            'amortisation of intangible':            'intangibles',
            'amortization of intangible':            'intangibles',
            'other expenses':                        'other_expenses',
            'exceptional items':                     'exceptional_items',
            'registration charges for solar':        'solar_registration_refund',
            'refund of liquidated damages':          'liquidated_damages',
            'total arr':                             'arr_total',
            # 'non-tariff income' MUST come before 'tariff income'
            'non-tariff income':                     'nti',
            'less power factor':                     'power_factor_incentive',
            'revenue from external sale':            'external_sale_revenue',
            'tariff income':                         'tariff_income',
            'total erc':                             'erc_total',
            'net revenue gap':                       'revenue_gap',
        }

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*89', r'TABLE\s*[–\-]?\s*D89',
             r'ARR\s*&\s*ERC.*DISTRIBUTION',
             r'ARR.*ERC.*DISTRIBUTION\s+BUSINESS'],
            self._d_start, self._d_end,
            multi_page=True
        )

        if not raw:
            print("      D89 not found — trying page range scan...")
            # Try last 15 pages of SBU-D section
            raw = self._find_table_in_range(
                [r'Total\s+ARR', r'Total\s+ERC', r'Revenue\s+Gap'],
                max(self._d_end - 15, self._d_start), self._d_end,
                multi_page=True
            )

        if not raw:
            print("      D89 extraction failed")
            return result

        result['found'] = True

        # Detect column indices: Approved=col1, True up=col2, Difference=col3
        col_approved = 1
        col_tu       = 2

        for row in raw:
            if not row:
                continue
            # D89: col 0 is always '' (border), description is in col 1
            # Try col 1 first, fall back to col 0
            row_text = ''
            for cell in row[:3]:
                if cell and cell.strip():
                    row_text = cell.lower().strip()
                    break
            if not row_text:
                continue

            for keyword, key in ROW_KEYS.items():
                if keyword in row_text:
                    nums = self._nums_from_row(row)
                    approved = nums[0] if len(nums) >= 1 else None
                    tu       = nums[1] if len(nums) >= 2 else None

                    result['rows'][key] = {
                        'approved': approved,
                        'tu':       tu,
                        'diff':     nums[2] if len(nums) >= 3 else None,
                    }
                    print(f"      {key}: Approved={approved} TU={tu}")
                    break

        # Convenience references
        for key in ['arr_total', 'erc_total', 'revenue_gap']:
            if key in result['rows']:
                result[key] = result['rows'][key]

        return result

    # =========================================================================
    # T&D LOSSES (D9, D10, D12)
    # =========================================================================

    def extract_td_losses(self) -> Dict:
        """
        Extract T&D loss data from Tables D9, D10, D12.
        D9: T&D loss for the year (MU)
        D10: Distribution losses
        D12: Gain attributable to KSEBL on T&D loss over-achievement
        """
        print("   Extracting T&D loss tables (D9, D10, D12)...")

        result = {
            'approved_loss_pct':  None,
            'actual_loss_pct':    None,
            'energy_input_mu':    None,
            'energy_sold_mu':     None,
            'td_loss_gain_cr':    None,
            'found': False,
        }

        # D10: Distribution losses — has approved vs actual loss %
        raw_d10 = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*10', r'TABLE\s*[–\-]?\s*D10',
             r'[Dd]istribution\s+losses'],
            self._d_start, self._d_start + 20
        )

        if raw_d10:
            result['found'] = True
            for row in raw_d10:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                if 'approved' in row_text and 'loss' in row_text and nums:
                    result['approved_loss_pct'] = nums[-1]
                elif 'actual' in row_text and 'loss' in row_text and nums:
                    result['actual_loss_pct'] = nums[-1]
                elif ('t&d' in row_text or 'loss' in row_text) and len(nums) >= 2:
                    # Row with approved then actual
                    if result['approved_loss_pct'] is None:
                        result['approved_loss_pct'] = nums[0]
                    if result['actual_loss_pct'] is None:
                        result['actual_loss_pct'] = nums[-1]

        # D12: Gain on T&D loss reduction
        raw_d12 = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*12', r'TABLE\s*[–\-]?\s*D12',
             r'[Gg]ain\s+attributable.*KSEBL',
             r'[Tt]&[Dd]\s+loss\s+reduction.*gain'],
            self._d_start, self._d_start + 20
        )

        if raw_d12:
            for row in raw_d12:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                if ('total' in row_text or 'gain' in row_text) and nums:
                    result['td_loss_gain_cr'] = nums[-1]
                    break

        print(f"      Approved loss%={result['approved_loss_pct']} "
              f"Actual loss%={result['actual_loss_pct']} "
              f"Gain={result['td_loss_gain_cr']} Cr")
        return result

    # =========================================================================
    # POWER PURCHASE (D68 — sourcewise summary)
    # =========================================================================

    def extract_power_purchase(self) -> Dict:
        """
        Extract Table D68: Sourcewise power purchase cost.
        This is the summary table — individual source tables (D16-D67) too granular.
        Also captures total from D89 Row 2 as cross-check.
        """
        print("   Extracting power purchase (D68 sourcewise)...")

        result = {
            'total_claimed_cr':   None,
            'total_approved_cr':  None,
            'sources': {},
            'found': False,
        }

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*68', r'TABLE\s*[–\-]?\s*D68',
             r'[Ss]ource\s*wise\s+power\s+purchase\s+cost',
             r'[Ss]ourcewise\s+power\s+purchase'],
            self._d_start + 60, self._d_end,
            multi_page=True
        )

        if not raw:
            print("      D68 not found")
            return result

        result['found'] = True

        SOURCE_KEYS = {
            'cgs':                              'cgs',
            'central generating':               'cgs',
            'maithon':                          'maithon_dvc',
            'dvc':                              'maithon_dvc',
            'dbfoo':                            'dbfoo',
            'medium term':                      'medium_term',
            're purchase':                      're_purchase',
            'renewable energy':                 're_purchase',
            'power purchase through short':     'short_term',
            'short term':                       'short_term',
            'rgccpp':                           'rgccpp',
            'kayamkulam':                       'rgccpp',
            # exchange sub-rows — all aggregated into 'exchange'
            'iex':                              'exchange',
            'pxil':                             'exchange',
            'power exchange':                   'exchange',
            'exchange':                         'exchange',
            # ISTS — multiple keyword forms
            'inter state transmission':         'ists',
            'inter-state transmission':         'ists',
            'intra state transmission':         'ists',
            'transmission charges':             'ists',
            'ists':                             'ists',
            'pgcil':                            'ists',
            'ctc':                              'ists',
            'swap':                             'swap',
            'banking':                          'swap',
            'deviation':                        'dsm',
            'dsm':                              'dsm',
            'other charges in connection':      'other',
            'grid connected average':           'solar',
            'solar energy':                     'solar',
            'total power purchase':             'total',
        }

        # Accumulator — sum quantum and cost for sources with multiple rows
        accumulator: Dict[str, Dict] = {}

        # Sources that have no MU column (cost-only pass-throughs)
        NO_MU_SOURCES = {'ists', 'rgccpp', 'other'}

        for row in raw:
            if not row:
                continue
            # D68: col 0 = serial no, col 3 = source name
            row_text = ''
            for cell in [row[3] if len(row) > 3 else '', row[0] if row else '']:
                if cell and cell.strip() and not re.match(r'^\d{1,2}$', cell.strip()):
                    row_text = cell.lower().strip()
                    break
            if not row_text:
                continue

            nums = self._nums_from_row(row)
            for kw, key in SOURCE_KEYS.items():
                if kw in row_text:
                    if key == 'total':
                        if nums:
                            result['total_claimed_cr'] = nums[-1]
                        break

                    # For sources with no MU: nums[0]=cost, nums[1]=N/A
                    # For sources with MU:    nums[0]=quantum, nums[1]=cost
                    if key in NO_MU_SOURCES or len(nums) == 1:
                        quantum = None
                        cost    = nums[0] if nums else None
                    else:
                        quantum = nums[0] if len(nums) >= 1 else None
                        cost    = nums[1] if len(nums) >= 2 else None

                    if key not in accumulator:
                        accumulator[key] = {'quantum_mu': 0.0, 'claimed': 0.0}
                    if quantum is not None:
                        accumulator[key]['quantum_mu'] = (
                            (accumulator[key]['quantum_mu'] or 0) + quantum
                        )
                    if cost is not None:
                        accumulator[key]['claimed'] = (
                            (accumulator[key]['claimed'] or 0) + cost
                        )
                    break

        # Write aggregated results to sources dict
        for key, data in accumulator.items():
            result['sources'][key] = {
                'quantum_mu': data['quantum_mu'] if data['quantum_mu'] != 0 else None,
                'claimed':    data['claimed'],
            }

        print(f"      Total PP approved={result['total_approved_cr']} "
              f"claimed={result['total_claimed_cr']} Cr")
        return result

    # =========================================================================
    # O&M EXPENSES (D69-D76)
    # =========================================================================

    def extract_om_details(self) -> Dict:
        """
        Extract O&M details from Tables D69-D76.
        D69:  Cost drivers (consumers, lines, substations)
        D70:  Normative employee + A&G expenses
        D571: Escalation rates (same as SBU-G)
        D73:  Normative employee + A&G 2024-25
        D74:  Normative R&M expenses
        D75:  Components of O&M for SBU-D
        D76:  Normative O&M 2024-25 total
        """
        print("   Extracting O&M details (D69-D76)...")

        result = {
            'cost_drivers': {},
            'normative_om_cr':     None,
            'claimed_om_cr':       None,
            'employee_cost_cr':    None,
            'rm_expenses_cr':      None,
            'ag_expenses_cr':      None,
            'found': False,
        }

        # D69: Cost drivers — consumers, line length, substations
        raw_d69 = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*69', r'TABLE\s*[–\-]?\s*D69',
             r'[Cc]ost\s+drivers.*O.*M',
             r'[Cc]onsumers.*[Ll]ines.*[Ss]ubstation'],
            self._d_start + 65, self._d_start + 80
        )

        if raw_d69:
            result['found'] = True
            DRIVER_KEYS = {
                'consumer':        'consumers',
                'line':            'line_length_km',
                'substation':      'substations',
                'distribution':    'dist_transformers',
                'transformer':     'dist_transformers',
            }
            for row in raw_d69:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                for kw, key in DRIVER_KEYS.items():
                    if kw in row_text and nums:
                        result['cost_drivers'][key] = nums[-1]
                        break

        # D75: Components of O&M for SBU-D
        raw_d75 = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*75', r'TABLE\s*[–\-]?\s*D75',
             r'[Cc]omponents\s+of\s+O.*M.*SBU.*D',
             r'[Cc]omponents\s+of\s+O.*M.*[Dd]istribution'],
            self._d_start + 65, self._d_start + 85
        )

        if raw_d75:
            result['found'] = True
            for row in raw_d75:
                if not row:
                    continue
                # D75: col 0=serial, col 3=description, col 6=normative(=TU claim)
                row_text = ''
                for cell in [row[3] if len(row) > 3 else '',
                             row[1] if len(row) > 1 else '']:
                    if cell and cell.strip() and not re.match(r'^\d{1,2}$', cell.strip()):
                        row_text = cell.lower().strip()
                        break
                if not row_text:
                    continue
                nums = self._nums_from_row(row)
                if not nums:
                    continue
                if 'employee' in row_text:
                    # nums: approved, accounts, normative, TU claim, variation
                    result['employee_cost_cr'] = nums[2] if len(nums) >= 3 else nums[-1]
                elif 'r&m' in row_text or 'repair' in row_text:
                    result['rm_expenses_cr'] = nums[2] if len(nums) >= 3 else nums[-1]
                elif 'total' in row_text:
                    result['claimed_om_cr'] = nums[2] if len(nums) >= 3 else nums[-1]

        # D76: Normative O&M total
        raw_d76 = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*76', r'TABLE\s*[–\-]?\s*D76',
             r'[Nn]ormative\s+O.*M.*2024'],
            self._d_start + 65, self._d_start + 85
        )

        if raw_d76:
            for row in raw_d76:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                if 'total' in row_text and nums:
                    result['normative_om_cr'] = nums[-1]
                    break

        print(f"      Normative={result['normative_om_cr']} "
              f"Claimed={result['claimed_om_cr']} "
              f"Employee={result['employee_cost_cr']} Cr")
        return result

    # =========================================================================
    # IFC DETAILS (D77-D83)
    # =========================================================================

    def extract_ifc_details(self) -> Dict:
        """
        Extract IFC details from Tables D77-D83.
        D77: Comparison of IFC 2024-25
        D79: Parameters for WC estimation
        D80: Interest on working capital
        D81: Carrying cost on approved revenue gap
        D82: Other charges under IFC
        D83: Details of IFC for FY 2024-25 (summary)
        """
        print("   Extracting IFC details (D77-D83)...")

        result = {
            'ifc_total':          None,
            'ifc_approved':       None,
            'term_loan_interest': None,
            'wc_interest':        None,
            'gpf_interest':       None,
            'other_charges':      None,
            'carrying_cost':      None,
            'master_trust_int':   None,
            'found': False,
        }

        # D83: Summary table — most reliable
        raw_d83 = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*83', r'TABLE\s*[–\-]?\s*D83',
             r'[Dd]etails\s+of\s+[Ii]nterest\s+and\s+[Ff]inance\s+[Cc]harges.*2024',
             r'[Dd]etails\s+of\s+IFC.*2024'],
            self._d_start + 70, self._d_end,
            multi_page=True
        )

        if raw_d83:
            result['found'] = True
            components = []
            for row in raw_d83:
                if not row:
                    continue
                # D83: col 1=description, cols: Approved|Accounts|TU Sought|Difference
                row_text = ''
                for cell in [row[1] if len(row) > 1 else '',
                             row[0] if row else '']:
                    if cell and cell.strip() and not re.match(r'^\d{1,2}$', cell.strip()):
                        row_text = cell.lower().strip()
                        break
                if not row_text:
                    continue
                nums = self._nums_from_row(row)
                if not nums:
                    continue
                # nums pattern: [approved, accounts, tu_sought, difference]
                tu = nums[2] if len(nums) >= 3 else nums[-1]

                if 'outstanding loan' in row_text or 'net interest' in row_text:
                    result['term_loan_interest'] = tu
                    components.append(tu)
                elif 'security deposit' in row_text:
                    result['wc_interest'] = tu  # security deposit treated as quasi-WC
                    components.append(tu)
                elif 'gpf' in row_text or 'provident fund' in row_text:
                    result['gpf_interest'] = tu
                    components.append(tu)
                elif 'other interest' in row_text or 'other charges' in row_text:
                    result['other_charges'] = tu
                    components.append(tu)
                elif 'master trust bond' in row_text:
                    result['master_trust_int'] = tu
                    components.append(tu)
                elif 'carrying cost' in row_text or 'revenue gap' in row_text:
                    result['carrying_cost'] = tu
                    components.append(tu)

            # Compute total from components if no explicit total row
            if components:
                result['ifc_total'] = round(sum(components), 2)

        # D77: IFC comparison — get approved total
        raw_d77 = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*77', r'TABLE\s*[–\-]?\s*D77',
             r'[Cc]omparison.*I.*FC.*2024'],
            self._d_start + 70, self._d_end
        )

        if raw_d77:
            for row in raw_d77:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                if 'total' in row_text and nums:
                    result['ifc_approved'] = nums[0]
                    if result['ifc_total'] is None:
                        result['ifc_total'] = nums[-1]
                    break

        print(f"      IFC total={result['ifc_total']} "
              f"approved={result['ifc_approved']} "
              f"LTL={result['term_loan_interest']} "
              f"WC={result['wc_interest']} Cr")
        return result

    # =========================================================================
    # DEPRECIATION (D78)
    # =========================================================================

    def extract_depreciation(self) -> Dict:
        """Extract D78: Details of Capital Works / Depreciation 2024-25"""
        print("   Extracting Depreciation (D78)...")

        result = {'claimed': None, 'approved': None, 'found': False}

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*78', r'TABLE\s*[–\-]?\s*D78',
             r'[Dd]etails\s+of\s+[Cc]apital\s+[Ww]orks',
             r'[Nn]ormative\s+[Dd]epreciation.*[Dd]istribution'],
            self._d_start + 70, self._d_end
        )

        if raw:
            result['found'] = True
            for row in raw:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                if 'total' in row_text and nums:
                    result['approved'] = nums[0] if len(nums) >= 2 else None
                    result['claimed']  = nums[-1]
                    break

        print(f"      Dep approved={result['approved']} claimed={result['claimed']} Cr")
        return result

    # =========================================================================
    # INTANGIBLES (D84)
    # =========================================================================

    def extract_intangibles(self) -> Dict:
        """Extract D84: Amortization of Intangible Assets 2024-25"""
        print("   Extracting Intangibles (D84)...")

        result = {'claimed': None, 'found': False}

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*84', r'TABLE\s*[–\-]?\s*D84',
             r'[Aa]mortiz[sa]tion\s+of\s+[Ii]ntangible.*2024'],
            self._d_start + 75, self._d_end
        )

        if raw:
            result['found'] = True
            for row in raw:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                if not nums:
                    continue
                # D84 cols: Item | SBU G | SBU T | SBU D | Total
                # nums: [1.32, 1.32, 10.58, 13.22] → SBU D = nums[2]
                if 'amortiz' in row_text or 'software' in row_text or 'intangible' in row_text:
                    result['claimed'] = nums[2] if len(nums) >= 3 else nums[-1]
                    break

        print(f"      Intangibles claimed={result['claimed']} Cr")
        return result

    # =========================================================================
    # LIQUIDATED DAMAGES (D85)
    # =========================================================================

    def extract_liquidated_damages(self) -> Dict:
        """Extract D85: Claim towards refund of Liquidated Damages"""
        print("   Extracting Liquidated Damages (D85)...")

        result = {'claimed': None, 'found': False}

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*85', r'TABLE\s*[–\-]?\s*D85',
             r'[Ll]iquidated\s+[Dd]amages',
             r'[Rr]efund.*[Ll]iquidated'],
            self._d_start + 75, self._d_end
        )

        if raw:
            result['found'] = True
            for row in raw:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                if not nums:
                    continue
                # D85 cols: Item | SBU G | SBU T | SBU D | Total
                # nums: [0.00, 0.13, 16.30, 16.43] → SBU D = nums[2]
                if 'liquidated' in row_text or 'refund' in row_text or 'claim' in row_text:
                    result['claimed'] = nums[2] if len(nums) >= 3 else nums[-1]
                    break

        print(f"      Liq. damages claimed={result['claimed']} Cr")
        return result

    # =========================================================================
    # REVENUE (D86-D88)
    # =========================================================================

    def extract_revenue(self) -> Dict:
        """
        Extract revenue data from Tables D86-D88.
        D86/D87: Revenue from sale of power
        D88: Revenue comparison approved vs actuals
        """
        print("   Extracting Revenue tables (D86-D88)...")

        result = {
            'tariff_income_cr':         None,
            'tariff_approved_cr':       None,
            'power_factor_incentive_cr': None,
            'external_sale_cr':         None,
            'nti_cr':                   None,
            'total_erc_cr':             None,
            'found': False,
        }

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*D\s*88', r'TABLE\s*[–\-]?\s*D88',
             r'[Rr]evenue\s+comparison\s+[Aa]pproved',
             r'[Rr]evenue.*[Aa]pproved.*[Aa]ctual'],
            self._d_start + 75, self._d_end,
            multi_page=True
        )

        if raw:
            result['found'] = True
            for row in raw:
                row_text = ' '.join(str(c) for c in row if c).lower()
                nums = self._nums_from_row(row)
                if not nums:
                    continue
                if 'tariff' in row_text and 'income' in row_text:
                    result['tariff_approved_cr'] = nums[0] if len(nums) >= 2 else None
                    result['tariff_income_cr']   = nums[-1]
                elif 'power factor' in row_text:
                    result['power_factor_incentive_cr'] = nums[-1]
                elif 'external' in row_text or 'outside' in row_text:
                    result['external_sale_cr'] = nums[-1]
                elif 'non-tariff' in row_text or 'non tariff' in row_text:
                    result['nti_cr'] = nums[-1]
                elif 'total' in row_text and 'erc' in row_text:
                    result['total_erc_cr'] = nums[-1]

        print(f"      Tariff income={result['tariff_income_cr']} "
              f"NTI={result['nti_cr']} "
              f"ERC total={result['total_erc_cr']} Cr")
        return result

    # =========================================================================
    # MASTER EXTRACT
    # =========================================================================

    def extract_all(self) -> Dict:
        """Run all extractions and return complete result dict"""
        print()
        print("=" * 60)
        print(f"SBU-D PDF Parser — {self.pdf_path}")
        print(f"Pages: {self.num_pages} | FY: {self.metadata['fiscal_year']}")
        print(f"SBU-D chapter: pages {self._d_start + 1} to {self._d_end + 1}")
        print("=" * 60)

        arr         = self.extract_arr_d89()
        td_losses   = self.extract_td_losses()
        power_pur   = self.extract_power_purchase()
        om          = self.extract_om_details()
        ifc         = self.extract_ifc_details()
        dep         = self.extract_depreciation()
        intangibles = self.extract_intangibles()
        liq_dam     = self.extract_liquidated_damages()
        revenue     = self.extract_revenue()

        def arr_val(key, col='tu'):
            row = arr.get('rows', {}).get(key, {})
            return row.get(col)

        # --- O&M fallback from D89 ---
        om_claimed = om.get('claimed_om_cr') or arr_val('om_expenses')

        # --- IFC fallback from D89 ---
        ifc_total   = ifc.get('ifc_total')   or arr_val('ifc')
        ifc_approved = ifc.get('ifc_approved') or arr_val('ifc', 'approved')

        # --- Build mapped dict for heuristics ---
        mapped = {
            # Pass-through (from other SBUs)
            'cost_generation_sbu_g':   arr_val('cost_generation_sbu_g'),
            'cost_transmission_sbu_t': arr_val('cost_transmission_sbu_t'),

            # Power purchase
            'pp_total_claimed':    (power_pur.get('total_claimed_cr') or
                                    arr_val('power_purchase')),
            'pp_total_approved':   (power_pur.get('total_approved_cr') or
                                    arr_val('power_purchase', 'approved')),
            'pp_sources':          power_pur.get('sources', {}),

            # O&M
            'om_claimed':          om_claimed,
            'om_normative':        om.get('normative_om_cr'),
            'om_employee':         om.get('employee_cost_cr'),
            'om_rm':               om.get('rm_expenses_cr'),
            'om_ag':               om.get('ag_expenses_cr'),
            'om_cost_drivers':     om.get('cost_drivers', {}),

            # IFC — D89 is most reliable; D83 components for breakdown detail
            'ifc_total_claimed':   arr_val('ifc'),
            'ifc_total_approved':  arr_val('ifc', 'approved'),
            'ifc_ltl':             ifc.get('term_loan_interest'),
            'ifc_wc':              ifc.get('wc_interest'),
            'ifc_gpf':             ifc.get('gpf_interest'),
            'ifc_other':           ifc.get('other_charges'),
            'ifc_carrying_cost':   ifc.get('carrying_cost'),
            'ifc_master_trust':    ifc.get('master_trust_int'),

            # Depreciation — D89 primary (D78 page conflicts with D77)
            'depreciation_claimed':  arr_val('depreciation'),
            'depreciation_approved': arr_val('depreciation', 'approved'),

            # ROE
            'roe_claimed':   arr_val('roe'),
            'roe_approved':  arr_val('roe', 'approved'),

            # Master Trust bonds
            'master_trust_claimed':  arr_val('master_trust'),
            'master_trust_approved': arr_val('master_trust', 'approved'),

            # Bond repayment
            'bond_repayment': arr_val('bond_repayment'),

            # T&D loss gain — D89 primary (D12 parsing unreliable)
            'td_loss_gain_claimed':   arr_val('td_loss_gain'),
            'td_loss_approved_pct':   td_losses.get('approved_loss_pct'),
            'td_loss_actual_pct':     td_losses.get('actual_loss_pct'),

            # Intangibles
            'intangibles_claimed':    (intangibles.get('claimed') or
                                       arr_val('intangibles')),

            # Liquidated damages
            'liquidated_damages_claimed': (liq_dam.get('claimed') or
                                           arr_val('liquidated_damages')),

            # Other / exceptional / solar
            'exceptional_claimed':        arr_val('exceptional_items'),
            'other_expenses_claimed':     arr_val('other_expenses'),
            'solar_registration_claimed': arr_val('solar_registration_refund'),

            # Revenue
            'tariff_income_claimed':        (revenue.get('tariff_income_cr') or
                                             arr_val('tariff_income')),
            'tariff_income_approved':       (revenue.get('tariff_approved_cr') or
                                             arr_val('tariff_income', 'approved')),
            'power_factor_incentive':       (revenue.get('power_factor_incentive_cr') or
                                             arr_val('power_factor_incentive')),
            'external_sale_revenue':        (revenue.get('external_sale_cr') or
                                             arr_val('external_sale_revenue')),
            'nti_claimed':                  (revenue.get('nti_cr') or arr_val('nti')),
            'nti_approved':                 arr_val('nti', 'approved'),
            'total_erc_claimed':            (revenue.get('total_erc_cr') or
                                             arr_val('erc_total')),

            # ARR/ERC totals
            'arr_total_claimed':   arr_val('arr_total'),
            'arr_total_approved':  arr_val('arr_total', 'approved'),
            'revenue_gap_claimed': arr_val('revenue_gap'),
        }

        # -----------------------------------------------------------------------
        # EXTRACTION SUMMARY
        # -----------------------------------------------------------------------
        print()
        print("=" * 60)
        print("EXTRACTION SUMMARY — SBU-D")
        print("=" * 60)
        print(f"ARR Table found:        {arr['found']}")
        print(f"ARR rows extracted:     {len(arr.get('rows', {}))}")
        print(f"Power Purchase claimed: ₹{mapped['pp_total_claimed'] or 'N/A'} Cr")
        print(f"O&M claimed:            ₹{mapped['om_claimed'] or 'N/A'} Cr")
        print(f"IFC total claimed:      ₹{mapped['ifc_total_claimed'] or 'N/A'} Cr")
        print(f"Depreciation claimed:   ₹{mapped['depreciation_claimed'] or 'N/A'} Cr")
        print(f"ROE claimed:            ₹{mapped['roe_claimed'] or 'N/A'} Cr")
        print(f"T&D Loss gain:          ₹{mapped['td_loss_gain_claimed'] or 'N/A'} Cr")
        print(f"Total ARR:              ₹{mapped['arr_total_claimed'] or 'N/A'} Cr")
        print(f"Total ERC:              ₹{mapped['total_erc_claimed'] or 'N/A'} Cr")
        print(f"Revenue Gap:            ₹{mapped['revenue_gap_claimed'] or 'N/A'} Cr")
        print("=" * 60)

        return {
            'metadata':  self.metadata,
            'arr_table': arr,
            'raw': {
                'td_losses':    td_losses,
                'power_pur':    power_pur,
                'om_details':   om,
                'ifc_details':  ifc,
                'depreciation': dep,
                'intangibles':  intangibles,
                'liq_damages':  liq_dam,
                'revenue':      revenue,
            },
            'mapped': mapped,
        }

    def close(self):
        self.pdf.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# =============================================================================
# CLI RUNNER
# =============================================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_parser_sbu_d.py <petition.pdf>")
        sys.exit(1)

    with SBUDPDFParser(sys.argv[1]) as parser:
        results = parser.extract_all()
