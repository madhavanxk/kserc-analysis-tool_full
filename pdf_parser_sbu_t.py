"""
PDF Parser for SBU-T (Transmission) - KSERC Truing-Up Petitions
================================================================
Extracts tables from KSEB truing-up petitions for SBU-T chapter.
Chapter 3: Pages 31-51 of the 2024-25 petition.

Key differences from SBU-G:
- ARR table (T6) columns: Approved / Actual / Truing up requirement
- Table prefix: T1-T16 have "T" prefix; Tables 12,13,14 have NO prefix (sloppy)
- Additional line items: TRANS-COMP-01, TRANS-INCENT-01
- Embedded page number "33" in ARR table between rows 8 and 9

Usage:
    parser = SBUTPDFParser('KSERC_TruingUp_2024-25_KSEB.pdf')
    results = parser.extract_all()
"""

import re
import pdfplumber
from typing import Dict, List, Optional, Tuple


# =============================================================================
# MAIN PARSER CLASS
# =============================================================================

class SBUTPDFParser:
    """
    Parse KSERC truing-up petitions for SBU-T data.
    Operates on pages 31-51 of the petition.
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.pdf = pdfplumber.open(pdf_path)
        self.num_pages = len(self.pdf.pages)

        self.metadata = {
            'fiscal_year': None,
            'sbu': 'T',
            'document_type': None,
            'num_pages': self.num_pages
        }

        # SBU-T page boundaries (0-indexed) — detected dynamically
        self._t_start = None
        self._t_end = None

        self._detect_metadata()
        self._detect_sbu_t_boundaries()

    # =========================================================================
    # METADATA + BOUNDARY DETECTION
    # =========================================================================

    def _detect_metadata(self):
        """Detect fiscal year from first 5 pages"""
        text = ""
        for p in self.pdf.pages[:5]:
            text += p.extract_text() or ""
        fy = re.findall(r'(20\d{2})-(\d{2})', text)
        if fy:
            self.metadata['fiscal_year'] = f"{fy[0][0]}-{fy[0][1]}"
        if 'petition' in text.lower():
            self.metadata['document_type'] = 'Petition'

    def _detect_sbu_t_boundaries(self):
        """Find SBU-T chapter start and end pages"""
        t_start = None
        t_end = None

        def _is_toc_page(text: str) -> bool:
            """
            Detect if a page is a Table of Contents page.
            TOC pages have: 'contents' keyword OR many dotted leaders OR
            dense page-number references (short lines ending in digits).
            """
            t = text.lower()
            if 'table of contents' in t or 'contents' in t[:200]:
                return True
            # TOC lines typically end with ".... 31" style patterns
            dot_lines = len(re.findall(r'\.{3,}\s*\d+', text))
            if dot_lines >= 4:
                return True
            # Many short lines each ending in a number = TOC
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            num_ending_lines = sum(1 for l in lines if re.search(r'\d+$', l))
            if lines and num_ending_lines / len(lines) > 0.6:
                return True
            return False

        for page_num in range(self.num_pages):
            text = (self.pdf.pages[page_num].extract_text() or '')
            text_lower = text[:1000].lower()

            # Skip TOC pages
            if _is_toc_page(text):
                continue

            is_chapter = re.search(r'chapter\s*[–\-]?\s*\d+', text_lower)
            if not is_chapter:
                continue

            if t_start is None:
                if ('transmission' in text or 'sbu-t' in text or
                        'sbu – t' in text or 'sbu- t' in text or 'sldc' in text):
                    t_start = page_num
                    print(f"   SBU-T starts at page {page_num + 1}")
            else:
                # Next chapter = end of SBU-T
                # Require strict distribution chapter header — not just a mention
                is_dist_chapter = (
                    ('distribution' in text_lower or 'sbu-d' in text_lower or
                     'sbu – d' in text_lower) and
                    ('truing up' in text_lower or 'arr' in text_lower or
                     'strategic business' in text_lower or 'chapter' in text_lower)
                )
                if is_dist_chapter:
                    t_end = page_num - 1
                    print(f"   SBU-T ends at page {page_num}")
                    break

        self._t_start = t_start if t_start is not None else 30
        self._t_end = t_end if t_end is not None else min(
            self._t_start + 21, self.num_pages - 1)
        print(f"   SBU-T boundary: pages {self._t_start + 1} to {self._t_end + 1}")

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _clean_value(self, val) -> Optional[float]:
        """Convert cell text to float, return None if not parseable"""
        if val is None:
            return None
        s = str(val).strip()
        # Remove common noise
        s = re.sub(r'[₹,\s]', '', s)
        s = re.sub(r'\(([0-9.]+)\)', r'-\1', s)  # (123) → -123
        # Skip pure page numbers or short noise
        if re.match(r'^\d{1,2}$', s) and len(s) <= 2:
            return None
        try:
            return float(s)
        except (ValueError, TypeError):
            return None

    def _clean_table(self, raw_table: List) -> List[List[str]]:
        """Clean raw table - normalize None, strip whitespace"""
        cleaned = []
        for row in raw_table:
            if row is None:
                continue
            cleaned_row = [
                str(cell).strip() if cell is not None else ''
                for cell in row
            ]
            # Skip rows that are entirely empty
            if any(c for c in cleaned_row):
                cleaned.append(cleaned_row)
        return cleaned

    def _find_table_in_range(
        self,
        patterns: List[str],
        start: int,
        end: int,
        multi_page: bool = False
    ) -> Optional[List[List[str]]]:
        """
        Find table matching any pattern within page range.
        Combines ALL tables on the matching page to handle cases where
        embedded page numbers or merged cells cause pdfplumber to split
        one logical table into multiple tables.
        Returns cleaned combined table data or None.
        """
        for page_num in range(start, min(end + 1, self.num_pages)):
            page = self.pdf.pages[page_num]
            text = page.extract_text() or ''

            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    tables = page.extract_tables()
                    if not tables:
                        continue

                    # Combine ALL tables on this page — handles split tables
                    combined = []
                    for tbl in tables:
                        cleaned = self._clean_table(tbl)
                        if cleaned:
                            combined.extend(cleaned)

                    if multi_page and page_num + 1 <= end:
                        next_tables = self.pdf.pages[page_num + 1].extract_tables()
                        if next_tables:
                            for tbl in next_tables:
                                next_data = self._clean_table(tbl)
                                if not next_data:
                                    continue
                                # Only append if continuation (no header row)
                                first_row = next_data[0] if next_data else []
                                is_continuation = not any(
                                    re.search(
                                        r'table|particulars|sl\.?\s*no|no\.',
                                        str(c), re.IGNORECASE
                                    )
                                    for c in first_row if c
                                )
                                if is_continuation:
                                    combined.extend(next_data)

                    return combined if combined else None
        return None

    def _extract_value_from_arr_row(
        self,
        row: List[str],
        col_index: int
    ) -> Optional[float]:
        """
        Extract numeric value from ARR table row at given column index.
        Handles embedded page numbers and blank cells.
        """
        if col_index >= len(row):
            return None
        return self._clean_value(row[col_index])

    # =========================================================================
    # ARR TABLE (T6) - MAIN EXTRACTION
    # =========================================================================

    def extract_arr_table(self) -> Dict:
        """
        Extract Table T6: ARR of Transmission Business Unit (SBU-T & SLDC)
        Columns: Approved / Actual / Truing up requirement
        Note: Embedded page number "33" between rows 8 and 9 handled.
        Note: Row 12 (Edamon-Kochi) has blank Actual column.
        """
        print("   Extracting Table T6: ARR (SBU-T)...")

        patterns = [
            r'TABLE\s*[–\-]?\s*T\s*6',
            r'ARR\s+OF\s+TRANSMISSION\s+BUSINESS',
            r'ARR.*TRANSMISSION.*SBU.*T',
            r'TABLE.*T6'
        ]

        # Use multi-page stitching — table spans pages 33-34
        raw = self._find_table_in_range(
            patterns, self._t_start, self._t_end, multi_page=True
        )

        result = {
            'table_id': 'T6',
            'found': False,
            'columns': ['approved', 'actual', 'tu_sought'],
            'rows': {}
        }

        if not raw:
            print("      Table T6 NOT found")
            return result

        result['found'] = True

        # Row mapping: row number → line item key
        ROW_MAP = {
            1:  'ifc_loan',
            2:  'ifc_gpf',
            3:  'ifc_master_trust',
            4:  'ifc_wc',
            5:  'ifc_other',
            6:  'ifc_total',
            7:  'roe',
            8:  'depreciation',
            9:  'om_expenses',
            10: 'master_trust_repayment',
            11: 'master_trust_contribution',
            12: 'edamon_kochi_compensation',
            13: 'pugalur_thrissur_compensation',
            14: 'intangibles',
            16: 'exceptional_items',
            17: 'liquidated_damages',
            19: 'transmission_incentive',
            20: 'arr_total',
            21: 'nti',
        }

        # Detect column positions from header rows in combined data
        # Default: col 0=row_num, col 1=particulars, col 2=blank/merged,
        # col 3=approved, col 4=actual, col 5=tu
        # SBU-T ARR table has an extra blank column due to merged header cell
        approved_col = 3
        actual_col   = 4
        tu_col       = 5

        for row in raw[:8]:
            row_text = ' '.join(str(c).lower() for c in row if c)
            if 'approv' in row_text or 'actual' in row_text or 'truing' in row_text:
                for i, cell in enumerate(row):
                    cell_l = str(cell).lower().strip()
                    if 'approv' in cell_l:
                        approved_col = i
                    elif 'actual' in cell_l:
                        actual_col = i
                    elif 'truing' in cell_l or 'requirement' in cell_l:
                        tu_col = i
                print(f"      Column positions — Approved:{approved_col} "
                      f"Actual:{actual_col} TU:{tu_col}")
                break
        else:
            print(f"      Header not found — using defaults: "
                  f"Approved:{approved_col} Actual:{actual_col} TU:{tu_col}")

        # Process each sub-table separately with its own column detection
        # This correctly handles sub-tables with different column counts
        parsed_rows = {}

        def extract_numeric_values(row):
            """Extract all numeric values from a row, skipping row number at index 0."""
            nums = []
            for i, cell in enumerate(row):
                if i == 0:
                    continue  # Skip row number column
                v = self._clean_value(cell)
                if v is not None:
                    nums.append(v)
            return nums

        def parse_rows(rows):
            """
            Parse rows using positional numeric extraction.
            Each data row has: [row_num, particulars..., approved, actual, tu]
            We collect all numeric values (excluding row_num) and map last 3 as (approved, actual, tu).
            Rows with fewer than 3 values get partial mapping.
            """
            for row in rows:
                if not row or not row[0]:
                    continue
                row_num_str = str(row[0]).strip()
                # Skip embedded page numbers
                try:
                    pn = int(row_num_str)
                    if pn > 25 and len(row_num_str) >= 2:
                        continue
                except ValueError:
                    continue
                try:
                    rn = int(re.sub(r'[^\d]', '', row_num_str))
                except (ValueError, TypeError):
                    continue
                if rn not in ROW_MAP:
                    continue

                nums = extract_numeric_values(row)
                # Map: last value = tu, second-last = actual, third-last = approved
                approved = nums[-3] if len(nums) >= 3 else None
                actual   = nums[-2] if len(nums) >= 2 else None
                tu       = nums[-1] if len(nums) >= 1 else None

                # Sanity cap: individual line items should not exceed 2000 Cr
                # Values like 26564 are GFA/asset figures leaked from row text
                MAX_LINE_ITEM = 2000.0
                if approved and approved > MAX_LINE_ITEM: approved = None
                if actual   and actual   > MAX_LINE_ITEM: actual   = None
                if tu       and tu       > MAX_LINE_ITEM: tu       = None

                ex = parsed_rows.get(rn, {})
                parsed_rows[rn] = {
                    'row_number': rn,
                    'approved':  approved  if approved  is not None else ex.get('approved'),
                    'actual':    actual    if actual    is not None else ex.get('actual'),
                    'tu_sought': tu        if tu        is not None else ex.get('tu_sought'),
                }

        # Process sub-tables per-page
        for page_num in range(self._t_start, min(self._t_end + 1, self.num_pages)):
            page_text = self.pdf.pages[page_num].extract_text() or ''
            if not any(re.search(p, page_text, re.IGNORECASE) for p in patterns):
                continue
            for pn in [page_num, page_num + 1]:
                if pn > self._t_end:
                    break
                for sub in (self.pdf.pages[pn].extract_tables() or []):
                    cleaned = self._clean_table(sub)
                    if cleaned:
                        parse_rows(cleaned)
            break

        # Write to result and print
        for row_num, data in sorted(parsed_rows.items()):
            key = ROW_MAP[row_num]
            result['rows'][key] = data
            print(f"      Row {row_num} ({key}): "
                  f"Approved={data['approved']} "
                  f"Actual={data['actual']} "
                  f"TU={data['tu_sought']}")

        return result

    # =========================================================================
    # TRANSMISSION STATISTICS (T1, T5)
    # =========================================================================

    def extract_transmission_statistics(self) -> Dict:
        """
        Extract Table T1/T5: Transmission system statistics
        Bays, MVA capacity, circuit-km — opening values.
        """
        print("   Extracting transmission statistics (T1/T5)...")

        result = {
            'found': False,
            'opening_bays': None,
            'opening_mva': None,
            'opening_cktkm': None,
            'closing_bays': None,
            'closing_mva': None,
            'closing_cktkm': None,
        }

        # Try T5 first (has both opening and closing), then T1
        patterns = [
            r'TABLE\s*[–\-]?\s*T\s*5',
            r'TABLE\s*[–\-]?\s*T5',
            r'Transmission\s+System\s+[Ss]tatistics',
            r'TABLE\s*[–\-]?\s*T\s*1',
        ]

        raw = self._find_table_in_range(patterns, self._t_start, self._t_end)
        if not raw:
            print("      Transmission statistics NOT found")
            return result

        result['found'] = True

        for row in raw:
            if not row:
                continue
            row_text = ' '.join(str(c).lower() for c in row if c)

            if 'bay' in row_text or 'bays' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if len(vals) >= 1:
                    result['opening_bays'] = vals[0]
                if len(vals) >= 2:
                    result['closing_bays'] = vals[-1]

            elif 'mva' in row_text or 'transformer' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if len(vals) >= 1:
                    result['opening_mva'] = vals[0]
                if len(vals) >= 2:
                    result['closing_mva'] = vals[-1]

            elif 'ckt' in row_text or 'circuit' in row_text or 'km' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if len(vals) >= 1:
                    result['opening_cktkm'] = vals[0]
                if len(vals) >= 2:
                    result['closing_cktkm'] = vals[-1]

        print(f"      Bays={result['opening_bays']} MVA={result['opening_mva']} "
              f"CktKm={result['opening_cktkm']}")
        return result

    # =========================================================================
    # ADDITIONS (T2, T3, T4)
    # =========================================================================

    def extract_additions(self) -> Dict:
        """
        Extract Tables T2/T3/T4: Assets commissioned during 2024-25
        Returns added bays, MVA, ckt-km.
        """
        print("   Extracting additions (T2/T3/T4)...")

        result = {
            'found': False,
            'added_bays': 0,
            'added_mva': 0.0,
            'added_cktkm': 0.0,
        }

        # T4 has the summary of all transmission assets created
        patterns = [
            r'TABLE\s*[–\-]?\s*T\s*4',
            r'Transmission\s+Asset\s+[Cc]reated',
            r'TABLE\s*[–\-]?\s*T\s*2',
            r'Sub\s*[Ss]tation\s+[Cc]ommissioned',
        ]

        raw = self._find_table_in_range(
            patterns, self._t_start, self._t_end, multi_page=True
        )
        if not raw:
            print("      Additions tables NOT found — using defaults")
            return result

        result['found'] = True
        total_bays = 0
        total_mva = 0.0
        total_cktkm = 0.0

        for row in raw:
            if not row:
                continue
            row_text = ' '.join(str(c).lower() for c in row if c)

            if 'bay' in row_text or 'bays' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if vals:
                    total_bays += int(vals[-1])

            elif 'mva' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if vals:
                    total_mva += vals[-1]

            elif 'ckt' in row_text or 'km' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if vals:
                    total_cktkm += vals[-1]

        result['added_bays']  = total_bays
        result['added_mva']   = round(total_mva, 2)
        result['added_cktkm'] = round(total_cktkm, 2)

        print(f"      Added — Bays={total_bays} MVA={total_mva:.1f} "
              f"CktKm={total_cktkm:.2f}")
        return result

    # =========================================================================
    # IFC BREAKDOWN (T7, T8, T9, T10)
    # =========================================================================

    def extract_ifc_details(self) -> Dict:
        """
        Extract IFC sub-tables for SBU-T.
        T7: GPF interest — heavily merged, extract from text
        T8: Working capital — data in narrative text on page 36
        T9: Other charges — in narrative text
        T10: Summary — use ARR row 6
        """
        print("   Extracting IFC details (T7-T10)...")

        result = {
            'gpf_interest':  {'found': False, 'claimed': None, 'opening': None, 'closing': None},
            'wc_interest':   {'found': False, 'claimed': None},
            'other_charges': {'found': False, 'claimed': None},
            'ifc_summary':   {'found': False, 'total_claimed': None},
        }

        # Search pages for GPF and WC data in narrative text
        for page_num in range(self._t_start, min(self._t_end + 1, self.num_pages)):
            text = self.pdf.pages[page_num].extract_text() or ''
            text_lower = text.lower()

            # GPF: Look specifically for "Interest paid on GPF...Rs. X Cr"
            if 'gpf' in text_lower and not result['gpf_interest']['found']:
                gpf_match = re.search(
                    r'interest\s+(?:paid\s+)?on\s+gpf.*?rs\.?\s*(\d+\.?\d*)\s*cr',
                    text_lower
                )
                if gpf_match:
                    result['gpf_interest']['found'] = True
                    result['gpf_interest']['claimed'] = float(gpf_match.group(1))
                else:
                    # Try table T7 — look for last numeric value in GPF table
                    tables = self.pdf.pages[page_num].extract_tables() or []
                    for tbl in tables:
                        tbl_text = ' '.join(str(c) for row in tbl for c in row if c).lower()
                        if 'gpf' in tbl_text and 't7' in tbl_text:
                            cleaned = self._clean_table(tbl)
                            for row in cleaned:
                                row_text = ' '.join(str(c).lower() for c in row if c)
                                if 'total' in row_text or 'interest' in row_text:
                                    vals = [self._clean_value(c) for c in row
                                            if self._clean_value(c)]
                                    if vals and vals[-1] < 100:  # GPF interest < 100 Cr
                                        result['gpf_interest']['claimed'] = vals[-1]
                                        result['gpf_interest']['found'] = True

            # WC: Look for "Interest on Working Capital X.XX Y.YY" pattern
            # The two numbers are approved and actual/TU
            if 'interest on working capital' in text_lower and not result['wc_interest']['found']:
                wc_match = re.search(
                    r'interest on working capital\s+([\d.]+)\s+([\d.]+)',
                    text_lower
                )
                if wc_match:
                    result['wc_interest']['found'] = True
                    # Second value is the claimed/TU amount
                    result['wc_interest']['claimed'] = float(wc_match.group(2))

            # Other charges: look for "Rs.X.XX Cr" near "other interest"
            if not result['other_charges']['found']:
                if 'other interest' in text_lower or ('other' in text_lower
                        and 'interest' in text_lower and '1.08' in text):
                    oth_match = re.search(
                        r'rs\.?\s*(\d+\.\d+)\s*cr.*(?:other|truing)',
                        text_lower
                    )
                    if not oth_match:
                        oth_match = re.search(
                            r'(?:other interest|other charges)[^.]*?(\d+\.\d+)\s*cr',
                            text_lower
                        )
                    if oth_match:
                        result['other_charges']['found'] = True
                        result['other_charges']['claimed'] = float(oth_match.group(1))

        print(f"      GPF claimed: {result['gpf_interest']['claimed']}")
        print(f"      WC claimed:  {result['wc_interest']['claimed']}")
        print(f"      Other:       {result['other_charges']['claimed']}")
        return result

    # =========================================================================
    # O&M (Tables 11, 12, 13, 14 — note: 12/13/14 have no T prefix)
    # =========================================================================

    def extract_om_details(self) -> Dict:
        """
        Extract O&M tables for SBU-T.
        T11: Cost drivers (actual bays/MVA/ckt-km)
        Table 12: O&M norms (no T prefix — sloppy)
        Table 13: SBU-T O&M charges (no T prefix)
        Table 14: SBU-T O&M charges continuation (no T prefix)
        """
        print("   Extracting O&M details (T11, 12, 13, 14)...")

        result = {
            'cost_drivers':  {'found': False, 'bays': None, 'mva': None, 'cktkm': None},
            'om_norms':      {'found': False, 'norm_per_bay': None, 'norm_per_mva': None,
                              'norm_per_cktkm': None},
            'om_charges':    {'found': False, 'actual': None, 'approved': None,
                              'claimed': None},
        }

        # T11: Cost drivers
        t11_raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*T\s*11', r'TABLE\s*[–\-]?\s*T11',
             r'[Cc]ost\s+[Dd]rivers.*[Tt]ransmission',
             r'[Aa]pproved.*[Aa]ctual.*[Cc]ost\s+[Dd]rivers'],
            self._t_start, self._t_end
        )
        if t11_raw:
            result['cost_drivers']['found'] = True
            for row in t11_raw:
                row_text = ' '.join(str(c).lower() for c in row if c)
                if 'bay' in row_text:
                    vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                    if vals:
                        result['cost_drivers']['bays'] = vals[-1]
                elif 'mva' in row_text:
                    vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                    if vals:
                        result['cost_drivers']['mva'] = vals[-1]
                elif 'ckt' in row_text or 'km' in row_text:
                    vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                    if vals:
                        result['cost_drivers']['cktkm'] = vals[-1]

        # Table 12: O&M Norms (no T prefix!)
        t12_raw = self._find_table_in_range(
            [r'Table\s+12\b', r'O&M\s+[Nn]orms',
             r'[Nn]orm.*[Bb]ay.*[Mm][Vv][Aa]',
             r'TABLE\s*[–\-]?\s*T\s*12'],
            self._t_start, self._t_end
        )
        if t12_raw:
            result['om_norms']['found'] = True
            for row in t12_raw:
                row_text = ' '.join(str(c).lower() for c in row if c)
                if 'bay' in row_text:
                    vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                    if vals:
                        result['om_norms']['norm_per_bay'] = vals[-1]
                elif 'mva' in row_text:
                    vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                    if vals:
                        result['om_norms']['norm_per_mva'] = vals[-1]
                elif 'ckt' in row_text or 'km' in row_text:
                    vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                    if vals:
                        result['om_norms']['norm_per_cktkm'] = vals[-1]

        # Table 13/14: O&M Charges (no T prefix!)
        for tnum, label in [('13', 'charges_1'), ('14', 'charges_2')]:
            raw = self._find_table_in_range(
                [rf'Table\s+{tnum}\b', rf'SBU\s*[–\-]?\s*T\s+O&M\s+[Cc]harges',
                 rf'TABLE\s*[–\-]?\s*T\s*{tnum}'],
                self._t_start, self._t_end
            )
            if raw:
                result['om_charges']['found'] = True
                for row in raw:
                    row_text = ' '.join(str(c).lower() for c in row if c)
                    if 'total' in row_text or 'grand' in row_text:
                        vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                        if len(vals) >= 2:
                            result['om_charges']['approved'] = vals[0]
                            result['om_charges']['claimed']  = vals[-1]
                        elif vals:
                            result['om_charges']['claimed'] = vals[-1]

        return result

    # =========================================================================
    # DEPRECIATION (T15)
    # =========================================================================

    def extract_depreciation(self) -> Dict:
        """Extract Table T15: Depreciation"""
        print("   Extracting T15: Depreciation...")

        result = {'found': False, 'approved': None, 'actual': None, 'claimed': None}

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*T\s*15', r'TABLE\s*[–\-]?\s*T15',
             r'[Dd]epreciation.*Rs\s*Cr'],
            self._t_start, self._t_end
        )
        if not raw:
            # Fall back to ARR row 8
            print("      T15 not found — will use ARR row 8")
            return result

        result['found'] = True
        for row in raw:
            row_text = ' '.join(str(c).lower() for c in row if c)
            if 'total' in row_text or 'depreciation' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if len(vals) >= 3:
                    result['approved'] = vals[0]
                    result['actual']   = vals[1]
                    result['claimed']  = vals[2]
                elif len(vals) >= 1:
                    result['claimed']  = vals[-1]

        print(f"      Depreciation: approved={result['approved']} "
              f"actual={result['actual']} claimed={result['claimed']}")
        return result

    # =========================================================================
    # ROE (T16)
    # =========================================================================

    def extract_roe(self) -> Dict:
        """Extract Table T16: Return on Equity"""
        print("   Extracting T16: ROE...")

        result = {'found': False, 'approved': None, 'claimed': None}

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*T\s*16', r'TABLE\s*[–\-]?\s*T16',
             r'[Rr]eturn\s+on\s+[Ee]quity.*SBU.T',
             r'[Rr]eturn\s+on\s+[Ee]quity.*Rs\s*Cr'],
            self._t_start, self._t_end
        )
        if not raw:
            print("      T16 not found — will use ARR row 7")
            return result

        result['found'] = True
        for row in raw:
            row_text = ' '.join(str(c).lower() for c in row if c)
            if 'total' in row_text or 'roe' in row_text or 'equity' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if len(vals) >= 2:
                    result['approved'] = vals[0]
                    result['claimed']  = vals[-1]
                elif vals:
                    result['claimed'] = vals[-1]

        print(f"      ROE: approved={result['approved']} claimed={result['claimed']}")
        return result

    # =========================================================================
    # COMPENSATION TABLES (T17-T20)
    # =========================================================================

    def extract_compensation(self) -> Dict:
        """
        Extract compensation totals from Table T20.
        T20 structure: Sl.No | Transmission Line | Amortization amount (Rs. Cr.)
        Row 1: Edamon-Kochi  7.68
        Row 2: Pugalur-Thrissur  1.36
        Total: 9.04
        """
        print("   Extracting compensation tables (T20)...")

        result = {
            'edamon_kochi':      {'found': False, 'claimed': None},
            'pugalur_thrissur':  {'found': False, 'claimed': None},
            'total_compensation':{'found': False, 'claimed': None}
        }

        raw = self._find_table_in_range(
            [r'Table\s+T\s*20', r'TABLE\s*[–\-]?\s*T\s*20',
             r'Total\s+amortization.*intangible',
             r'amortization.*intangible.*interest'],
            self._t_start, self._t_end
        )

        if raw:
            for row in raw:
                if not row:
                    continue
                # Get all non-empty cells
                cells = [str(c).strip() for c in row if c and str(c).strip()]
                if not cells:
                    continue
                row_text = ' '.join(cells).lower()
                # Get last numeric value in row
                nums = [self._clean_value(c) for c in cells if self._clean_value(c)]
                val = nums[-1] if nums else None

                if 'edamon' in row_text:
                    result['edamon_kochi']['found'] = True
                    result['edamon_kochi']['claimed'] = val
                elif 'pugalur' in row_text or 'thrissur' in row_text:
                    result['pugalur_thrissur']['found'] = True
                    result['pugalur_thrissur']['claimed'] = val
                elif 'total' in row_text and val and val > 5:
                    result['total_compensation']['found'] = True
                    result['total_compensation']['claimed'] = val

        # Fallback: read directly from ARR table rows 12 and 13
        if not result['edamon_kochi']['claimed']:
            result['edamon_kochi']['note'] = 'Using ARR row 12 TU value'
        if not result['pugalur_thrissur']['claimed']:
            result['pugalur_thrissur']['note'] = 'Using ARR row 13 TU value'

        print(f"      Edamon-Kochi: {result['edamon_kochi']['claimed']} Cr")
        print(f"      Pugalur-Thrissur: {result['pugalur_thrissur']['claimed']} Cr")
        print(f"      Total: {result['total_compensation']['claimed']} Cr")
        return result

    # =========================================================================
    # INTANGIBLES (T21)
    # =========================================================================

    def extract_intangibles(self) -> Dict:
        """Extract Table T21: Amortization of Intangible Assets"""
        print("   Extracting T21: Intangibles...")

        result = {'found': False, 'claimed': None}

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*T\s*21', r'TABLE\s*[–\-]?\s*T21',
             r'[Ss]oftware.*[Aa]mortization',
             r'[Ii]ntangible\s+[Aa]ssets.*[Ss]oftware'],
            self._t_start, self._t_end
        )
        if not raw:
            print("      T21 not found — will use ARR row 14")
            return result

        result['found'] = True
        for row in raw:
            row_text = ' '.join(str(c).lower() for c in row if c)
            if 'total' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if vals:
                    result['claimed'] = vals[-1]

        return result

    # =========================================================================
    # TRANSMISSION INCENTIVE (T22)
    # =========================================================================

    def extract_transmission_incentive(self) -> Dict:
        """
        Extract Table T22: Incentive on transmission availability
        Key fields: target availability, actual availability, claimed incentive
        """
        print("   Extracting T22: Transmission incentive...")

        result = {
            'found': False,
            'target_availability': 98.50,  # Default per Regulation 56(2)
            'actual_availability': None,
            'claimed_incentive': None,
            'sldc_certified': True,  # Assume certified unless evidence otherwise
        }

        raw = self._find_table_in_range(
            [r'TABLE\s*[–\-]?\s*T\s*22', r'TABLE\s*[–\-]?\s*T22',
             r'[Ii]ncentive.*[Tt]ransmission.*[Aa]vailability',
             r'[Tt]ransmission\s+[Aa]vailability.*Rs\s*Cr'],
            self._t_start, self._t_end
        )
        if not raw:
            print("      T22 not found")
            return result

        result['found'] = True
        for row in raw:
            row_text = ' '.join(str(c).lower() for c in row if c)

            if 'target' in row_text or 'norm' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if vals:
                    result['target_availability'] = vals[-1]

            elif 'actual' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if vals:
                    result['actual_availability'] = vals[-1]

            elif 'incentive' in row_text and 'total' in row_text:
                vals = [self._clean_value(c) for c in row if self._clean_value(c)]
                if vals:
                    result['claimed_incentive'] = vals[-1]

            elif 'sldc' in row_text or 'certif' in row_text:
                if 'not' in row_text or 'no' in row_text:
                    result['sldc_certified'] = False

        print(f"      Target={result['target_availability']}% "
              f"Actual={result['actual_availability']}% "
              f"Incentive={result['claimed_incentive']} Cr")
        return result

    # =========================================================================
    # NTI
    # =========================================================================

    def extract_nti(self) -> Dict:
        """Extract NTI from ARR table row 21"""
        print("   NTI will be extracted from ARR table row 21")
        return {'found': False, 'claimed': None}

    # =========================================================================
    # MASTER EXTRACT_ALL
    # =========================================================================

    def extract_all(self) -> Dict:
        """
        Run all extractions and return consolidated results.
        """
        print(f"\n{'='*60}")
        print(f"SBU-T PDF Parser — {self.pdf_path}")
        print(f"Pages: {self.num_pages} | FY: {self.metadata['fiscal_year']}")
        print(f"SBU-T chapter: pages {self._t_start+1} to {self._t_end+1}")
        print(f"{'='*60}\n")

        # Core ARR table — all claimed values flow from here
        arr = self.extract_arr_table()

        # Supporting tables
        stats        = self.extract_transmission_statistics()
        additions    = self.extract_additions()
        ifc_details  = self.extract_ifc_details()
        om_details   = self.extract_om_details()
        depreciation = self.extract_depreciation()
        roe          = self.extract_roe()
        compensation = self.extract_compensation()
        intangibles  = self.extract_intangibles()
        incentive    = self.extract_transmission_incentive()

        # Helper to get ARR row value
        def arr_val(key, col='tu_sought'):
            row = arr['rows'].get(key, {})
            return row.get(col)

        results = {
            'metadata': self.metadata,
            'arr_table': arr,
            'arr_found': arr['found'],

            # Mapped values for heuristics
            'mapped': {
                # IFC sub-items — use IFC details if available, else ARR rows
                'ifc_loan_claimed':         arr_val('ifc_loan'),
                'ifc_gpf_claimed':          (ifc_details['gpf_interest'].get('claimed') or
                                             arr_val('ifc_gpf')),
                'ifc_master_trust_claimed': arr_val('ifc_master_trust'),
                'ifc_wc_claimed':           (ifc_details['wc_interest'].get('claimed') or
                                             arr_val('ifc_wc')),
                'ifc_other_claimed':        (ifc_details['other_charges'].get('claimed') or
                                             arr_val('ifc_other')),
                'ifc_total_claimed':        arr_val('ifc_total'),
                # ROE
                'roe_claimed':              arr_val('roe'),
                'roe_approved':             arr_val('roe', 'approved'),
                # Depreciation
                'depreciation_claimed':     (depreciation.get('claimed') or
                                             arr_val('depreciation')),
                'depreciation_approved':    (depreciation.get('approved') or
                                             arr_val('depreciation', 'approved')),
                # O&M
                'om_claimed':               om_details['om_charges'].get('claimed') or arr_val('om_expenses'),
                'om_approved':              om_details['om_charges'].get('approved') or arr_val('om_expenses', 'approved'),
                # Transmission specific
                'edamon_kochi_claimed':     (compensation['edamon_kochi'].get('claimed') or
                                             arr_val('edamon_kochi_compensation')),
                'pugalur_thrissur_claimed': (compensation['pugalur_thrissur'].get('claimed') or
                                             arr_val('pugalur_thrissur_compensation')),
                'trans_incentive_claimed':  (incentive.get('claimed_incentive') or
                                             arr_val('transmission_incentive')),
                # Master Trust
                'master_trust_claimed':     arr_val('ifc_master_trust'),
                'master_trust_approved':    arr_val('ifc_master_trust', 'approved'),
                # NTI
                'nti_claimed':              arr_val('nti'),
                # Intangibles
                'intangibles_claimed':      (intangibles.get('claimed') or
                                             arr_val('intangibles')),
                # Exceptional
                'exceptional_claimed':      arr_val('exceptional_items'),
                # Liquidated damages (new in SBU-T)
                'liquidated_damages_claimed': arr_val('liquidated_damages'),
                # O&M norms for heuristic
                'opening_bays':   stats.get('opening_bays'),
                'opening_mva':    stats.get('opening_mva'),
                'opening_cktkm':  stats.get('opening_cktkm'),
                'added_bays':     additions.get('added_bays'),
                'added_mva':      additions.get('added_mva'),
                'added_cktkm':    additions.get('added_cktkm'),
                'norm_per_bay':   om_details['om_norms'].get('norm_per_bay'),
                'norm_per_mva':   om_details['om_norms'].get('norm_per_mva'),
                'norm_per_cktkm': om_details['om_norms'].get('norm_per_cktkm'),
                # Incentive
                'actual_availability': incentive.get('actual_availability'),
                'target_availability': incentive.get('target_availability', 98.50),
                'sldc_certified':      incentive.get('sldc_certified', True),
                # IFC details
                'gpf_opening':  ifc_details['gpf_interest'].get('opening'),
                'gpf_closing':  ifc_details['gpf_interest'].get('closing'),
            },

            # Raw extractions for debugging
            'raw': {
                'transmission_statistics': stats,
                'additions':               additions,
                'ifc_details':             ifc_details,
                'om_details':              om_details,
                'depreciation':            depreciation,
                'roe':                     roe,
                'compensation':            compensation,
                'intangibles':             intangibles,
                'incentive':               incentive,
            }
        }

        # Print summary
        print(f"\n{'='*60}")
        print("EXTRACTION SUMMARY — SBU-T")
        print(f"{'='*60}")
        print(f"ARR Table found: {arr['found']}")
        print(f"ARR rows extracted: {len(arr['rows'])}")
        mapped = results['mapped']
        print(f"ROE claimed:          ₹{mapped.get('roe_claimed')} Cr")
        print(f"Depreciation claimed: ₹{mapped.get('depreciation_claimed')} Cr")
        print(f"O&M claimed:          ₹{mapped.get('om_claimed')} Cr")
        print(f"IFC total claimed:    ₹{mapped.get('ifc_total_claimed')} Cr")
        print(f"Edamon-Kochi:         ₹{mapped.get('edamon_kochi_claimed')} Cr")
        print(f"Pugalur-Thrissur:     ₹{mapped.get('pugalur_thrissur_claimed')} Cr")
        print(f"Trans Incentive:      ₹{mapped.get('trans_incentive_claimed')} Cr")
        print(f"NTI:                  ₹{mapped.get('nti_claimed')} Cr")
        print(f"{'='*60}\n")

        return results

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
        print("Usage: python pdf_parser_sbu_t.py <petition.pdf>")
        sys.exit(1)

    parser = SBUTPDFParser(sys.argv[1])
    results = parser.extract_all()
    parser.close()

    import json
    out_file = sys.argv[1].replace('.pdf', '_sbu_t_extracted.json')
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {out_file}")
