"""
Data Mapper for SBU-G - Maps extracted PDF data to heuristic inputs
================================================================
This module bridges the PDF parser and the heuristics engine.

Extracts ALL 4 columns: ARR Approved, Actuals, TU Sought, Difference
Then transforms into the format expected by heuristic functions.
NOW INCLUDES: Chapter 5 data integration for complete heuristic inputs.
"""

from pdf_parser_sbu_g import SBUGPDFParser
from typing import Dict, List, Optional
import re


class SBUGDataMapper:
    """
    Maps parsed PDF data to heuristic function inputs.
    
    Extracts complete financial data (approved, actuals, claimed, variance)
    for regulatory analysis, then formats for heuristic consumption.
    """
    
    def __init__(self, parsed_data: Dict):
        """
        Initialize mapper with parsed PDF data.
        
        Args:
            parsed_data: Output from SBUGPDFParser.extract_all()
        """
        self.parsed_data = parsed_data
        self.metadata = parsed_data.get('metadata', {})
        self.line_items = parsed_data.get('line_items', {})
        self.chapter5_tables = parsed_data.get('chapter5_tables', {})  # NEW
    
    def map_all(self) -> Dict:
        """
        Map all line items to heuristic inputs.
        
        Returns:
            Dictionary with complete financial data for each line item
        """
        results = {
            'metadata': self.metadata,
            'heuristic_inputs': {}
        }
        
        # Map each line item
        results['heuristic_inputs']['roe'] = self._map_roe()
        results['heuristic_inputs']['depreciation'] = self._map_depreciation()
        results['heuristic_inputs']['fuel_costs'] = self._map_fuel()
        results['heuristic_inputs']['om_expenses'] = self._map_om()
        results['heuristic_inputs']['nti'] = self._map_nti()
        results['heuristic_inputs']['ifc'] = self._map_ifc()
        results['heuristic_inputs']['master_trust'] = self._map_master_trust()
        results['heuristic_inputs']['intangibles'] = self._map_intangibles()
        results['heuristic_inputs']['exceptional_items'] = self._map_exceptional()
        results['heuristic_inputs']['other_expenses'] = self._map_other()
        
        return results
    
    # =========================================================================
    # INTELLIGENT TABLE EXTRACTION
    # =========================================================================
    
    def _find_column_index(self, table_data: List[List[str]], 
                           column_keywords: List[str]) -> Optional[int]:
        """
        Find column index by searching header rows for keywords.
        Handles multi-line headers and newlines within cells.
        """
        if not table_data or len(table_data) < 1:
            return None
        
        # Check first 10 rows for header
        max_cols = max(len(row) for row in table_data[:10] if row)
        
        for col_idx in range(max_cols):
            # Combine text from multiple header rows for this column
            column_text = []
            
            for row_idx in range(min(10, len(table_data))):
                if col_idx < len(table_data[row_idx]):
                    cell = str(table_data[row_idx][col_idx]).strip()
                    if cell:
                        # Replace newlines with spaces
                        cell = cell.replace('\n', ' ').replace('\r', ' ')
                        column_text.append(cell.lower())
            
            # Join all text for this column
            combined = ' '.join(column_text)
            
            # Check if any keyword matches
            for keyword in column_keywords:
                if keyword.lower() in combined:
                    return col_idx
        
        return None
    
    def _find_header_end(self, table_data: List[List[str]]) -> int:
        """
        Find where header rows end and data rows begin.
        
        Returns:
            Row index where data starts
        """
        if not table_data or len(table_data) < 2:
            return 0
        
        for row_idx, row in enumerate(table_data):
            # Check if first column looks like a row number
            if len(row) > 0:
                first_col = str(row[0]).strip()
                if first_col.isdigit() and int(first_col) > 0:
                    return row_idx
            
            # Check if this is the header row with "Particulars"
            if len(row) > 2:
                for cell in row:
                    cell_lower = str(cell).lower()
                    if 'particulars' in cell_lower or 'description' in cell_lower:
                        return row_idx + 1
        
        # Default: data starts after row 5
        return 5
    
    def _clean_numeric_value(self, value_str) -> Optional[float]:
        """
        Clean and convert string to float.
        
        Handles: commas, spaces, parentheses (negative), currency symbols
        """
        if value_str is None or value_str == '':
            return None
        
        try:
            # Convert to string
            cleaned = str(value_str).strip()
            
            # Remove commas and spaces
            cleaned = re.sub(r'[,\s]', '', cleaned)
            
            # Handle parentheses as negative
            if '(' in cleaned and ')' in cleaned:
                cleaned = '-' + cleaned.replace('(', '').replace(')', '')
            
            # Remove currency symbols and other non-numeric chars (except . and -)
            cleaned = re.sub(r'[^\d.\-]', '', cleaned)
            
            # Check if empty after cleaning
            if not cleaned or cleaned in ['-', '.', '-.']:
                return None
            
            return float(cleaned)
        
        except (ValueError, AttributeError):
            return None
    
    def _extract_all_columns_from_row(self, table_data: List[List[str]], 
                                       row_keywords: List[str],
                                       exact_match: bool = False) -> Optional[Dict]:
        """
        Extract ALL 4 financial columns from a row.
        
        Returns dict with: arr_approved, actuals, tu_sought, difference_per_pdf
        
        Args:
            table_data: Table data
            row_keywords: Keywords to identify the row
            exact_match: If True, require exact keyword match (for totals)
        
        Returns:
            Dict with all 4 values or None
        """
        if not table_data or len(table_data) < 2:
            return None
        
        # Find column indices dynamically
        arr_col = self._find_column_index(table_data, ['arr approval', 'approval', 'approved'])
        actuals_col = self._find_column_index(table_data, ['actual', 'actuals'])
        tu_col = self._find_column_index(table_data, ['tu sought', 'truing up sought'])
        diff_col = 6  # FIXED: Difference values are always in column 6 (due to merged cells)
        
        # Find where data starts
        data_start = self._find_header_end(table_data)
        
        # Search for matching row
        for row_idx, row in enumerate(table_data[data_start:], start=data_start):
            if len(row) <= 2:
                continue
            
            # Search for keywords in the row
            row_match = False
            
            # Check each cell in the row
            for cell in row:
                cell_lower = str(cell).lower().strip()
                
                if exact_match:
                    # Require ALL keywords to be present
                    if all(keyword.lower() in cell_lower for keyword in row_keywords):
                        row_match = True
                        break
                else:
                    # Any keyword matches
                    if any(keyword.lower() in cell_lower for keyword in row_keywords):
                        row_match = True
                        break
            
            if not row_match:
                continue
            
            # Extract all 4 values from this row
            result = {
                'arr_approved': None,
                'actuals': None,
                'tu_sought': None,
                'difference_per_pdf': None,
                '_row_index': row_idx,
                '_row_text': ' '.join(str(c) for c in row if c)
            }
            
            if arr_col is not None and arr_col < len(row):
                result['arr_approved'] = self._clean_numeric_value(row[arr_col])
            
            if actuals_col is not None and actuals_col < len(row):
                result['actuals'] = self._clean_numeric_value(row[actuals_col])
            
            if tu_col is not None and tu_col < len(row):
                result['tu_sought'] = self._clean_numeric_value(row[tu_col])
            
            if diff_col < len(row):
                result['difference_per_pdf'] = self._clean_numeric_value(row[diff_col])
            
            # Validation: Check if we extracted at least 2 values
            non_none_count = sum(1 for v in [result['arr_approved'], 
                                             result['actuals'], 
                                             result['tu_sought']] if v is not None)
            
            if non_none_count >= 2:
                return result
        
        return None
    
    # =========================================================================
    # LINE ITEM MAPPERS
    # =========================================================================
    
    def _map_roe(self) -> Dict:
        """Map ROE data - extract all 4 columns and format for heuristic"""
        roe_data = self.line_items.get('roe', {})
        
        if roe_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'ROE data not found in PDF'}
        
        table_data = roe_data.get('table', {}).get('data', [])
        context = roe_data.get('context', {})
        
        # Extract all 4 columns for ROE
        values = self._extract_all_columns_from_row(
            table_data, 
            ['roe', 'return on equity']
        )
        
        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract ROE values from table'}
        
        # Equity capital - TODO: Extract from balance sheet
        equity_capital = 831.27
        
        return {
            'status': 'success',
            
            # Parameters expected by heuristic_ROE_01
            'equity_capital': equity_capital,
            'roe_rate': 0.14,  # Regulatory norm
            'claimed_roe': values.get('tu_sought'),  # What KSEB claims
            
            # Optional parameters (with defaults)
            'equity_infusion_during_year': 0.0,
            'equity_infusion_details': None,
            
            # Raw data for analysis/validation
            '_raw_data': {
                'arr_approved': values['arr_approved'],
                'actuals': values['actuals'],
                'tu_sought': values['tu_sought'],
                'difference_per_pdf': values['difference_per_pdf'],
            },
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text': values['_row_text']
            }
        }
    
    def _map_depreciation(self) -> Dict:
        """
        Map Depreciation data - extract from ARR table + Chapter 5 tables.
        
        Combines:
        - Claimed depreciation from ARR table (Table G8)
        - Asset details from Chapter 5 tables (5.27, 5.28, 5.29, 5.7/5.8)
        """
        # Get claimed depreciation from ARR table
        dep_data = self.line_items.get('depreciation', {})
        
        if dep_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'Depreciation data not found in PDF'}
        
        table_data = dep_data.get('table', {}).get('data', [])
        context = dep_data.get('context', {})
        
        values = self._extract_all_columns_from_row(
            table_data,
            ['depreciation']
        )
        
        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract Depreciation values'}
        
        claimed_depreciation = values.get('tu_sought')
        
        # Get asset details from Chapter 5 tables
        dep_schedule = self.chapter5_tables.get('depreciation_schedule', {})
        land_values = self.chapter5_tables.get('land_values', {})
        grants = self.chapter5_tables.get('grants_contributions', {})
        gfa_additions = self.chapter5_tables.get('gfa_additions', {})
        
        # Extract values from Chapter 5 tables
        dep_extracted = dep_schedule.get('extracted_values', {})
        land_extracted = land_values.get('extracted_values', {})
        grants_extracted = grants.get('extracted_values', {})
        additions_extracted = gfa_additions.get('extracted_values', {})
        
        # Validation: Check if we have required data
        missing_data = []
        if dep_schedule.get('status') != 'found':
            missing_data.append('Depreciation Schedule (Table 5.27)')
        if land_values.get('status') != 'found':
            missing_data.append('Land Values (Table 5.28)')
        if grants.get('status') != 'found':
            missing_data.append('Grants (Table 5.29)')
        
        if missing_data:
            return {
                'status': 'partial',
                'error': f"Missing Chapter 5 data: {', '.join(missing_data)}",
                'claimed_depreciation': claimed_depreciation,
                '_raw_data': {
                    'arr_approved': values['arr_approved'],
                    'actuals': values['actuals'],
                    'tu_sought': values['tu_sought'],
                    'difference_per_pdf': values['difference_per_pdf'],
                }
            }
        
        return {
            'status': 'success',
            
            # Parameters expected by heuristic_DEP_GEN_01
            'gfa_opening_total': dep_extracted.get('gfa_opening_total'),
            'gfa_13_to_30_years': dep_extracted.get('gfa_13_to_30_years'),
            'land_13_to_30_years': land_extracted.get('land_13_to_30_years'),
            'grants_13_to_30_years': grants_extracted.get('grants_13_to_30_years', 0.0),
            'gfa_below_13_years': dep_extracted.get('gfa_below_13_years'),
            'land_below_13_years': land_extracted.get('land_below_13_years'),
            'grants_below_13_years': grants_extracted.get('grants_below_13_years', 0.0),
            'asset_additions': additions_extracted.get('asset_additions') or dep_extracted.get('asset_additions'),
            'claimed_depreciation': claimed_depreciation,
            'asset_withdrawals': dep_extracted.get('asset_withdrawals', 0.0),
            
            # Raw data for analysis/validation
            '_raw_data': {
                'arr_approved': values['arr_approved'],
                'actuals': values['actuals'],
                'tu_sought': values['tu_sought'],
                'difference_per_pdf': values['difference_per_pdf'],
            },
            '_chapter5_data': {
                'depreciation_schedule': dep_extracted,
                'land_values': land_extracted,
                'grants': grants_extracted,
                'gfa_additions': additions_extracted
            },
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text': values['_row_text']
            }
        }
    
    def _map_fuel(self) -> Dict:
        """Map Fuel/Cost of Generation - ARR total + Table G9 station breakdown"""
        fuel_data = self.line_items.get('fuel_costs', {})

        if fuel_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'Fuel data not found in PDF'}

        # Get total claimed from ARR table
        roe_data = self.line_items.get('roe', {})
        table_data = roe_data.get('table', {}).get('data', [])

        values = self._extract_all_columns_from_row(
            table_data,
            ['cost of generation of power', 'generation of power', 'cost of generation'],
            exact_match=False
        )

        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract Fuel values'}

        # Get Table G9 breakdown
        fuel_detail = self.chapter5_tables.get('fuel_detail', {})
        fuel_extracted = fuel_detail.get('extracted_values', {})

        missing_data = []
        if fuel_detail.get('status') != 'found':
            missing_data.append('Table G9: Station wise Cost of Generation')

        if missing_data:
            return {
                'status': 'partial',
                'error': f"Missing detail data: {', '.join(missing_data)}",
                'total_claimed_fuel_cost': values.get('tu_sought'),
                '_raw_data': {
                    'arr_approved':        values['arr_approved'],
                    'actuals':             values['actuals'],
                    'tu_sought':           values['tu_sought'],
                    'difference_per_pdf':  values['difference_per_pdf'],
                }
            }

        # Rename station breakdown keys to match heuristic_FUEL_01 expectations
        raw_stations = fuel_extracted.get('station_breakdown', [])
        station_breakdown = [
            {
                'name':           s.get('station', ''),
                'heavy_fuel_oil': s.get('hfo', 0.0),
                'hsd_oil':        s.get('hsd', 0.0),
                # Merge lube oil + hydel + IC (G9 has no separate column)
                'lube_oil':       round(s.get('lube_oil', 0.0) +
                                        s.get('hydel', 0.0) +
                                        s.get('ic', 0.0), 4),
                'lubricants':     0.0,
                'total':          s.get('total', 0.0),
            }
            for s in raw_stations
        ]

        # Merge hydel + ic into lube_oil for column totals too
        lube_merged = round(
            fuel_extracted.get('lube_oil', 0.0) +
            fuel_extracted.get('hydel_power_gen', 0.0) +
            fuel_extracted.get('ic_power_gen', 0.0), 4
        )

        return {
            'status': 'success',

            # ARR-level totals
            'total_claimed_fuel_cost': values.get('tu_sought'),

            # Station-wise breakdown (keys match heuristic_FUEL_01)
            'station_breakdown':      station_breakdown,

            # Column totals (keys match heuristic_FUEL_01)
            'heavy_fuel_oil':         fuel_extracted.get('heavy_fuel_oil', 0.0),
            'hsd_oil':                fuel_extracted.get('hsd_oil', 0.0),
            'lube_oil':               lube_merged,
            'lubricants_consumables': 0.0,

            # Raw data
            '_raw_data': {
                'arr_approved':        values['arr_approved'],
                'actuals':             values['actuals'],
                'tu_sought':           values['tu_sought'],
                'difference_per_pdf':  values['difference_per_pdf'],
            },
            '_g9_data': fuel_extracted,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text':  values['_row_text']
            }
        }
    
    def _map_om(self) -> Dict:
        """Map O&M Expenses - ARR total + Tables 5.37/5.38/5.39/5.40 breakdown"""
        om_data = self.line_items.get('om_expenses', {})

        if om_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'O&M data not found in PDF'}

        table_data = om_data.get('table', {}).get('data', [])
        context    = om_data.get('context', {})

        values = self._extract_all_columns_from_row(
            table_data,
            ['o&m expenses - total', 'o&m expenses-total'],
            exact_match=False
        )
        if values is None:
            values = self._extract_all_columns_from_row(
                table_data,
                ['o&m expenses'],
                exact_match=False
            )

        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract O&M values'}

        # Get Tables 5.37-5.40 breakdown
        om_detail = self.chapter5_tables.get('om_detail', {})
        om_extracted = om_detail.get('extracted_values', {})

        missing_data = []
        if om_detail.get('status') != 'found':
            missing_data.append('Tables 5.37-5.40: O&M Expenses Detail')

        if missing_data:
            return {
                'status': 'partial',
                'error': f"Missing detail data: {', '.join(missing_data)}",
                'claimed_om': values.get('tu_sought'),
                '_raw_data': {
                    'arr_approved':        values['arr_approved'],
                    'actuals':             values['actuals'],
                    'tu_sought':           values['tu_sought'],
                    'difference_per_pdf':  values['difference_per_pdf'],
                }
            }

        return {
            'status': 'success',

            # ARR-level total
            'claimed_om': values.get('tu_sought'),

            # Component breakdown from Tables 5.37-5.40
            'employee_cost':  om_extracted.get('employee_cost'),
            'rm_expenses':    om_extracted.get('rm_expenses'),
            'ag_expenses':    om_extracted.get('ag_expenses'),
            'om_total_ch5':   om_extracted.get('om_total'),

            # Sub-breakdowns (may be None if sub-tables not found)
            'basic_pay':      om_extracted.get('basic_pay'),
            'da':             om_extracted.get('da'),
            'hra':            om_extracted.get('hra'),
            'civil_rm':       om_extracted.get('civil_rm'),
            'plant_rm':       om_extracted.get('plant_rm'),

            # Raw data
            '_raw_data': {
                'arr_approved':        values['arr_approved'],
                'actuals':             values['actuals'],
                'tu_sought':           values['tu_sought'],
                'difference_per_pdf':  values['difference_per_pdf'],
            },
            '_om_detail': om_extracted,
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text':  values['_row_text']
            }
        }
    
    def _map_nti(self) -> Dict:
        """Map Non-Tariff Income - ARR total + Tables 5.49/5.51 breakdown"""
        nti_data = self.line_items.get('nti', {})

        if nti_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'NTI data not found in PDF'}

        table_data = nti_data.get('table', {}).get('data', [])
        context    = nti_data.get('context', {})

        values = self._extract_all_columns_from_row(
            table_data,
            ['less non-tariff', 'less non tariff', 'non-tariff income', 'non tariff income']
        )

        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract NTI values'}

        nti_detail    = self.chapter5_tables.get('nti_detail', {})
        nti_extracted = nti_detail.get('extracted_values', {})

        if nti_detail.get('status') != 'found':
            return {
                'status': 'partial',
                'error': 'Missing Tables 5.49/5.51 detail',
                'claimed_nti': values.get('tu_sought'),
                '_raw_data': {
                    'arr_approved':       values['arr_approved'],
                    'actuals':            values['actuals'],
                    'tu_sought':          values['tu_sought'],
                    'difference_per_pdf': values['difference_per_pdf'],
                }
            }

        return {
            'status': 'success',
            'claimed_nti':      values.get('tu_sought'),
            'meter_rent':       nti_extracted.get('meter_rent'),
            'rental_income':    nti_extracted.get('rental_income'),
            'interest_income':  nti_extracted.get('interest_income'),
            'misc_income':      nti_extracted.get('misc_income'),
            'surcharge_income': nti_extracted.get('surcharge_income'),
            'nti_total_ch5':    nti_extracted.get('nti_total'),
            'nti_approved_551': nti_extracted.get('nti_approved_551'),
            'nti_claimed_551':  nti_extracted.get('nti_claimed_551'),
            '_raw_data': {
                'arr_approved':       values['arr_approved'],
                'actuals':            values['actuals'],
                'tu_sought':          values['tu_sought'],
                'difference_per_pdf': values['difference_per_pdf'],
            },
            '_nti_detail': nti_extracted,
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text':  values['_row_text']
            }
        }
    
    def _map_ifc(self) -> Dict:
        """Map Interest & Finance Charges - ARR total + Tables 5.1/5.3/5.22 breakdown"""
        ifc_data = self.line_items.get('ifc', {})

        if ifc_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'IFC data not found in PDF'}

        table_data = ifc_data.get('table', {}).get('data', [])
        context    = ifc_data.get('context', {})

        values = self._extract_all_columns_from_row(
            table_data,
            ['interest', 'finance charge', 'interest & finance']
        )

        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract IFC values'}

        # Get Tables 5.1/5.3/5.22 breakdown
        ifc_detail    = self.chapter5_tables.get('ifc_detail', {})
        ifc_extracted = ifc_detail.get('extracted_values', {})

        missing_data = []
        if ifc_detail.get('status') != 'found':
            missing_data.append('Table 5.1: IFC Summary')

        if missing_data:
            return {
                'status': 'partial',
                'error': f"Missing detail data: {', '.join(missing_data)}",
                'claimed_ifc': values.get('tu_sought'),
                '_raw_data': {
                    'arr_approved':        values['arr_approved'],
                    'actuals':             values['actuals'],
                    'tu_sought':           values['tu_sought'],
                    'difference_per_pdf':  values['difference_per_pdf'],
                }
            }

        return {
            'status': 'success',

            # ARR-level total
            'claimed_ifc': values.get('tu_sought'),

            # Component breakdown from Table 5.1
            'normative_interest':  ifc_extracted.get('normative_interest'),
            'gpf_interest':        ifc_extracted.get('gpf_interest'),
            'master_trust_int':    ifc_extracted.get('master_trust_int'),
            'power_purchase_int':  ifc_extracted.get('power_purchase_int'),
            'carrying_cost':       ifc_extracted.get('carrying_cost'),
            'other_charges':       ifc_extracted.get('other_charges'),
            'ifc_total_ch5':       ifc_extracted.get('ifc_total'),

            # Loan metrics from Table 5.3
            'avg_interest_rate':   ifc_extracted.get('avg_interest_rate'),

            # SBU-G specific from Table 5.22
            'sbu_g_ifc_verified':  ifc_extracted.get('sbu_g_ifc_from_5_22'),

            # Raw data
            '_raw_data': {
                'arr_approved':        values['arr_approved'],
                'actuals':             values['actuals'],
                'tu_sought':           values['tu_sought'],
                'difference_per_pdf':  values['difference_per_pdf'],
            },
            '_ifc_detail': ifc_extracted,
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text':  values['_row_text']
            }
        }

    def _map_master_trust(self) -> Dict:
        """Map Master Trust - ARR total + Tables 5.17/5.25/5.26 breakdown"""
        mt_data = self.line_items.get('master_trust', {})

        if mt_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'Master Trust data not found in PDF'}

        table_data = mt_data.get('table', {}).get('data', [])
        context    = mt_data.get('context', {})

        values = self._extract_all_columns_from_row(
            table_data,
            ['master trust', 'contribution to master trust', 'additional contribution']
        )

        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract Master Trust values'}

        mt_detail    = self.chapter5_tables.get('master_trust_detail', {})
        mt_extracted = mt_detail.get('extracted_values', {})

        if mt_detail.get('status') != 'found':
            return {
                'status': 'partial',
                'error': 'Missing Tables 5.17/5.25/5.26 detail',
                'claimed_master_trust': values.get('tu_sought'),
                '_raw_data': {
                    'arr_approved':       values['arr_approved'],
                    'actuals':            values['actuals'],
                    'tu_sought':          values['tu_sought'],
                    'difference_per_pdf': values['difference_per_pdf'],
                }
            }

        return {
            'status': 'success',
            'claimed_master_trust': values.get('tu_sought'),
            'bond_interest':        mt_extracted.get('bond_interest'),
            'additional_contrib':   mt_extracted.get('additional_contrib'),
            'bond_repayment':       mt_extracted.get('bond_repayment'),
            'mt_total_computed':    mt_extracted.get('mt_total_computed'),
            '_raw_data': {
                'arr_approved':       values['arr_approved'],
                'actuals':            values['actuals'],
                'tu_sought':          values['tu_sought'],
                'difference_per_pdf': values['difference_per_pdf'],
            },
            '_mt_detail': mt_extracted,
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text':  values['_row_text']
            }
        }
    
    def _map_intangibles(self) -> Dict:
        """Map Intangible Assets - ARR total + Tables 5.48(A)/(B) breakdown"""
        int_data = self.line_items.get('intangibles', {})

        if int_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'Intangibles data not found in PDF'}

        table_data = int_data.get('table', {}).get('data', [])
        context    = int_data.get('context', {})

        values = self._extract_all_columns_from_row(
            table_data,
            ['intangible', 'amortisation', 'amortization']
        )

        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract Intangibles values'}

        int_detail    = self.chapter5_tables.get('intangibles_detail', {})
        int_extracted = int_detail.get('extracted_values', {})

        if int_detail.get('status') != 'found':
            return {
                'status': 'partial',
                'error': 'Missing Tables 5.48(A)/(B) detail',
                'total_claimed_amortization': values.get('tu_sought'),
                '_raw_data': {
                    'arr_approved':       values['arr_approved'],
                    'actuals':            values['actuals'],
                    'tu_sought':          values['tu_sought'],
                    'difference_per_pdf': values['difference_per_pdf'],
                }
            }

        return {
            'status': 'success',
            'total_claimed_amortization': values.get('tu_sought'),
            'opening_gross':              int_extracted.get('opening_gross'),
            'additions':                  int_extracted.get('additions'),
            'closing_gross':              int_extracted.get('closing_gross'),
            'opening_amort':              int_extracted.get('opening_amort'),
            'amort_for_year':             int_extracted.get('amort_for_year'),
            'closing_amort':              int_extracted.get('closing_amort'),
            'net_block':                  int_extracted.get('net_block'),
            'sbu_g_amort_total':          int_extracted.get('sbu_g_amort_total'),
            '_raw_data': {
                'arr_approved':       values['arr_approved'],
                'actuals':            values['actuals'],
                'tu_sought':          values['tu_sought'],
                'difference_per_pdf': values['difference_per_pdf'],
            },
            '_int_detail': int_extracted,
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text':  values['_row_text']
            }
        }
    
    def _map_exceptional(self) -> Dict:
        """Map Exceptional Items - extract all 4 columns"""
        exc_data = self.line_items.get('exceptional_items', {})
        
        if exc_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'Exceptional Items data not found in PDF'}
        
        table_data = exc_data.get('table', {}).get('data', [])
        context = exc_data.get('context', {})
        
        values = self._extract_all_columns_from_row(
            table_data,
            ['exceptional', 'exceptional items']
        )
        
        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract Exceptional Items values'}
        
        return {
            'status': 'success',
            
            # Parameters for Exceptional heuristic (placeholder - needs expansion)
            'claimed_exceptional': values.get('tu_sought'),
            # TODO: Add parameters for Exceptional heuristic from Chapter 5
            
            # Raw data
            '_raw_data': {
                'arr_approved': values['arr_approved'],
                'actuals': values['actuals'],
                'tu_sought': values['tu_sought'],
                'difference_per_pdf': values['difference_per_pdf'],
            },
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text': values['_row_text']
            }
        }
    
    def _map_other(self) -> Dict:
        """Map Other Expenses - extract all 4 columns"""
        other_data = self.line_items.get('other_expenses', {})
        
        if other_data.get('status') != 'found':
            return {'status': 'not_found', 'error': 'Other Expenses data not found in PDF'}
        
        table_data = other_data.get('table', {}).get('data', [])
        context = other_data.get('context', {})
        
        values = self._extract_all_columns_from_row(
            table_data,
            ['other expenses', 'discount to consumers', 'other exp', 'miscellaneous write']
        )
        
        if values is None:
            return {'status': 'extraction_failed', 'error': 'Could not extract Other Expenses values'}
        
        return {
            'status': 'success',
            
            # Parameters for Other Expenses heuristic (placeholder - needs expansion)
            'claimed_other': values.get('tu_sought'),
            # TODO: Add parameters for Other Expenses heuristic from Chapter 5
            
            # Raw data
            '_raw_data': {
                'arr_approved': values['arr_approved'],
                'actuals': values['actuals'],
                'tu_sought': values['tu_sought'],
                'difference_per_pdf': values['difference_per_pdf'],
            },
            '_context': context,
            '_debug': {
                'row_index': values['_row_index'],
                'row_text': values['_row_text']
            }
        }


