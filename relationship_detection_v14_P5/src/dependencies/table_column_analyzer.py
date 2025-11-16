#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Table Column Analyzer

Extracts variable information from table column headers, detecting
symbols, units, names, and column types (categorical vs continuous).

Author: V12 Development Team
Created: 2025-11-04
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
import re
from dataclasses import dataclass
import yaml

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

from src.core.semantic_registry import SemanticRegistry


@dataclass
class TableColumnInfo:
    """Information extracted from table column"""
    column_index: int
    header_text: str
    name: Optional[str] = None
    symbol: Optional[str] = None
    units: Optional[str] = None
    is_index_column: bool = False
    data_type: Optional[str] = None  # "categorical", "continuous", "discrete"
    canonical_id: Optional[str] = None
    sample_values: List[Any] = None

    def __post_init__(self):
        if self.sample_values is None:
            self.sample_values = []


class TableColumnAnalyzer:
    """
    Extract variable information from table column headers.

    Responsibilities:
    - Parse column headers for symbols, names, units
    - Handle multiple header formats (parenthetical, comma-separated, etc.)
    - Detect index columns (categorical lookup keys)
    - Resolve symbols to canonical IDs via SemanticRegistry
    - Extract units with Unicode support
    """

    def __init__(
        self,
        semantic_registry: SemanticRegistry,
        config: Dict
    ):
        """
        Initialize table column analyzer.

        Args:
            semantic_registry: SemanticRegistry instance for symbol resolution
            config: Configuration dict from data_dependency_config.yaml
        """
        self.semantic_registry = semantic_registry
        self.config = config
        self.header_patterns = self._build_header_patterns()
        self.unit_patterns = self._build_unit_patterns()

    def _build_header_patterns(self) -> List[Dict]:
        """Build compiled regex patterns from config"""
        patterns = []
        for pattern_config in self.config['variable_extraction']['table']['header_patterns']:
            patterns.append({
                'regex': re.compile(pattern_config['pattern']),
                'name_group': pattern_config.get('name_group'),
                'symbol_group': pattern_config.get('symbol_group'),
                'units_group': pattern_config.get('units_group')
            })
        return patterns

    def _build_unit_patterns(self) -> List[re.Pattern]:
        """Build compiled regex patterns for unit detection"""
        unit_strings = self.config['variable_extraction']['table']['unit_patterns']
        return [re.compile(pattern) for pattern in unit_strings]

    def analyze_table_columns(
        self,
        table_metadata: Dict[str, Any]
    ) -> List[TableColumnInfo]:
        """
        Extract variable info from table column headers.

        Args:
            table_metadata: Dict with keys:
                - headers: List[str] (column headers)
                - data: List[List[Any]] (table data rows)
                - table_id: str (e.g., "tbl:3")

        Returns:
            List of TableColumnInfo objects
        """
        headers = table_metadata.get('headers', [])
        data = table_metadata.get('data', [])

        column_infos = []

        for idx, header in enumerate(headers):
            # Extract column values for this index
            column_values = self._extract_column_values(data, idx)

            # Parse the header
            info = self._parse_column_header(header, idx)

            # Detect if index column
            info.is_index_column = self._detect_index_column(header, column_values)

            # Determine data type
            info.data_type = self._determine_data_type(column_values)

            # Store sample values
            info.sample_values = column_values[:5] if len(column_values) > 5 else column_values

            # Try to resolve to canonical ID
            if info.symbol and self.semantic_registry:
                context = {
                    'table_id': table_metadata.get('table_id'),
                    'column_name': info.name,
                    'units': info.units
                }
                info.canonical_id = self.semantic_registry.resolve_symbol(
                    info.symbol,
                    context
                )

            column_infos.append(info)

        return column_infos

    def _extract_column_values(self, data: List[List[Any]], col_idx: int) -> List[Any]:
        """Extract all values for a specific column index"""
        values = []
        for row in data:
            if col_idx < len(row):
                values.append(row[col_idx])
        return values

    def _parse_column_header(self, header: str, column_index: int) -> TableColumnInfo:
        """
        Parse single column header to extract name, symbol, units.

        Handles formats:
        - "Emissivity (ε)" → name: Emissivity, symbol: ε
        - "k (W/m K)" → symbol: k, units: W/m K
        - "Temperature, K" → name: Temperature, units: K
        - "Thermal Conductivity (k), W/m·K" → all three

        Args:
            header: Column header string
            column_index: Column position (0-indexed)

        Returns:
            TableColumnInfo with extracted components
        """
        info = TableColumnInfo(
            column_index=column_index,
            header_text=header
        )

        # Check for complex format first: "Name (symbol), units"
        complex_pattern = r'([A-Z][a-zA-Z\s]+)\s*\(([^)]+)\)\s*,\s*(.+)$'
        complex_match = re.search(complex_pattern, header)
        if complex_match:
            info.name = complex_match.group(1).strip()
            info.symbol = self._clean_symbol(complex_match.group(2).strip())
            info.units = complex_match.group(3).strip()
            if info.units:
                info.units = self._normalize_units(info.units)
            return info

        # Try each pattern from config
        for pattern_info in self.header_patterns:
            match = pattern_info['regex'].search(header)
            if match:
                # Extract name if group specified
                if pattern_info['name_group'] is not None:
                    info.name = match.group(pattern_info['name_group']).strip()

                # Extract symbol if group specified
                if pattern_info['symbol_group'] is not None:
                    symbol_text = match.group(pattern_info['symbol_group']).strip()
                    # Clean symbol (remove extra whitespace)
                    info.symbol = self._clean_symbol(symbol_text)

                # Extract units if group specified
                if pattern_info['units_group'] is not None:
                    info.units = match.group(pattern_info['units_group']).strip()

                break

        # If no pattern matched, try fallback extraction
        if not info.name and not info.symbol:
            info = self._fallback_header_parse(header, column_index)

        # Try to extract units if not found yet
        if not info.units:
            units = self._extract_units(header)
            if units:
                info.units = units

        # Normalize units
        if info.units:
            info.units = self._normalize_units(info.units)

        return info

    def _clean_symbol(self, symbol_text: str) -> str:
        r"""
        Clean extracted symbol text.

        Removes:
        - Extra whitespace
        - Surrounding parentheses
        - LaTeX commands (\epsilon → ε via registry)
        """
        # Remove extra whitespace
        symbol = symbol_text.strip()

        # Remove surrounding parentheses if present
        if symbol.startswith('(') and symbol.endswith(')'):
            symbol = symbol[1:-1]

        return symbol

    def _extract_units(self, header: str) -> Optional[str]:
        """
        Extract units from header using unit patterns.

        Args:
            header: Column header text

        Returns:
            Units string or None if not found
        """
        for pattern in self.unit_patterns:
            match = pattern.search(header)
            if match:
                return match.group(0)
        return None

    def _normalize_units(self, units: str) -> str:
        """
        Normalize unit strings.

        Examples:
        - "W/m K" → "W/m·K"
        - "kg/m3" → "kg/m³"
        - "W/m2 K" → "W/m²·K"
        """
        # Normalize spacing around /
        units = re.sub(r'\s*/\s*', '/', units)

        # Replace space with · (middle dot) for compound units
        # W/m K → W/m·K
        units = re.sub(r'([a-zA-Z0-9])(\s+)([a-zA-Z])', r'\1·\3', units)

        # Replace digit after m/s to superscript if appropriate
        # kg/m3 → kg/m³
        units = units.replace('m2', 'm²')
        units = units.replace('m3', 'm³')

        return units

    def _fallback_header_parse(self, header: str, column_index: int) -> TableColumnInfo:
        """
        Fallback parsing when no pattern matches.

        Treats entire header as name, tries to detect symbol/units.

        Args:
            header: Column header string
            column_index: Column position

        Returns:
            TableColumnInfo with best-effort extraction
        """
        info = TableColumnInfo(
            column_index=column_index,
            header_text=header
        )

        # Check for parenthetical content
        paren_match = re.search(r'\(([^)]+)\)', header)
        if paren_match:
            paren_content = paren_match.group(1).strip()

            # Is it a single symbol or units?
            if len(paren_content) <= 3 and not any(c.isdigit() or c in '/' for c in paren_content):
                # Likely a symbol (short, no numbers or slashes)
                info.symbol = paren_content
                # Name is text before parentheses
                info.name = header[:paren_match.start()].strip()
            else:
                # Likely units (longer, or contains numbers/slashes)
                info.units = paren_content
                # Name is text before parentheses
                info.name = header[:paren_match.start()].strip()
        else:
            # No parentheses, entire header is name
            info.name = header.strip()

        return info

    def _detect_index_column(self, header: str, values: List[str]) -> bool:
        """
        Detect if column is categorical (lookup key).

        Index column indicators:
        - Low unique value ratio (<10%)
        - Text/string values
        - Common index names (Material, Geometry, Type, etc.)
        - No numeric units in header

        Args:
            header: Column header text
            values: List of column values

        Returns:
            True if column is an index/categorical column
        """
        # Check for common index column names
        index_keywords = {
            'material', 'geometry', 'type', 'surface', 'finish',
            'gas', 'fluid', 'substance', 'configuration', 'condition'
        }
        header_lower = header.lower()
        if any(keyword in header_lower for keyword in index_keywords):
            return True

        # Check unique value ratio
        if len(values) > 0:
            unique_ratio = len(set(values)) / len(values)
            if unique_ratio < 0.1:  # Less than 10% unique
                return True

        # Check if values are non-numeric strings
        if len(values) > 0:
            # Sample first 5 values
            sample = values[:5]
            non_numeric_count = sum(1 for v in sample if isinstance(v, str) and not self._is_numeric(str(v)))
            if non_numeric_count >= len(sample) * 0.8:  # 80% non-numeric
                return True

        return False

    def _is_numeric(self, value_str: str) -> bool:
        """Check if string represents a numeric value"""
        try:
            float(value_str.replace(',', ''))
            return True
        except (ValueError, AttributeError):
            return False

    def _determine_data_type(self, values: List[Any]) -> str:
        """
        Determine data type of column.

        Types:
        - "categorical": String values, low unique ratio
        - "continuous": Numeric values, high unique ratio
        - "discrete": Numeric values, low unique ratio

        Args:
            values: List of column values

        Returns:
            Data type string
        """
        if len(values) == 0:
            return "unknown"

        # Check if values are numeric
        numeric_count = sum(1 for v in values if self._is_numeric(str(v)))
        numeric_ratio = numeric_count / len(values)

        # Mostly non-numeric → categorical
        if numeric_ratio < 0.5:
            return "categorical"

        # Mostly numeric → check unique ratio
        unique_ratio = len(set(values)) / len(values)

        if unique_ratio > 0.5:
            return "continuous"
        else:
            return "discrete"

    def get_column_summary(
        self,
        column_infos: List[TableColumnInfo]
    ) -> Dict:
        """
        Generate summary statistics for analyzed columns.

        Returns:
            Dict with counts and statistics
        """
        summary = {
            'total_columns': len(column_infos),
            'with_symbols': 0,
            'with_units': 0,
            'with_names': 0,
            'index_columns': 0,
            'by_data_type': {
                'categorical': 0,
                'continuous': 0,
                'discrete': 0,
                'unknown': 0
            },
            'resolved_to_canonical': 0
        }

        for col in column_infos:
            if col.symbol:
                summary['with_symbols'] += 1
            if col.units:
                summary['with_units'] += 1
            if col.name:
                summary['with_names'] += 1
            if col.is_index_column:
                summary['index_columns'] += 1
            if col.canonical_id:
                summary['resolved_to_canonical'] += 1

            if col.data_type:
                summary['by_data_type'][col.data_type] += 1

        return summary
