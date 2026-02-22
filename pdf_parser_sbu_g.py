"""
PDF Parser for SBU-G (Generation) - KSERC Truing-Up Petitions
================================================================
Extracts tables and context from KSEB truing-up petitions.
ROBUST content-based detection - finds ARR table regardless of format!
HANDLES MULTI-PAGE TABLES!
NOW INCLUDES: Chapter 5 Common Tables (Depreciation, Assets, etc.)

Usage:
    parser = SBUGPDFParser('KSEB_Petition_FY2024-25.pdf')
    roe_data = parser.extract_roe()
    depreciation_data = parser.extract_depreciation_schedule()
    all_data = parser.extract_all()
"""

import re
import pdfplumber
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TableMatch:
    """Represents a matched table with confidence score"""
    page_number: int
    table_data: List[List[str]]
    table_title: str
    confidence: float
    bounding_box: Optional[Tuple] = None


@dataclass
class SectionData:
    """Represents a complete section with tables and context"""
    section_number: str
    section_title: str
    narrative_text: str
    tables: List[TableMatch]
    variance_explanation: Optional[Dict] = None


# =============================================================================
# MAIN PARSER CLASS
# =============================================================================

class SBUGPDFParser:
    """
    Parse KSERC truing-up petitions for SBU-G data.
    Extracts both tables and contextual explanations.
    """
    
    def __init__(self, pdf_path: str):
        """
        Initialize parser with PDF file.
        
        Args:
            pdf_path: Path to KSEB petition or KSERC order PDF
        """
        self.pdf_path = pdf_path
        self.pdf = pdfplumber.open(pdf_path)
        self.num_pages = len(self.pdf.pages)
        
        # Metadata
        self.metadata = {
            'fiscal_year': None,
            'sbu': 'G',
            'document_type': None,
            'num_pages': self.num_pages
        }
        
        # Cache for section boundaries
        self._boundaries_cache = None
        
        # Detect document type and fiscal year
        self._detect_metadata()
    
    def _detect_metadata(self):
        """Detect FY and document type from first few pages"""
        first_pages_text = ""
        for page_num in range(min(5, self.num_pages)):
            first_pages_text += self.pdf.pages[page_num].extract_text() or ""
        
        # Detect fiscal year
        fy_pattern = r'(20\d{2})-(\d{2})'
        fy_matches = re.findall(fy_pattern, first_pages_text)
        if fy_matches:
            self.metadata['fiscal_year'] = f"{fy_matches[0][0]}-{fy_matches[0][1]}"
        
        # Detect document type
        if 'petition' in first_pages_text.lower():
            self.metadata['document_type'] = 'Petition'
        elif 'order' in first_pages_text.lower():
            self.metadata['document_type'] = 'Order'
    
    # =========================================================================
    # SECTION BOUNDARY DETECTION
    # =========================================================================
    
    def _detect_sbu_boundaries(self) -> Dict[str, Tuple[int, int]]:
        """
        Intelligently detect SBU chapter boundaries.
        Takes FIRST chapter occurrence only (not summary chapters).
        
        Returns:
            Dict like {'sbu_g': (6, 30), 'sbu_t': (31, 51), 'sbu_d': (52, 176)}
        """
        if self._boundaries_cache is not None:
            return self._boundaries_cache
        
        print("   Detecting SBU chapter boundaries...")
        
        boundaries = {}
        
        # Flags to track if we've found each SBU chapter (FIRST occurrence only)
        found_sbu_g = False
        found_sbu_t = False
        found_sbu_d = False
        
        sbu_g_start = None
        sbu_t_start = None
        sbu_d_start = None
        
        for page_num in range(self.num_pages):
            page = self.pdf.pages[page_num]
            text = page.extract_text() or ""
            
            # Check first 1000 chars for chapter headers
            header_text = text[:1000].lower()
            
            # Look for "CHAPTER" with number (stricter pattern)
            is_chapter = re.search(r'chapter\s*[–\-]?\s*\d+', header_text)
            
            if not is_chapter:
                continue
            
            # Check for SBU markers
            has_sbu = 'sbu' in header_text
            
            # SBU-G / Generation - take FIRST occurrence only
            if not found_sbu_g and has_sbu and ('generation' in header_text or 
                                                'sbu-g' in header_text or 
                                                'sbu – g' in header_text or
                                                'sbu- g' in header_text or
                                                'sbu -g' in header_text):
                sbu_g_start = page_num
                found_sbu_g = True
                print(f"      SBU-G chapter starts at page {page_num + 1}")
            
            # SBU-T / Transmission - take FIRST occurrence only
            elif not found_sbu_t and has_sbu and ('transmission' in header_text or 
                                                  'sbu-t' in header_text or 
                                                  'sbu – t' in header_text or
                                                  'sbu- t' in header_text or
                                                  'sbu -t' in header_text or
                                                  'sldc' in header_text):
                # Close SBU-G
                if sbu_g_start is not None:
                    boundaries['sbu_g'] = (sbu_g_start, page_num - 1)
                
                sbu_t_start = page_num
                found_sbu_t = True
                print(f"      SBU-T chapter starts at page {page_num + 1}")
            
            # SBU-D / Distribution - take FIRST occurrence only
            elif not found_sbu_d and has_sbu and ('distribution' in header_text or 
                                                  'sbu-d' in header_text or 
                                                  'sbu – d' in header_text or
                                                  'sbu- d' in header_text or
                                                  'sbu -d' in header_text):
                # Close SBU-T
                if sbu_t_start is not None:
                    boundaries['sbu_t'] = (sbu_t_start, page_num - 1)
                
                sbu_d_start = page_num
                found_sbu_d = True
                print(f"      SBU-D chapter starts at page {page_num + 1}")
                
                # All three found - close SBU-D
                boundaries['sbu_d'] = (sbu_d_start, min(sbu_d_start + 125, self.num_pages - 1))
                break
        
        # Handle cases where not all sections found
        if sbu_g_start is not None and 'sbu_g' not in boundaries:
            if sbu_t_start:
                boundaries['sbu_g'] = (sbu_g_start, sbu_t_start - 1)
            else:
                boundaries['sbu_g'] = (sbu_g_start, min(sbu_g_start + 25, self.num_pages - 1))
        
        if sbu_t_start is not None and 'sbu_t' not in boundaries:
            if sbu_d_start:
                boundaries['sbu_t'] = (sbu_t_start, sbu_d_start - 1)
            else:
                boundaries['sbu_t'] = (sbu_t_start, min(sbu_t_start + 20, self.num_pages - 1))
        
        # Log detected boundaries
        for sbu, (start, end) in boundaries.items():
            print(f"      {sbu.upper()}: pages {start + 1} to {end + 1}")
        
        # Cache results
        self._boundaries_cache = boundaries
        return boundaries
    
    # =========================================================================
    # TABLE DETECTION & EXTRACTION
    # =========================================================================
    
    def _find_table_by_patterns(
        self, 
        patterns: List[str], 
        start_page: int = 0,
        end_page: Optional[int] = None
    ) -> Optional[TableMatch]:
        """
        Find table matching any of the given title patterns.
        
        Args:
            patterns: List of regex patterns to match table titles
            start_page: Start searching from this page (default: 0)
            end_page: Stop at this page (default: None = search all)
        
        Returns:
            TableMatch object or None if not found
        """
        if end_page is None:
            end_page = self.num_pages
        
        for page_num in range(start_page, min(end_page, self.num_pages)):
            page = self.pdf.pages[page_num]
            page_text = page.extract_text() or ""
            
            # Check each pattern
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    # Found matching title
                    table_title = match.group(0)
                    
                    # Extract tables from this page
                    tables = page.extract_tables()
                    
                    if tables:
                        # Usually the first table after title
                        table_data = self._clean_table(tables[0])
                        
                        # Calculate confidence
                        confidence = self._calculate_table_confidence(
                            table_data, 
                            table_title
                        )
                        
                        return TableMatch(
                            page_number=page_num,
                            table_data=table_data,
                            table_title=table_title,
                            confidence=confidence
                        )
        
        return None
    
    def _clean_table(self, raw_table: List[List]) -> List[List[str]]:
        """
        Clean extracted table data.
        - Remove None values
        - Strip whitespace
        - Handle merged cells
        """
        cleaned = []
        for row in raw_table:
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append('')
                else:
                    cleaned_row.append(str(cell).strip())
            cleaned.append(cleaned_row)
        
        return cleaned
    
    def _calculate_table_confidence(
        self, 
        table_data: List[List[str]], 
        table_title: str
    ) -> float:
        """
        Calculate confidence score for table extraction.
        
        Checks:
        - Has reasonable number of rows (3+)
        - Has numeric data
        - Header row looks reasonable
        """
        score = 0.0
        
        # Must have at least 3 rows (header + 2 data)
        if len(table_data) < 3:
            return 0.3
        score += 30
        
        # Check for numeric data in rows
        numeric_count = 0
        for row in table_data[1:]:  # Skip header
            for cell in row:
                if re.search(r'\d+\.?\d*', cell):
                    numeric_count += 1
        
        if numeric_count >= len(table_data) - 1:  # At least 1 number per row
            score += 40
        
        # Check header quality
        header = table_data[0]
        expected_keywords = ['claimed', 'approved', 'myt', 'actual', 'amount', 'arr', 'tu sought']
        header_matches = sum(
            1 for keyword in expected_keywords 
            if any(keyword in cell.lower() for cell in header)
        )
        score += header_matches * 6  # Up to 42 points
        
        return min(score, 100.0)
    
    def _find_summary_table(self) -> Optional[Dict]:
        """
        Find the SBU-G ARR summary table using CONTENT-BASED detection.
        Works even if table number changes (G8 → G9, etc.)
        HANDLES MULTI-PAGE TABLES!
        
        Strategy:
        1. Search within SBU-G boundaries
        2. Find table with "ARR" + "GENERATION" in title
        3. Validate: has 10+ rows with key line items
        4. Validate: has financial numbers
        5. Check for continuation on next page(s)
        
        Returns:
            Dictionary with table info or None
        """
        # Detect section boundaries
        boundaries = self._detect_sbu_boundaries()
        
        if 'sbu_g' not in boundaries:
            print("   WARNING: Could not detect SBU-G section boundaries")
            start_page = 0
            end_page = self.num_pages
        else:
            start_page, end_page = boundaries['sbu_g']
            print(f"   Searching for ARR table in SBU-G section (pages {start_page + 1}-{end_page + 1})...")
        
        best_match = None
        best_score = 0
        
        # Search within SBU-G section
        for page_num in range(start_page, min(end_page + 1, self.num_pages)):
            page = self.pdf.pages[page_num]
            page_text = page.extract_text() or ""
            
            # Check if page has ARR table title
            # Pattern: "ARR" AND ("GENERATION" OR "SBU-G" OR "SBU G")
            page_lower = page_text[:2000].lower()
            
            has_arr = 'arr' in page_lower
            has_generation = ('generation' in page_lower or 
                            'sbu-g' in page_lower or 
                            'sbu – g' in page_lower or
                            'sbu g' in page_lower)
            
            if not (has_arr and has_generation):
                continue
            
            # Extract tables from this page
            tables = page.extract_tables()
            
            for table in tables:
                if not table or len(table) < 10:  # ARR table has 10+ rows
                    continue
                
                table_data = self._clean_table(table)
                
                # Check structure: allow up to 10 columns
                num_cols = len(table_data[0]) if table_data else 0
                if num_cols < 4 or num_cols > 10:
                    continue
                
                # Convert to searchable text
                table_text = ' '.join([' '.join(row).lower() for row in table_data])
                
                # Count SBU-G ARR line items
                key_items = [
                    'roe', 'return on equity',
                    'depreciation',
                    'interest', 'finance',
                    'o&m', 'operation', 'maintenance',
                    'generation', 'cost of generation',
                    'non-tariff', 'nti',
                    'master trust',
                    'exceptional',
                    'intangible',
                    'amortisation'
                ]
                
                keyword_score = sum(1 for item in key_items if item in table_text)
                
                # Must have at least 7 keywords (most ARR items)
                if keyword_score < 7:
                    continue
                
                # Check for FINANCIAL numbers
                financial_rows = sum(1 for row in table_data[1:] 
                                   if any(re.search(r'\d+\.?\d+', cell) for cell in row))
                
                if financial_rows < len(table_data) * 0.5:  # 50% threshold
                    continue
                
                # Check header has ARR-related keywords
                header_text = ' '.join(table_data[0]).lower() if table_data else ''
                header_score = 0
                if 'arr' in header_text:
                    header_score += 3
                if 'actual' in header_text or 'tu sought' in header_text:
                    header_score += 2
                if 'approval' in header_text or 'difference' in header_text:
                    header_score += 1
                
                # Combined score
                total_score = keyword_score + header_score
                
                # Bonus for having exactly 10-20 rows (typical ARR table)
                if 10 <= len(table_data) <= 20:
                    total_score += 3
                
                if total_score > best_score:
                    best_score = total_score
                    best_match = {
                        'page_num': page_num,
                        'table_data': table_data,
                        'score': keyword_score,
                        'start_page': page_num
                    }
        
        if not best_match or best_match['score'] < 7:
            print("   ARR table not found")
            return None
        
        # =====================================================================
        # Check if table continues on next page(s)
        # =====================================================================
        
        start_page_num = best_match['start_page']
        combined_table = best_match['table_data']
        
        print(f"   Found ARR table on page {start_page_num + 1} (score: {best_match['score']}/20 items)")
        
        # Check up to 3 subsequent pages for table continuation
        for continuation_page in range(start_page_num + 1, min(start_page_num + 4, self.num_pages)):
            page = self.pdf.pages[continuation_page]
            tables = page.extract_tables()
            
            if not tables:
                break  # No more tables, stop looking
            
            # Check if first table on this page is a continuation
            continuation_table = self._clean_table(tables[0])
            
            if not continuation_table or len(continuation_table) < 2:
                break
            
            # Heuristic: Is this a continuation?
            first_row_text = ' '.join(continuation_table[0]).lower() if continuation_table[0] else ''
            
            # If first row has "table" or "arr of", it's a new table, not continuation
            if 'table' in first_row_text or 'arr of' in first_row_text:
                break
            
            # Check column count matches (within 4 columns tolerance for merged cells)
            if abs(len(continuation_table[0]) - len(combined_table[0])) > 4:
                break
            
            # Check if has row numbers in first column (sign of data rows)
            has_row_numbers = any(
                row[0].strip().isdigit() 
                for row in continuation_table[:5] 
                if row and len(row) > 0 and row[0]
            )
            
            if not has_row_numbers:
                # Might be continuation but without row numbers
                # Check if has financial data
                has_numbers = any(
                    re.search(r'\d+\.?\d+', str(cell))
                    for row in continuation_table[:5]
                    for cell in row
                )
                if not has_numbers:
                    break
            
            # This looks like a continuation! Append rows (skip header if present)
            print(f"      Table continues on page {continuation_page + 1}")
            
            # Skip header rows in continuation (rows with "Particulars", "ARR", etc.)
            start_row = 0
            for i, row in enumerate(continuation_table):
                if len(row) > 2:
                    row_text = ' '.join(row).lower()
                    if 'particulars' in row_text or 'arr approval' in row_text:
                        start_row = i + 1
                        break
            
            # Append data rows
            combined_table.extend(continuation_table[start_row:])
        
        print(f"      Total rows extracted: {len(combined_table)}")
        
        # Update the match with combined table
        best_match['table_data'] = combined_table
        best_match['page_num'] = start_page_num  # Keep original page number
        
        return best_match
    
    # =========================================================================
    # CHAPTER 5 TABLE EXTRACTION
    # =========================================================================
    
    def _find_table_by_keywords_and_structure(
        self,
        title_keywords: List[str],
        column_keywords: List[str],
        start_page: int,
        end_page: int,
        min_rows: int = 3
    ) -> Optional[Dict]:
        """
        Generic intelligent table finder for Chapter 5 tables.
        Checks ALL tables on each page, not just the first one.
        NOW HANDLES MULTI-PAGE TABLES!
        
        Finds table by:
        1. Title keywords (e.g., "normative depreciation")
        2. Expected column headers (e.g., "SBU-G", "SBU-T")
        3. Minimum number of data rows
        4. Continues across multiple pages if needed
        
        Args:
            title_keywords: Keywords in table title
            column_keywords: Expected column headers
            start_page: Start search page
            end_page: End search page
            min_rows: Minimum number of rows
        
        Returns:
            Dict with table data and metadata, or None
        """
        print(f"   Searching for table with keywords: {', '.join(title_keywords[:2])}...")
        
        for page_num in range(start_page, min(end_page + 1, self.num_pages)):
            page = self.pdf.pages[page_num]
            
            # Extract tables from this page
            tables = page.extract_tables()
            
            if not tables:
                continue
            
            # Check EACH table on this page
            for table in tables:
                if not table or len(table) < min_rows:
                    continue
                
                table_data = self._clean_table(table)
                
                # Check if THIS TABLE has title keywords (in first few rows)
                table_title_text = ' '.join([' '.join(row) for row in table_data[:3]]).lower()
                
                # At least one keyword must match
                if not any(keyword.lower() in table_title_text for keyword in title_keywords):
                    continue
                
                # Check for expected column headers
                header_text = ' '.join(table_data[0] + table_data[1]).lower() if len(table_data) > 1 else ''
                matching_cols = sum(1 for kw in column_keywords if kw.lower() in header_text)
                
                if matching_cols < len(column_keywords) * 0.6:  # At least 60% match
                    continue
                
                # Found matching table! Now check for continuation on next page(s)
                print(f"      Found table on page {page_num + 1}")
                
                combined_table = table_data
                
                # Check up to 2 subsequent pages for continuation
                for continuation_page in range(page_num + 1, min(page_num + 3, self.num_pages)):
                    cont_page = self.pdf.pages[continuation_page]
                    cont_tables = cont_page.extract_tables()
                    
                    if not cont_tables:
                        break
                    
                    # Check first table on continuation page
                    cont_table = self._clean_table(cont_tables[0])
                    
                    if not cont_table or len(cont_table) < 2:
                        break
                    
                    # Check if this looks like a continuation
                    # Continuation typically doesn't have the table title again
                    first_row_text = ' '.join(cont_table[0]).lower()
                    if 'table' in first_row_text and any(kw.lower() in first_row_text for kw in title_keywords):
                        break  # New table, not continuation
                    
                    # Check column count similarity
                    if abs(len(cont_table[0]) - len(combined_table[0])) > 2:
                        break
                    
                    # This looks like continuation - append rows
                    print(f"      Table continues on page {continuation_page + 1}")
                    
                    # Skip header if present in continuation
                    start_row = 0
                    for i, row in enumerate(cont_table):
                        row_text = ' '.join(row).lower()
                        if 'particulars' in row_text or any(kw in row_text for kw in column_keywords):
                            start_row = i + 1
                            break
                    
                    combined_table.extend(cont_table[start_row:])
                
                print(f"      Total rows extracted: {len(combined_table)}")
                
                return {
                    'page_num': page_num,
                    'table_data': combined_table,
                    'confidence': min(matching_cols / len(column_keywords) * 100, 95)
                }
        
        print(f"      Table not found")
        return None
    
    def extract_depreciation_schedule(self) -> Dict:
        """
        Extract Table 5.27: Normative Depreciation for 2024-25.
        
        Extracts:
        - GFA opening by SBU
        - Asset age categories (13-30 years, below 13 years)
        - Asset additions
        - Asset withdrawals
        
        Returns:
            Dict with depreciation schedule data
        """
        print(" Extracting Depreciation Schedule (Table 5.27)...")
        
        # Search in Chapter 5 pages around table 5.27
        result = self._find_table_by_keywords_and_structure(
            title_keywords=['normative depreciation'],
            column_keywords=['sbu-g', 'sbu-t', 'sbu-d'],
            start_page=194,  # Page 195 (index 194)
            end_page=197,
            min_rows=10
        )
        
        if not result:
            return {'status': 'not_found', 'confidence': 0}
        
        # Extract specific values for SBU-G from table
        table_data = result['table_data']
        
        # Helper function to find value by row keyword
        def find_sbu_g_value(row_keywords: List[str]) -> Optional[float]:
            for row in table_data:
                row_text = ' '.join(row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    # Find SBU-G column (usually column 2)
                    for i, cell in enumerate(row):
                        if i >= 2 and re.match(r'^\d+\.?\d*$', cell.strip()):
                            try:
                                return float(cell.strip())
                            except ValueError:
                                continue
            return None
        
        # Extract key values with improved keywords
        gfa_opening = find_sbu_g_value(['approved gfa as on 31.03.2024', 'adjusted gfa as on 31.03.2024', 'gfa as on 31.03.2024'])
        gfa_13_30_years = find_sbu_g_value(['assets having life 13-30', '13-30 yrs', 'assets having age', '13 to 30'])
        gfa_below_13 = find_sbu_g_value(['gfa < 13 years old as on', '< 13 years old', 'gfa < 13'])
        asset_additions = find_sbu_g_value(['additions during the year', 'addition during', 'gfa addition'])
        asset_withdrawals = find_sbu_g_value(['withdrawal', 'retirement', 'disposal', 'less: disposal'])
        
        return {
            'status': 'found',
            'confidence': result['confidence'],
            'table': {
                'page_number': result['page_num'] + 1,
                'title': 'Table 5.27: Normative Depreciation',
                'data': table_data
            },
            'extracted_values': {
                'gfa_opening_total': gfa_opening,
                'gfa_13_to_30_years': gfa_13_30_years,
                'gfa_below_13_years': gfa_below_13,
                'asset_additions': asset_additions,
                'asset_withdrawals': asset_withdrawals or 0.0
            }
        }
    
    def extract_land_values(self) -> Dict:
        """
        Extract Table 5.28: Land value computation.
        
        Extracts land values for different asset age categories.
        
        Returns:
            Dict with land value data
        """
        print(" Extracting Land Values (Table 5.28)...")
        
        result = self._find_table_by_keywords_and_structure(
            title_keywords=['table', '5.28', 'land'],
            column_keywords=['sbu-g', 'sbu-t', 'sbu-d'],
            start_page=170,
            end_page=210,
            min_rows=3
        )
        
        if not result:
            # Land values might be in Table 5.27
            print("      Trying to extract from Table 5.27...")
            dep_schedule = self.extract_depreciation_schedule()
            if dep_schedule.get('status') == 'found':
                table_data = dep_schedule['table']['data']
                
                def find_land_value(row_keywords: List[str]) -> Optional[float]:
                    for row in table_data:
                        row_text = ' '.join(row).lower()
                        if any(kw.lower() in row_text for kw in row_keywords):
                            for i, cell in enumerate(row):
                                if i >= 2 and re.match(r'^\d+\.?\d*$', cell.strip()):
                                    try:
                                        return float(cell.strip())
                                    except ValueError:
                                        continue
                    return None
                
                land_13_30 = find_land_value(['value of land', 'land on having age between 13 to 30'])
                land_below_13 = find_land_value(['adjusted value of land', 'land (from 01.04.2011'])
                
                return {
                    'status': 'found',
                    'confidence': 70,
                    'table': dep_schedule['table'],
                    'extracted_values': {
                        'land_13_to_30_years': land_13_30,
                        'land_below_13_years': land_below_13
                    }
                }
            
            return {'status': 'not_found', 'confidence': 0}
        
        # Extract land values from dedicated table
        table_data = result['table_data']
        
        def find_land_value(row_keywords: List[str]) -> Optional[float]:
            for row in table_data:
                row_text = ' '.join(row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    for i, cell in enumerate(row):
                        if i >= 2 and re.match(r'^\d+\.?\d*$', cell.strip()):
                            try:
                                return float(cell.strip())
                            except ValueError:
                                continue
            return None
        
        return {
            'status': 'found',
            'confidence': result['confidence'],
            'table': {
                'page_number': result['page_num'] + 1,
                'title': 'Table 5.28: Land Values',
                'data': table_data
            },
            'extracted_values': {
                'land_13_to_30_years': find_land_value(['value of land', 'land on having age between 13 to 30']),
                'land_below_13_years': find_land_value(['adjusted value of land', 'land (from 01.04.2011'])
            }
        }
    
    def extract_grants_contributions(self) -> Dict:
        """
        Extract Table 5.29: Contributions and grants.
        
        Extracts grants/contributions for different asset age categories.
        
        Returns:
            Dict with grants data
        """
        print(" Extracting Grants/Contributions (Table 5.29)...")
        
        result = self._find_table_by_keywords_and_structure(
            title_keywords=['table', '5.29', 'grants', 'contributions'],
            column_keywords=['sbu-g', 'sbu-t', 'sbu-d'],
            start_page=170,
            end_page=210,
            min_rows=3
        )
        
        if not result:
            # Grants might be in Table 5.27
            print("      Trying to extract from Table 5.27...")
            dep_schedule = self.extract_depreciation_schedule()
            if dep_schedule.get('status') == 'found':
                table_data = dep_schedule['table']['data']
                
                def find_grants_value(row_keywords: List[str]) -> Optional[float]:
                    for row in table_data:
                        row_text = ' '.join(row).lower()
                        if any(kw.lower() in row_text for kw in row_keywords):
                            for i, cell in enumerate(row):
                                if i >= 2 and re.match(r'^\d+\.?\d*$', cell.strip()):
                                    try:
                                        return float(cell.strip())
                                    except ValueError:
                                        continue
                    return None
                
                grants_13_30 = find_grants_value(['grants and contributions on assets having life from 13 to 30', 'grants and contributions till 31.03.2011']) or 0.0
                grants_below_13 = find_grants_value(['grants and contributions (1-4-2011 to 31-3-2024)', 'grants and contributions till', 'grants and contributions (1-4-2011']) or 0.0
                
                return {
                    'status': 'found',
                    'confidence': 70,
                    'table': dep_schedule['table'],
                    'extracted_values': {
                        'grants_13_to_30_years': grants_13_30 or 0.0,
                        'grants_below_13_years': grants_below_13 or 0.0
                    }
                }
            
            return {'status': 'not_found', 'confidence': 0}
        
        # Extract from dedicated table
        table_data = result['table_data']
        
        def find_grants_value(row_keywords: List[str]) -> Optional[float]:
            for row in table_data:
                row_text = ' '.join(row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    for i, cell in enumerate(row):
                        if i >= 2 and re.match(r'^\d+\.?\d*$', cell.strip()):
                            try:
                                return float(cell.strip())
                            except ValueError:
                                continue
            return None
        
        return {
            'status': 'found',
            'confidence': result['confidence'],
            'table': {
                'page_number': result['page_num'] + 1,
                'title': 'Table 5.29: Grants/Contributions',
                'data': table_data
            },
            'extracted_values': {
                'grants_13_to_30_years': find_grants_value(['grants and contributions on assets having life from 13 to 30', 'grants and contributions till 31.03.2011']) or 0.0,
                'grants_below_13_years': find_grants_value(['grants and contributions (1-4-2011 to 31-3-2024)', 'grants and contributions (1-4-2011']) or 0.0
            }
        }
    
    def extract_gfa_additions(self) -> Dict:
        """
        Extract Table 5.7 or 5.8: GFA additions for SBU-G.
        
        Extracts asset additions during the year.
        
        Returns:
            Dict with GFA additions data
        """
        print(" Extracting GFA Additions (Table 5.7/5.8)...")
        
        # Try Table 5.8 first (SBU-G specific)
        result = self._find_table_by_keywords_and_structure(
            title_keywords=['table', '5.8', 'gfa addition', 'sbu g'],
            column_keywords=['gfa', 'addition'],
            start_page=170,
            end_page=195,
            min_rows=3
        )
        
        if not result:
            # Try Table 5.7 (SBU-wise)
            result = self._find_table_by_keywords_and_structure(
                title_keywords=['table', '5.7', 'gfa addition', 'sbu wise'],
                column_keywords=['sbu-g', 'sbu-t', 'sbu-d'],
                start_page=170,
                end_page=195,
                min_rows=3
            )
        
        if not result:
            return {'status': 'not_found', 'confidence': 0}
        
        table_data = result['table_data']
        
        # Extract total GFA addition for SBU-G
        def find_addition_value() -> Optional[float]:
            for row in table_data:
                # Look for row with "Generation" in column 1
                if len(row) > 1 and 'generation' in str(row[1]).lower():
                    # GFA Addition is in column 4
                    if len(row) > 4:
                        cell = row[4].strip().replace(',', '')
                        try:
                            return float(cell)
                        except (ValueError, AttributeError):
                            pass
            return None
        
        return {
            'status': 'found',
            'confidence': result['confidence'],
            'table': {
                'page_number': result['page_num'] + 1,
                'title': 'Table 5.7/5.8: GFA Additions',
                'data': table_data
            },
            'extracted_values': {
                'asset_additions': find_addition_value()
            }
        }
    
    # =========================================================================
    # NARRATIVE EXTRACTION
    # =========================================================================
    
    def _extract_section_text(
        self,
        section_number: str,
        start_page: int = 0
    ) -> Tuple[str, str]:
        """
        Extract all text for a given section number.
        
        Args:
            section_number: Section like "3.2.1" or "3.2"
            start_page: Page to start searching
        
        Returns:
            Tuple of (section_title, full_section_text)
        """
        section_pattern = rf'^{re.escape(section_number)}\s+(.+?)$'
        next_section_pattern = rf'^\d+\.\d+\.?\d*\s+'  # Any section number
        
        section_text = ""
        section_title = ""
        in_section = False
        
        for page_num in range(start_page, self.num_pages):
            page = self.pdf.pages[page_num]
            page_text = page.extract_text() or ""
            lines = page_text.split('\n')
            
            for line in lines:
                # Check if this is our section start
                match = re.match(section_pattern, line.strip(), re.IGNORECASE)
                if match:
                    in_section = True
                    section_title = match.group(1).strip()
                    section_text += line + '\n'
                    continue
                
                # If in section, collect text
                if in_section:
                    # Check if next section started
                    if re.match(next_section_pattern, line.strip()):
                        # Different section - stop
                        different_section = not line.strip().startswith(section_number)
                        if different_section:
                            return section_title, section_text
                    
                    section_text += line + '\n'
        
        return section_title, section_text
    
    def _parse_variance_explanation(self, text: str) -> Dict:
        """
        Parse variance explanation from narrative text.
        
        Extracts:
        - Variance amount and percentage
        - Reasons (bullet points)
        - Force majeure claims
        - Supporting documents
        - Regulatory references
        """
        explanation = {
            'variance_amount': None,
            'variance_percentage': None,
            'reasons': [],
            'force_majeure_claimed': False,
            'supporting_docs': [],
            'regulatory_refs': []
        }
        
        # Extract variance amount
        variance_patterns = [
            r'variance of\s*(\d+\.?\d*)\s*Cr',
            r'excess.*?(\d+\.?\d*)\s*Cr',
            r'shortfall.*?(\d+\.?\d*)\s*Cr'
        ]
        for pattern in variance_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                explanation['variance_amount'] = float(match.group(1))
                break
        
        # Extract variance percentage
        pct_match = re.search(r'(\d+\.?\d*)%', text)
        if pct_match:
            explanation['variance_percentage'] = float(pct_match.group(1))
        
        # Extract reasons (look for bullet points or numbered lists)
        reason_patterns = [
            r'\(([a-z])\)\s*([^\n]+)',  # (a) reason
            r'(\d+)\.\s*([^\n]+)',       # 1. reason
            r'[-]\s*([^\n]+)'           # - reason
        ]
        
        for pattern in reason_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                reason = match.group(2) if match.lastindex > 1 else match.group(1)
                # Only add if looks like a reason (has some length)
                if len(reason.strip()) > 10:
                    explanation['reasons'].append(reason.strip())
        
        # Detect force majeure
        force_majeure_keywords = [
            'force majeure', 'unforeseen', 'extraordinary',
            'beyond control', 'natural calamity', 'unprecedented'
        ]
        explanation['force_majeure_claimed'] = any(
            kw in text.lower() for kw in force_majeure_keywords
        )
        
        # Extract supporting documents
        annexure_pattern = r'Annexure[- ](\d+\.?\d*[a-zA-Z]?)'
        explanation['supporting_docs'] = list(set(
            re.findall(annexure_pattern, text, re.IGNORECASE)
        ))
        
        # Extract regulatory references
        reg_patterns = [
            r'Regulation\s+(\d+)',
            r'Section\s+(\d+)',
            r'Order dated\s+(\d{2}\.\d{2}\.\d{4})',
            r'OP\s+No\.?\s*(\d+/\d{4})'
        ]
        for pattern in reg_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            explanation['regulatory_refs'].extend(matches)
        
        return explanation
    
    # =========================================================================
    # LINE ITEM EXTRACTORS - SBU-G
    # =========================================================================
    
    def extract_roe(self) -> Dict:
        """
        Extract Return on Equity data.
        
        Looks for:
        - ARR table with ROE line item
        - Section text explaining ROE
        
        Returns:
            Dictionary with extracted ROE data + context
        """
        print(" Extracting ROE data...")
        
        # Find ARR table using content-based detection
        summary = self._find_summary_table()
        
        if not summary:
            return {'status': 'not_found', 'confidence': 0}
        
        roe_table = TableMatch(
            page_number=summary['page_num'],
            table_data=summary['table_data'],
            table_title=f"ARR Table (Page {summary['page_num'] + 1})",
            confidence=min(summary['score'] * 5, 95.0)
        )
        
        print(f" Found ROE table on page {roe_table.page_number + 1} "
              f"(confidence: {roe_table.confidence:.0f}%)")
        
        # Extract section text (look for section about ROE)
        section_patterns = [r'3\.\d+\.\d*', r'ROE', r'Return on Equity']
        section_title = ""
        section_text = ""
        
        # Try to find section discussing ROE
        for page_num in range(max(0, roe_table.page_number - 2), 
                               min(self.num_pages, roe_table.page_number + 3)):
            page = self.pdf.pages[page_num]
            text = page.extract_text() or ""
            
            if any(re.search(p, text, re.IGNORECASE) for p in section_patterns):
                # Found relevant section
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if 'return on equity' in line.lower() or 'roe' in line.lower():
                        # Start collecting from here
                        section_text = '\n'.join(lines[i:min(i+50, len(lines))])
                        break
                if section_text:
                    break
        
        # Parse variance explanation if present
        variance_explanation = None
        if section_text:
            variance_explanation = self._parse_variance_explanation(section_text)
        
        return {
            'status': 'found',
            'confidence': roe_table.confidence,
            'table': {
                'page_number': roe_table.page_number + 1,
                'title': roe_table.table_title,
                'data': roe_table.table_data
            },
            'context': {
                'section_text': section_text,
                'variance_explanation': variance_explanation
            },
            'metadata': self.metadata
        }
    
    def extract_depreciation(self) -> Dict:
        """Extract Depreciation data"""
        print(" Extracting Depreciation data...")
        
        # Find ARR table
        summary = self._find_summary_table()
        
        if not summary:
            return {'status': 'not_found', 'confidence': 0}
        
        depr_table = TableMatch(
            page_number=summary['page_num'],
            table_data=summary['table_data'],
            table_title=f"ARR Table (Page {summary['page_num'] + 1})",
            confidence=min(summary['score'] * 5, 95.0)
        )
        
        print(f" Found Depreciation table on page {depr_table.page_number + 1}")
        
        # Extract context (similar to ROE)
        section_text = ""
        for page_num in range(max(0, depr_table.page_number - 2), 
                               min(self.num_pages, depr_table.page_number + 3)):
            page = self.pdf.pages[page_num]
            text = page.extract_text() or ""
            if 'depreciation' in text.lower():
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if 'depreciation' in line.lower():
                        section_text = '\n'.join(lines[i:min(i+50, len(lines))])
                        break
                if section_text:
                    break
        
        variance_explanation = None
        if section_text:
            variance_explanation = self._parse_variance_explanation(section_text)
        
        return {
            'status': 'found',
            'confidence': depr_table.confidence,
            'table': {
                'page_number': depr_table.page_number + 1,
                'title': depr_table.table_title,
                'data': depr_table.table_data
            },
            'context': {
                'section_text': section_text,
                'variance_explanation': variance_explanation
            },
            'metadata': self.metadata
        }
    
    def extract_fuel_costs(self) -> Dict:
        """Extract Fuel Costs data"""
        print(" Extracting Fuel Costs data...")
        
        # Get SBU-G boundaries
        boundaries = self._detect_sbu_boundaries()
        
        if 'sbu_g' in boundaries:
            start_page, end_page = boundaries['sbu_g']
        else:
            start_page, end_page = 0, self.num_pages
        
        table_patterns = [
            r'Table\s*[G-]?\s*\d+.*Fuel',
            r'Fuel.*Cost',
            r'Fuel.*Expense',
            r'Cost.*Generation'
        ]
        
        fuel_table = self._find_table_by_patterns(table_patterns, start_page, end_page)
        
        if not fuel_table:
            print("  Fuel costs table not found")
            return {'status': 'not_found', 'confidence': 0}
        
        print(f" Found Fuel table on page {fuel_table.page_number + 1}")
        
        return {
            'status': 'found',
            'confidence': fuel_table.confidence,
            'table': {
                'page_number': fuel_table.page_number + 1,
                'title': fuel_table.table_title,
                'data': fuel_table.table_data
            },
            'metadata': self.metadata
        }
    
    def extract_other_expenses(self) -> Dict:
        """Extract Other Expenses from ARR table"""
        print(" Extracting Other Expenses...")
        return self._extract_from_summary_table('other', 'Other Expenses')
    
    def extract_exceptional_items(self) -> Dict:
        """Extract Exceptional Items from ARR table"""
        print(" Extracting Exceptional Items...")
        return self._extract_from_summary_table('exceptional', 'Exceptional Items')
    
    def extract_intangibles(self) -> Dict:
        """Extract Intangible Assets from ARR table"""
        print(" Extracting Intangible Assets...")
        return self._extract_from_summary_table('intangible', 'Intangible Assets')
    
    def extract_nti(self) -> Dict:
        """Extract Non-Tariff Income from ARR table"""
        print(" Extracting Non-Tariff Income...")
        return self._extract_from_summary_table('nti', 'Non-Tariff Income')
    
    def extract_master_trust(self) -> Dict:
        """Extract Master Trust from ARR table"""
        print(" Extracting Master Trust...")
        return self._extract_from_summary_table('master_trust', 'Master Trust')
    
    def extract_ifc(self) -> Dict:
        """Extract Interest & Finance Charges from ARR table"""
        print(" Extracting Interest & Finance Charges...")
        return self._extract_from_summary_table('ifc', 'Interest & Finance Charges')
    
    def extract_om_expenses(self) -> Dict:
        """Extract O&M Expenses from ARR table"""
        print(" Extracting O&M Expenses...")
        return self._extract_from_summary_table('om', 'O&M Expenses')
    
    def _extract_from_summary_table(self, item_key: str, search_term: str) -> Dict:
        """
        Helper: Extract any item from ARR table.
        Uses content-based detection!
        """
        # Find ARR table
        summary = self._find_summary_table()
        
        if not summary:
            return {'status': 'not_found', 'confidence': 0}
        
        return {
            'status': 'found',
            'confidence': min(summary['score'] * 5, 95.0),
            'table': {
                'page_number': summary['page_num'] + 1,
                'title': f'ARR Table - {search_term}',
                'data': summary['table_data']
            },
            'context': {}
        }
    
    # =========================================================================
    # FUEL DETAIL EXTRACTION (Table G9 - in SBU-G chapter)
    # =========================================================================

    def extract_fuel_detail(self) -> Dict:
        """
        Extract Table G9: Station wise Cost of Generation (Rs Cr).
        Located in the SBU-G chapter (pages ~17-18), NOT Chapter 5.

        Columns: Station | Heavy Fuel Oil | HSD Oil | Lub. Oil |
                 For Hydel Power Gen | For IC Power Gen | TOTAL
        Rows: One per station, then a TOTAL row.

        Returns:
            Dict with per-station fuel breakdown and column totals
        """
        print(" Extracting Fuel Detail (Table G9)...")

        # Search within SBU-G section boundaries
        boundaries = self._detect_sbu_boundaries()
        if 'sbu_g' not in boundaries:
            print("   WARNING: SBU-G boundaries not found, searching full doc")
            start_page, end_page = 0, self.num_pages
        else:
            start_page, end_page = boundaries['sbu_g']

        result = self._find_table_by_keywords_and_structure(
            title_keywords=['table', 'g9', 'station wise cost', 'cost of generation'],
            column_keywords=['station', 'lub. oil'],
            start_page=start_page,
            end_page=end_page,
            min_rows=3
        )

        if not result:
            return {'status': 'not_found', 'confidence': 0}

        table_data = result['table_data']

        def _parse_numeric(cell: str) -> float:
            try:
                return float(str(cell).strip().replace(',', ''))
            except (ValueError, AttributeError):
                return 0.0

        # Parse station rows and find TOTAL row
        # Columns: Station | HFO | HSD | LubOil | Hydel | IC | TOTAL
        station_breakdown = []
        totals = {'hfo': 0.0, 'hsd': 0.0, 'lube_oil': 0.0,
                  'hydel': 0.0, 'ic': 0.0, 'total': 0.0}

        for row in table_data:
            if not row or len(row) < 6:
                continue

            first_cell = str(row[0]).strip().lower() if row[0] else ''

            # Skip header rows
            if any(kw in first_cell for kw in ['station', 'heavy', 'h.s.d', 'furnace',
                                                 'lub.', 'hydel', 'combustion', 'table']):
                continue
            # Skip empty first cell (continuation of multi-line header)
            if not first_cell:
                continue

            # Try parsing numeric values — need at least the TOTAL column
            nums = [_parse_numeric(row[i]) if i < len(row) else 0.0 for i in range(1, 7)]
            row_total = nums[5]  # last column = TOTAL

            is_total_row = 'total' in first_cell

            if is_total_row:
                totals = {
                    'hfo':      nums[0],
                    'hsd':      nums[1],
                    'lube_oil': nums[2],
                    'hydel':    nums[3],
                    'ic':       nums[4],
                    'total':    nums[5],
                }
                break
            else:
                # Only add if row has any non-zero value
                if any(n > 0 for n in nums):
                    station_breakdown.append({
                        'station':  str(row[0]).strip(),
                        'hfo':      nums[0],
                        'hsd':      nums[1],
                        'lube_oil': nums[2],
                        'hydel':    nums[3],
                        'ic':       nums[4],
                        'total':    nums[5],
                    })

        return {
            'status': 'found',
            'confidence': result['confidence'],
            'table': {
                'page_number': result['page_num'] + 1,
                'title': 'Table G9: Station wise Cost of Generation',
                'data': table_data
            },
            'extracted_values': {
                'station_breakdown': station_breakdown,
                'heavy_fuel_oil':    totals['hfo'],
                'hsd_oil':           totals['hsd'],
                'lube_oil':          totals['lube_oil'],
                'hydel_power_gen':   totals['hydel'],
                'ic_power_gen':      totals['ic'],
                'total_fuel_cost':   totals['total'],
            }
        }

    # =========================================================================
    # O&M DETAIL EXTRACTION (Tables 5.37, 5.38, 5.39, 5.40)
    # =========================================================================

    def extract_om_detail(self) -> Dict:
        """
        Extract O&M expense breakdown from Chapter 5:
          Table 5.37 - O&M expenses total
          Table 5.38 - Gross Employee Cost
          Table 5.39 - R&M Expenses
          Table 5.40 - Administrative & General Expenses

        All are on pages 201-202 (index 200-201).

        Returns:
            Dict with O&M component breakdown
        """
        print(" Extracting O&M Detail (Tables 5.37-5.40)...")

        CH5_START = 175   # Chapter 5 starts around page 177 (index 176)
        CH5_END   = 215

        def _find_om_table(title_kws, col_kws, label):
            r = self._find_table_by_keywords_and_structure(
                title_keywords=title_kws,
                column_keywords=col_kws,
                start_page=CH5_START,
                end_page=CH5_END,
                min_rows=3
            )
            if r:
                print(f"      Found {label} on page {r['page_num'] + 1}")
            else:
                print(f"      {label} not found")
            return r

        def _get_sbu_g_value(table_data, row_keywords):
            """Extract SBU-G column value from a row matching row_keywords."""
            for row in table_data:
                row_text = ' '.join(row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    # SBU-G column is typically col index 1 or 2
                    for i in range(1, min(5, len(row))):
                        cell = str(row[i]).strip().replace(',', '')
                        try:
                            return float(cell)
                        except ValueError:
                            continue
            return None

        def _get_total_value(table_data, row_keywords):
            """Extract TOTAL column (last numeric col) from matching row."""
            for row in table_data:
                row_text = ' '.join(row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    # Walk from right to left to find last numeric cell
                    for cell in reversed(row):
                        c = str(cell).strip().replace(',', '')
                        try:
                            return float(c)
                        except ValueError:
                            continue
            return None

        # --- Table 5.37: O&M Summary ---
        r537 = _find_om_table(
            ['5.37', 'details of o&m', 'o&m expenses 2024'],
            ['employee', 'r&m', 'total'],
            'Table 5.37'
        )

        # --- Table 5.38: Employee Cost ---
        r538 = _find_om_table(
            ['5.38', 'gross employee cost'],
            ['employee', 'gross', 'total'],
            'Table 5.38'
        )

        # --- Table 5.39: R&M ---
        r539 = _find_om_table(
            ['5.39', 'r&m expenses'],
            ['r&m', 'repair', 'total'],
            'Table 5.39'
        )

        # --- Table 5.40: A&G ---
        r540 = _find_om_table(
            ['5.40', 'administrative', 'general expenses'],
            ['administrative', 'general', 'total'],
            'Table 5.40'
        )

        if not r537 and not r538 and not r539 and not r540:
            return {'status': 'not_found', 'confidence': 0}

        # Use 5.37 as primary if found, else fall back to sub-tables
        t537 = r537['table_data'] if r537 else []
        t538 = r538['table_data'] if r538 else []
        t539 = r539['table_data'] if r539 else []
        t540 = r540['table_data'] if r540 else []

        # Extract component totals — prefer 5.37 summary, fall back to sub-tables
        # Use simple 'total' keyword since each sub-table has a clear Total row
        employee_cost = (_get_total_value(t537, ['employee cost', 'employee expenses'])
                         or _get_total_value(t538, ['total']))
        rm_cost       = (_get_total_value(t537, ['r&m', 'repair and maintenance'])
                         or _get_total_value(t539, ['total']))
        ag_cost       = (_get_total_value(t537, ['administrative', 'a&g'])
                         or _get_total_value(t540, ['total']))
        om_total      = (_get_total_value(t537, ['total', 'om total'])
                         or sum(filter(None, [employee_cost, rm_cost, ag_cost])) or None)

        # Detailed breakdowns from sub-tables if available
        basic_pay       = _get_total_value(t538, ['basic pay', 'basic salary']) if t538 else None
        da              = _get_total_value(t538, ['dearness allowance', ' da ']) if t538 else None
        hra             = _get_total_value(t538, ['hra', 'house rent']) if t538 else None

        civil_rm        = _get_total_value(t539, ['civil', 'building']) if t539 else None
        plant_rm        = _get_total_value(t539, ['plant', 'machinery', 'electrical']) if t539 else None

        primary = r537 or r538 or r539 or r540

        return {
            'status': 'found',
            'confidence': primary['confidence'],
            'table': {
                'page_number': primary['page_num'] + 1,
                'title': 'Tables 5.37-5.40: O&M Expenses Detail',
                'data': primary['table_data']
            },
            'extracted_values': {
                'employee_cost':    employee_cost,
                'rm_expenses':      rm_cost,
                'ag_expenses':      ag_cost,
                'om_total':         om_total,
                # Sub-breakdowns (may be None if sub-tables not found)
                'basic_pay':        basic_pay,
                'da':               da,
                'hra':              hra,
                'civil_rm':         civil_rm,
                'plant_rm':         plant_rm,
            }
        }

    # =========================================================================
    # IFC DETAIL EXTRACTION (Tables 5.1, 5.3, 5.22)
    # =========================================================================

    def extract_ifc_detail(self) -> Dict:
        """
        Extract Interest & Finance Charges breakdown from Chapter 5:
          Table 5.1  - IFC summary by component
          Table 5.3  - Loans, interest, and average rate
          Table 5.22 - Detailed IFC breakdown

        Pages 177-193 (index 176-192).

        Returns:
            Dict with IFC component breakdown
        """
        print(" Extracting IFC Detail (Tables 5.1, 5.3, 5.22)...")

        CH5_START = 175
        CH5_END   = 200

        def _find_ifc_table(title_kws, col_kws, label):
            r = self._find_table_by_keywords_and_structure(
                title_keywords=title_kws,
                column_keywords=col_kws,
                start_page=CH5_START,
                end_page=CH5_END,
                min_rows=3
            )
            if r:
                print(f"      Found {label} on page {r['page_num'] + 1}")
            else:
                print(f"      {label} not found")
            return r

        def _get_value(table_data, row_keywords, col_index=None):
            """
            Extract value from table by matching row keywords.
            If col_index is given, use that column; else use last numeric cell.
            """
            for row in table_data:
                row_text = ' '.join(row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    if col_index is not None and col_index < len(row):
                        cell = str(row[col_index]).strip().replace(',', '')
                        try:
                            return float(cell)
                        except ValueError:
                            pass
                    # Fallback: last numeric cell
                    for cell in reversed(row):
                        c = str(cell).strip().replace(',', '')
                        try:
                            return float(c)
                        except ValueError:
                            continue
            return None

        # --- Table 5.1: IFC Summary (columns use 'G UBS' not 'SBU-G') ---
        r51 = _find_ifc_table(
            ['5.1', 'interests and finance charges', 'interest and finance'],
            ['ubs', 'total'],
            'Table 5.1'
        )

        # --- Table 5.3: Loan summary ---
        r53 = _find_ifc_table(
            ['5.3', 'summary of loans', 'loan', 'average rate'],
            ['loan', 'interest', 'average rate'],
            'Table 5.3'
        )

        # --- Table 5.22: Detailed IFC (columns use 'SBU G' with space not hyphen) ---
        r522 = _find_ifc_table(
            ['5.22', 'interests and finance charges'],
            ['sbu g', 'sbu t', 'total'],
            'Table 5.22'
        )

        # --- Table G10: SBU-G specific IFC (in SBU-G chapter, page ~18) ---
        boundaries = self._detect_sbu_boundaries()
        g_start, g_end = boundaries.get('sbu_g', (0, 30))
        rg10 = self._find_table_by_keywords_and_structure(
            title_keywords=['table g 10', 'table g10', 'interest and finance charges'],
            column_keywords=['approved', 'actual', 'tu'],
            start_page=g_start,
            end_page=g_end,
            min_rows=5
        )
        if rg10:
            print(f"      Found Table G10 on page {rg10['page_num'] + 1}")

        if not r51 and not rg10:
            return {'status': 'not_found', 'confidence': 0}

        t51  = r51['table_data']  if r51  else []
        t53  = r53['table_data']  if r53  else []
        t522 = r522['table_data'] if r522 else []
        tg10 = rg10['table_data'] if rg10 else []

        # Helper: get SBU-G column value (col index 1) from matching row
        def _sbu_g_col(table_data, row_keywords):
            for row in table_data:
                row_text = ' '.join(str(c) for c in row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    for i in range(1, min(5, len(row))):
                        c = str(row[i]).strip().replace(',', '') if row[i] else ''
                        try:
                            return float(c)
                        except ValueError:
                            continue
            return None

        # From Table G10 (SBU-G specific, TU column = index 4)
        def _g10_tu_value(row_keywords):
            for row in tg10:
                row_text = ' '.join(str(c) for c in row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    # G10 columns: No | Particulars | Approved | Actual | TU | Difference
                    if len(row) > 4:
                        c = str(row[4]).strip().replace(',', '') if row[4] else ''
                        try:
                            return float(c)
                        except ValueError:
                            pass
                    # fallback to last numeric
                    for cell in reversed(row):
                        c = str(cell).strip().replace(',', '') if cell else ''
                        try:
                            return float(c)
                        except ValueError:
                            continue
            return None

        # IFC components — prefer G10 (SBU-G specific TU values)
        term_loan_interest  = _g10_tu_value(['interest on capital', 'term loan', 'capital liabilities'])
        gpf_interest        = _g10_tu_value(['gpf', 'general provident', 'pf interest'])
        wc_interest         = _g10_tu_value(['working capital', 'wc/od', 'working capital'])
        master_trust_int    = _g10_tu_value(['master trust', 'trust bond'])
        other_charges       = _g10_tu_value(['other interest', 'other charges'])
        ifc_subtotal        = _g10_tu_value(['sub total', 'subtotal', 'balance'])

        # From Table 5.1 — SBU-G approval column (col 1)
        term_loan_approved  = _sbu_g_col(t51, ['interest on term loan', 'term loan'])
        carrying_cost       = _sbu_g_col(t51, ['carrying cost'])

        # Average interest rate from Table 5.3
        avg_interest_rate = None
        if t53:
            for row in t53:
                row_text = ' '.join(str(c) for c in row).lower()
                if 'average rate' in row_text or 'weighted average' in row_text:
                    for cell in reversed(row):
                        c = str(cell).strip().replace(',', '') if cell else ''
                        try:
                            avg_interest_rate = float(c)
                            break
                        except ValueError:
                            continue
                    if avg_interest_rate:
                        break

        # SBU-G TU total from Table 5.22 (col 5 = SBU G TU)
        sbu_g_ifc_total = None
        if t522:
            for row in t522:
                if not row or len(row) < 6:
                    continue
                row_text = ' '.join(str(c) for c in row if c).lower()
                if 'gross total' in row_text or ('total' in row_text and 'less' not in row_text):
                    c = str(row[5]).strip().replace(',', '') if row[5] else ''
                    try:
                        sbu_g_ifc_total = float(c)
                        break
                    except ValueError:
                        pass

        primary = r51 or rg10
        return {
            'status': 'found',
            'confidence': primary['confidence'],
            'table': {
                'page_number': primary['page_num'] + 1,
                'title': 'Tables 5.1/5.3/5.22/G10: IFC Detail',
                'data': primary['table_data']
            },
            'extracted_values': {
                'term_loan_interest':  term_loan_interest,
                'gpf_interest':        gpf_interest,
                'wc_interest':         wc_interest,
                'master_trust_int':    master_trust_int,
                'other_charges':       other_charges,
                'ifc_subtotal':        ifc_subtotal,
                'term_loan_approved':  term_loan_approved,
                'carrying_cost':       carrying_cost,
                'avg_interest_rate':   avg_interest_rate,
                'sbu_g_ifc_total':     sbu_g_ifc_total,
                # Compute total from components if subtotal not found
                'ifc_total':           ifc_subtotal or (
                    sum(filter(None, [term_loan_interest, gpf_interest,
                                      wc_interest, master_trust_int, other_charges]))
                    or None
                ),
            }
        }

    # =========================================================================
    # MASTER TRUST DETAIL EXTRACTION (Tables 5.17, 5.25, 5.26)
    # =========================================================================

    def extract_master_trust_detail(self) -> Dict:
        """
        Extract Master Trust breakdown from Chapter 5:
          Table 5.17 - Interest on Master Trust Bonds (pg 191)
          Table 5.25 - Additional Contribution to Master Trust Bonds (pg 194)
          Table 5.26 - Repayment of Master Trust Bonds (pg 195)
        """
        print(" Extracting Master Trust Detail (Tables 5.17, 5.25, 5.26)...")

        CH5_START = 175
        CH5_END   = 205

        def _find(title_kws, col_kws, label):
            r = self._find_table_by_keywords_and_structure(
                title_keywords=title_kws,
                column_keywords=col_kws,
                start_page=CH5_START,
                end_page=CH5_END,
                min_rows=2
            )
            print(f"      {'Found' if r else 'Not found'}: {label}" +
                  (f" on page {r['page_num'] + 1}" if r else ""))
            return r

        def _sbu_g_value(table_data, row_keywords):
            for row in table_data:
                row_text = ' '.join(row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    for i in range(1, min(4, len(row))):
                        c = str(row[i]).strip().replace(',', '')
                        try:
                            return float(c)
                        except ValueError:
                            continue
            return None

        r517 = _find(
            ['5.17', 'interest on master trust bonds', 'master trust bond'],
            ['sbu g', 'sbu t', 'total'],
            'Table 5.17'
        )
        # 5.25 and 5.26 don't exist in this petition — 5.17 is sufficient
        r525 = None
        r526 = None

        if not r517:
            return {'status': 'not_found', 'confidence': 0}

        t517 = r517['table_data']
        t525 = r525['table_data'] if r525 else []
        t526 = r526['table_data'] if r526 else []

        bond_interest      = _sbu_g_value(t517, ['total', 'interest'])
        additional_contrib = _sbu_g_value(t525, ['total', 'additional', 'contribution']) if t525 else None
        repayment          = _sbu_g_value(t526, ['total', 'repayment'])                  if t526 else None

        mt_total = None
        if bond_interest is not None and additional_contrib is not None:
            mt_total = round(bond_interest + additional_contrib, 2)

        return {
            'status': 'found',
            'confidence': r517['confidence'],
            'table': {
                'page_number': r517['page_num'] + 1,
                'title': 'Tables 5.17/5.25/5.26: Master Trust Detail',
                'data': t517
            },
            'extracted_values': {
                'bond_interest':      bond_interest,
                'additional_contrib': additional_contrib,
                'bond_repayment':     repayment,
                'mt_total_computed':  mt_total,
            }
        }

    # =========================================================================
    # NTI DETAIL EXTRACTION (Tables 5.49, 5.51)
    # =========================================================================

    def extract_nti_detail(self) -> Dict:
        """
        Extract Non-Tariff Income breakdown from Chapter 5:
          Table 5.49 - Non-tariff income for 2024-25 (pg 208-209)
          Table 5.51 - Non-tariff income for 2024-25 (pg 211)
        """
        print(" Extracting NTI Detail (Tables 5.49, 5.51)...")

        CH5_START = 205
        CH5_END   = 215

        def _find(title_kws, col_kws, label):
            r = self._find_table_by_keywords_and_structure(
                title_keywords=title_kws,
                column_keywords=col_kws,
                start_page=CH5_START,
                end_page=CH5_END,
                min_rows=3
            )
            print(f"      {'Found' if r else 'Not found'}: {label}" +
                  (f" on page {r['page_num'] + 1}" if r else ""))
            return r

        def _get_value(table_data, row_keywords):
            for row in table_data:
                row_text = ' '.join(row).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    for cell in reversed(row):
                        c = str(cell).strip().replace(',', '')
                        try:
                            return float(c)
                        except ValueError:
                            continue
            return None

        r549 = _find(
            ['5.49', 'non-tariff income', 'non tariff income'],
            ['sbu g', 'sbu t', 'total'],
            'Table 5.49'
        )
        r551 = _find(
            ['5.51', 'non-tariff income', 'non tariff income'],
            ['approved', 'actuals', 'claimed'],
            'Table 5.51'
        )

        if not r549 and not r551:
            return {'status': 'not_found', 'confidence': 0}

        primary = r549 or r551
        t549 = r549['table_data'] if r549 else []
        t551 = r551['table_data'] if r551 else []

        def _sbu_g_nti(table_data, row_keywords):
            """Get SBU-G value (col 2) from matching row in 5.49."""
            for row in table_data:
                if not row:
                    continue
                row_text = ' '.join(str(c) for c in row if c).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    # Col 2 = SBU G in 5.49 layout
                    if len(row) > 2:
                        c = str(row[2]).strip().replace(',', '') if row[2] else ''
                        try:
                            return float(c)
                        except ValueError:
                            pass
                    # fallback: first numeric cell after col 0,1
                    for cell in row[2:]:
                        c = str(cell).strip().replace(',', '') if cell else ''
                        try:
                            return float(c)
                        except ValueError:
                            continue
            return None

        return {
            'status': 'found',
            'confidence': primary['confidence'],
            'table': {
                'page_number': primary['page_num'] + 1,
                'title': 'Tables 5.49/5.51: NTI Detail',
                'data': primary['table_data']
            },
            'extracted_values': {
                'misc_receipts':    _sbu_g_nti(t549, ['miscellaneous receipts', 'performance incentive', 'misc receipts']),
                'interest_income':  _sbu_g_nti(t549, ['interest-advance', 'interest income', 'interest from banks']),
                'sale_income':      _sbu_g_nti(t549, ['income from sale', 'sale of scrap']),
                'sub_total_b':      _sbu_g_nti(t549, ['sub total (b)', 'sub total b']),
                'sub_total_c':      _sbu_g_nti(t549, ['sub total (c)', 'sub total c']),
                'nti_total':        _sbu_g_nti(t549, ['income as per accounts', 'd=', 'total non-tariff']),
                'nti_approved_551': _get_value(t551, ['approved', 'arr approved']) if t551 else None,
                'nti_claimed_551':  _get_value(t551, ['claimed', 'tu sought'])     if t551 else None,
            }
        }

    # =========================================================================
    # INTANGIBLES DETAIL EXTRACTION (Tables 5.48A, 5.48B)
    # =========================================================================

    def extract_intangibles_detail(self) -> Dict:
        """
        Extract Intangible Assets amortization from Chapter 5:
          Table 5.48(A) - Asset-wise amortization (pg 206)
          Table 5.48(B) - SBU-wise amortization summary (pg 207)
        """
        print(" Extracting Intangibles Detail (Tables 5.48A, 5.48B)...")

        CH5_START = 203
        CH5_END   = 210

        def _find(title_kws, col_kws, label):
            r = self._find_table_by_keywords_and_structure(
                title_keywords=title_kws,
                column_keywords=col_kws,
                start_page=CH5_START,
                end_page=CH5_END,
                min_rows=2
            )
            print(f"      {'Found' if r else 'Not found'}: {label}" +
                  (f" on page {r['page_num'] + 1}" if r else ""))
            return r

        r548a = _find(
            ['5.48(a)', '5.48', 'amortization', 'intangible assets'],
            ['sbu g', 'sbu t', 'total'],
            'Table 5.48(A)'
        )
        r548b = _find(
            ['5.48(b)', '5.48', 'amortization', 'transmission line'],
            ['transmission', 'rs. cr'],
            'Table 5.48(B)'
        )

        def _sbu_g_value(table_data, row_keywords):
            """Get SBU-G col (index 1) from matching row."""
            for row in table_data:
                if not row:
                    continue
                row_text = ' '.join(str(c) for c in row if c).lower()
                if any(kw.lower() in row_text for kw in row_keywords):
                    if len(row) > 1:
                        c = str(row[1]).strip().replace(',', '') if row[1] else ''
                        try:
                            return float(c)
                        except ValueError:
                            pass
            return None

        if not r548a and not r548b:
            return {'status': 'not_found', 'confidence': 0}

        primary = r548a or r548b
        t548a = r548a['table_data'] if r548a else []
        t548b = r548b['table_data'] if r548b else []

        return {
            'status': 'found',
            'confidence': primary['confidence'],
            'table': {
                'page_number': primary['page_num'] + 1,
                'title': 'Tables 5.48(A)/(B): Intangibles Amortization',
                'data': primary['table_data']
            },
            'extracted_values': {
                # 5.48(A): SBU-G amortization (col 1)
                'sbu_g_amort':    _sbu_g_value(t548a, ['amortization', 'amortisation', 'software']),
                # 5.48(B): SBU-T transmission line total (not SBU-G, noted for reference)
                'transmission_amort_sbu_t': None,  # 5.48(B) is SBU-T only
            }
        }

    # =========================================================================
    # MASTER EXTRACTION METHOD
    # =========================================================================

    def extract_all(self) -> Dict:
        """
        Extract all SBU-G line items + Chapter 5 supporting tables.
        
        Returns:
            Dictionary with all extracted data
        """
        print("\n" + "="*60)
        print("EXTRACTING ALL SBU-G LINE ITEMS")
        print(f"PDF: {self.pdf_path}")
        print(f"Pages: {self.num_pages}")
        print(f"Fiscal Year: {self.metadata.get('fiscal_year', 'Unknown')}")
        print("="*60 + "\n")
        
        results = {
            'metadata': self.metadata,
            'line_items': {},
            'chapter5_tables': {}
        }
        
        # Extract SBU-G line items (from ARR table)
        results['line_items']['roe'] = self.extract_roe()
        results['line_items']['depreciation'] = self.extract_depreciation()
        results['line_items']['fuel_costs'] = self.extract_fuel_costs()
        results['line_items']['other_expenses'] = self.extract_other_expenses()
        results['line_items']['exceptional_items'] = self.extract_exceptional_items()
        results['line_items']['intangibles'] = self.extract_intangibles()
        results['line_items']['nti'] = self.extract_nti()
        results['line_items']['master_trust'] = self.extract_master_trust()
        results['line_items']['ifc'] = self.extract_ifc()
        results['line_items']['om_expenses'] = self.extract_om_expenses()
        
        # Extract Chapter 5 supporting tables
        print("\n" + "="*60)
        print("EXTRACTING CHAPTER 5 SUPPORTING TABLES")
        print("="*60 + "\n")
        
        results['chapter5_tables']['depreciation_schedule'] = self.extract_depreciation_schedule()
        results['chapter5_tables']['land_values'] = self.extract_land_values()
        results['chapter5_tables']['grants_contributions'] = self.extract_grants_contributions()
        results['chapter5_tables']['gfa_additions'] = self.extract_gfa_additions()
        results['chapter5_tables']['fuel_detail'] = self.extract_fuel_detail()
        results['chapter5_tables']['om_detail'] = self.extract_om_detail()
        results['chapter5_tables']['ifc_detail'] = self.extract_ifc_detail()
        results['chapter5_tables']['master_trust_detail'] = self.extract_master_trust_detail()
        results['chapter5_tables']['nti_detail'] = self.extract_nti_detail()
        results['chapter5_tables']['intangibles_detail'] = self.extract_intangibles_detail()
        
        # Summary
        found_line_items = sum(1 for item in results['line_items'].values() 
                              if item.get('status') == 'found')
        total_line_items = len(results['line_items'])
        
        found_ch5 = sum(1 for item in results['chapter5_tables'].values()
                       if item.get('status') == 'found')
        total_ch5 = len(results['chapter5_tables'])
        
        print("\n" + "="*60)
        print(f"EXTRACTION SUMMARY:")
        print(f"  SBU-G Line Items: {found_line_items}/{total_line_items} found")
        print(f"  Chapter 5 Tables: {found_ch5}/{total_ch5} found")
        print("="*60 + "\n")
        
        return results
    
    def close(self):
        """Close PDF file"""
        self.pdf.close()
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support"""
        self.close()


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def preview_extraction(pdf_path: str):
    """
    Quick preview of what can be extracted from PDF.
    Useful for testing.
    """
    with SBUGPDFParser(pdf_path) as parser:
        results = parser.extract_all()
        
        print("\n EXTRACTION PREVIEW:")
        print(f"   Fiscal Year: {results['metadata'].get('fiscal_year')}")
        print(f"   Document Type: {results['metadata'].get('document_type')}")
        print(f"   Total Pages: {results['metadata'].get('num_pages')}")
        
        print("\n   SBU-G Line Items:")
        for item_name, item_data in results['line_items'].items():
            status = item_data.get('status', 'unknown')
            confidence = item_data.get('confidence', 0)
            
            if status == 'found':
                print(f"    {item_name:20s} - "
                      f"Page {item_data['table']['page_number']:3d} - "
                      f"Confidence {confidence:5.1f}%")
            else:
                print(f"    {item_name:20s} - Not found")
        
        print("\n   Chapter 5 Tables:")
        for table_name, table_data in results['chapter5_tables'].items():
            status = table_data.get('status', 'unknown')
            confidence = table_data.get('confidence', 0)
            
            if status == 'found':
                print(f"    {table_name:25s} - "
                      f"Page {table_data['table']['page_number']:3d} - "
                      f"Confidence {confidence:5.1f}%")
            else:
                print(f"    {table_name:25s} - Not found")
        
        return results


if __name__ == "__main__":
    # Test with a sample PDF
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        preview_extraction(pdf_file)
    else:
        print("Usage: python pdf_parser_sbu_g.py <path_to_pdf>")
        print("\nExample:")
        print("  python pdf_parser_sbu_g.py KSEB_Truing_Up_2024-25.pdf")