# =============================================================================
# COMMAND LINE TESTING
# =============================================================================

def main():
    """Test the mapper with a PDF file"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_mapper_sbu_g.py <path_to_pdf>")
        return
    
    pdf_path = sys.argv[1]
    
    # Parse PDF
    print("Parsing PDF...")
    with SBUGPDFParser(pdf_path) as parser:
        parsed_data = parser.extract_all()
    
    # Map data
    print("\nMapping data to heuristic inputs...")
    mapper = SBUGDataMapper(parsed_data)
    mapped_data = mapper.map_all()
    
    # Display results
    print("\n" + "="*70)
    print("MAPPED DATA PREVIEW - ALL 4 COLUMNS")
    print("="*70)
    
    for item_name, inputs in mapped_data['heuristic_inputs'].items():
        status = inputs.get('status', 'unknown')
        
        if status not in ['success', 'partial']:
            print(f"\n{item_name.upper()}: {status}")
            if 'error' in inputs:
                print(f"  Error: {inputs['error']}")
            continue
        
        # Show raw data
        raw_data = inputs.get('_raw_data', {})
        
        print(f"\n{item_name.upper()}:")
        
        # Helper to format values
        def fmt(val):
            if val is None:
                return "N/A".rjust(10)
            return f"{val:>10.2f}"
        
        print(f"  ARR Approved:  {fmt(raw_data.get('arr_approved'))}")
        print(f"  Actuals:       {fmt(raw_data.get('actuals'))}")
        print(f"  TU Sought:     {fmt(raw_data.get('tu_sought'))}")
        print(f"  Difference:    {fmt(raw_data.get('difference_per_pdf'))}")
        
        # Show validation
        arr_app = raw_data.get('arr_approved')
        tu_sou = raw_data.get('tu_sought')
        pdf_diff = raw_data.get('difference_per_pdf')
        
        if arr_app is not None and tu_sou is not None:
            calc_diff = tu_sou - arr_app
            
            if pdf_diff is not None and abs(calc_diff - pdf_diff) > 0.1:
                print(f"  ⚠️  VALIDATION: Calculated diff ({calc_diff:.2f}) ≠ PDF diff ({pdf_diff:.2f})")
            else:
                print(f"  ✅ VALIDATION: OK")
        
        # Show heuristic parameters for depreciation
        if item_name == 'depreciation' and status == 'success':
            print(f"\n  HEURISTIC PARAMETERS:")
            print(f"    GFA Opening:       {fmt(inputs.get('gfa_opening_total'))}")
            print(f"    GFA 13-30 years:   {fmt(inputs.get('gfa_13_to_30_years'))}")
            print(f"    Land 13-30 years:  {fmt(inputs.get('land_13_to_30_years'))}")
            print(f"    Grants 13-30:      {fmt(inputs.get('grants_13_to_30_years'))}")
            print(f"    Asset Additions:   {fmt(inputs.get('asset_additions'))}")


if __name__ == "__main__":
    main()