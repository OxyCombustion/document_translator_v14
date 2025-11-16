#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lookup Method Generator

Generates appropriate lookup methods based on table structure:
- Categorical tables → select_by_X (material, geometry)
- Continuous tables → interpolate_by_X (temperature, pressure, Re)
- Multi-indexed tables → compound_lookup (material + temperature)

Author: V12 Development Team
Created: 2025-11-04
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

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

from src.detectors.data_structures import (
    LookupMethod, VariableLinkage
)
from src.detectors.table_column_analyzer import TableColumnInfo


@dataclass
class LookupMethodInfo:
    """
    Information about generated lookup method.

    Attributes:
        method: LookupMethod enum (SELECT_BY, INTERPOLATE, etc.)
        lookup_key_column: Name of index column used for lookup
        lookup_key_column_index: Column position (0-indexed)
        method_name: Generated method name (e.g., 'select_by_material_type')
        parameters: Method-specific parameters
    """
    method: LookupMethod
    lookup_key_column: str
    lookup_key_column_index: int
    method_name: str
    parameters: Dict[str, Any]


class LookupMethodGenerator:
    """
    Generate lookup methods based on table structure.

    Responsibilities:
    - Analyze table structure (categorical, continuous, multi-indexed)
    - Detect index columns automatically
    - Generate appropriate lookup method
    - Create descriptive method names
    - Determine interpolation type
    """

    def __init__(self, config: Dict):
        """
        Initialize lookup method generator.

        Args:
            config: Configuration dict from data_dependency_config.yaml
        """
        self.config = config
        self.lookup_config = config.get('lookup_methods', {})

    def generate_lookup_method(
        self,
        table_metadata: Dict[str, Any],
        table_columns: List[TableColumnInfo],
        variable_linkage: VariableLinkage
    ) -> LookupMethodInfo:
        """
        Determine lookup method based on table structure.

        Args:
            table_metadata: Table metadata with table_id, page, etc.
            table_columns: List of TableColumnInfo from table
            variable_linkage: Variable linkage (may contain preliminary lookup_method)

        Returns:
            LookupMethodInfo with complete lookup details
        """
        # Analyze table structure
        structure = self._analyze_table_structure(table_columns)

        # Detect index columns
        index_columns = self._detect_index_columns(table_columns)

        # Determine lookup method based on structure
        if structure['is_multiindex']:
            # Multi-indexed lookup (compound)
            method = LookupMethod.COMPOUND_LOOKUP
            # Use first index column as primary key
            key_column = index_columns[0] if index_columns else table_columns[0]
            method_name = self._generate_method_name(method, key_column)
            parameters = {
                'index_columns': [col.header_text for col in index_columns],
                'index_column_indices': [col.column_index for col in index_columns]
            }

        elif structure['is_categorical']:
            # Categorical lookup (select by category)
            method = LookupMethod.SELECT_BY_CATEGORY
            key_column = index_columns[0] if index_columns else self._find_categorical_column(table_columns)
            method_name = self._generate_method_name(method, key_column)
            parameters = {
                'categories': key_column.sample_values if hasattr(key_column, 'sample_values') else []
            }

        elif structure['is_continuous']:
            # Continuous lookup (interpolation)
            # Determine interpolation type
            key_column = index_columns[0] if index_columns else self._find_continuous_column(table_columns)
            interp_type = self._determine_interpolation_method(key_column)

            if interp_type == 'spline':
                method = LookupMethod.INTERPOLATE_SPLINE
            else:
                method = LookupMethod.INTERPOLATE_LINEAR

            method_name = self._generate_method_name(method, key_column)
            parameters = {
                'interpolation_type': interp_type,
                'extrapolation': 'warn'  # Warn when extrapolating
            }

        else:
            # Default: exact match
            method = LookupMethod.EXACT_MATCH
            key_column = index_columns[0] if index_columns else table_columns[0]
            method_name = self._generate_method_name(method, key_column)
            parameters = {}

        return LookupMethodInfo(
            method=method,
            lookup_key_column=key_column.header_text,
            lookup_key_column_index=key_column.column_index,
            method_name=method_name,
            parameters=parameters
        )

    def _analyze_table_structure(
        self,
        table_columns: List[TableColumnInfo]
    ) -> Dict[str, Any]:
        """
        Analyze table to determine structure type.

        Args:
            table_columns: List of table columns

        Returns:
            Dict with structure analysis:
            - index_columns: List of index columns
            - data_columns: List of data columns
            - is_categorical: True if categorical lookup table
            - is_continuous: True if continuous lookup table
            - is_multiindex: True if has multiple index columns
        """
        index_columns = [col for col in table_columns if col.is_index_column]
        data_columns = [col for col in table_columns if not col.is_index_column]

        # Determine structure type
        is_multiindex = len(index_columns) >= 2

        # Categorical if index column has categorical data type
        is_categorical = any(
            col.data_type == 'categorical' for col in index_columns
        ) if index_columns else False

        # Continuous if index column has continuous data type
        is_continuous = any(
            col.data_type == 'continuous' for col in index_columns
        ) if index_columns else False

        # If no explicit index columns, infer from first column
        if not index_columns and table_columns:
            first_col = table_columns[0]
            is_categorical = first_col.data_type == 'categorical'
            is_continuous = first_col.data_type == 'continuous'

        return {
            'index_columns': index_columns,
            'data_columns': data_columns,
            'is_categorical': is_categorical,
            'is_continuous': is_continuous,
            'is_multiindex': is_multiindex
        }

    def _detect_index_columns(
        self,
        table_columns: List[TableColumnInfo]
    ) -> List[TableColumnInfo]:
        """
        Find columns marked as index columns.

        Args:
            table_columns: List of table columns

        Returns:
            List of index columns (may be empty)
        """
        return [col for col in table_columns if col.is_index_column]

    def _find_categorical_column(
        self,
        table_columns: List[TableColumnInfo]
    ) -> TableColumnInfo:
        """
        Find first categorical column (fallback if no index columns).

        Args:
            table_columns: List of table columns

        Returns:
            First categorical column or first column
        """
        for col in table_columns:
            if col.data_type == 'categorical':
                return col

        # Fallback: return first column
        return table_columns[0] if table_columns else None

    def _find_continuous_column(
        self,
        table_columns: List[TableColumnInfo]
    ) -> TableColumnInfo:
        """
        Find first continuous column (fallback if no index columns).

        Args:
            table_columns: List of table columns

        Returns:
            First continuous column or first column
        """
        for col in table_columns:
            if col.data_type == 'continuous':
                return col

        # Fallback: return first column
        return table_columns[0] if table_columns else None

    def _generate_method_name(
        self,
        method: LookupMethod,
        key_column: TableColumnInfo
    ) -> str:
        """
        Generate descriptive method name.

        Args:
            method: LookupMethod enum
            key_column: Index column used for lookup

        Returns:
            Method name string

        Examples:
            - select_by_material_type
            - interpolate_by_temperature
            - compound_lookup_material_temperature
        """
        # Clean column name (remove special chars, convert to lowercase)
        col_name = key_column.name or key_column.header_text
        clean_name = ''.join(c if c.isalnum() else '_' for c in col_name)
        clean_name = clean_name.strip('_').lower()

        # Replace multiple underscores with single
        while '__' in clean_name:
            clean_name = clean_name.replace('__', '_')

        # Generate name based on method
        if method == LookupMethod.SELECT_BY_CATEGORY:
            return f"select_by_{clean_name}"
        elif method in (LookupMethod.INTERPOLATE_LINEAR, LookupMethod.INTERPOLATE_SPLINE):
            return f"interpolate_by_{clean_name}"
        elif method == LookupMethod.COMPOUND_LOOKUP:
            return f"compound_lookup_{clean_name}"
        elif method == LookupMethod.EXACT_MATCH:
            return f"exact_match_{clean_name}"
        else:
            return f"lookup_{clean_name}"

    def _determine_interpolation_method(
        self,
        key_column: TableColumnInfo
    ) -> str:
        """
        Determine interpolation type based on column characteristics.

        Args:
            key_column: Column used for interpolation

        Returns:
            Interpolation type: 'linear', 'log', 'spline'
        """
        # Check if column name suggests logarithmic scale
        col_name = (key_column.name or key_column.header_text).lower()

        # Dimensionless numbers often need log scale
        log_keywords = ['reynolds', 'prandtl', 'nusselt', 'rayleigh',
                       'grashof', 'peclet', 'weber', 'froude']

        if any(keyword in col_name for keyword in log_keywords):
            return 'log'

        # Check for large value ranges (suggest log scale) - if available
        # Note: value_range not in TableColumnInfo dataclass, skip this check
        # Could be added in future enhancement

        # Default to linear interpolation
        return 'linear'
