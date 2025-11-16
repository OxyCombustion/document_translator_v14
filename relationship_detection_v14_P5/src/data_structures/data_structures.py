#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Structures for Data Dependency Detector

Defines dataclasses for representing equation-table data dependencies,
variable linkages, and related metadata.

Author: V12 Development Team
Created: 2025-11-03
"""

import sys
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum

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


class VariableRole(Enum):
    """Role of variable in equation context"""
    INPUT = "input"           # Independent variable (temperature, pressure, Re)
    OUTPUT = "output"         # Dependent variable (heat transfer coefficient, friction factor)
    PARAMETER = "parameter"   # Constant needed for evaluation (emissivity, conductivity)


class LookupMethod(Enum):
    """Method for retrieving data from table"""
    SELECT_BY_CATEGORY = "select_by_category"       # Categorical lookup (material type)
    INTERPOLATE_LINEAR = "interpolate_linear"       # Linear interpolation (temperature)
    INTERPOLATE_SPLINE = "interpolate_spline"       # Spline interpolation (smooth curves)
    COMPOUND_LOOKUP = "compound_lookup"             # Multi-indexed (material + temperature)
    EXACT_MATCH = "exact_match"                     # Direct value lookup


class ValidationStatus(Enum):
    """Validation check result status"""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class UnitInfo:
    """Unit and conversion information"""
    equation_units: str
    table_units: str
    conversion_needed: bool
    conversion_factor: Optional[float] = None
    conversion_expression: Optional[str] = None


@dataclass
class ValidationCheck:
    """Individual validation check result"""
    check_type: str
    status: ValidationStatus
    details: Dict[str, Any]
    message: Optional[str] = None


@dataclass
class ValidationResult:
    """Overall validation result for dependency"""
    overall_status: ValidationStatus
    checks: List[ValidationCheck]
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConfidenceFactors:
    """Individual factors contributing to confidence score"""
    symbol_exact_match: float = 0.0
    dimensional_consistency: float = 0.0
    semantic_tag_overlap: float = 0.0
    name_similarity: float = 0.0


@dataclass
class ConfidenceScore:
    """Confidence scoring for dependency match"""
    score: float
    method: str
    factors: ConfidenceFactors


@dataclass
class VariableLinkage:
    """Link between equation variable and table column"""
    variable_id: str              # Canonical ID from SemanticRegistry (e.g., "var:epsilon")
    symbol: str                   # Symbol used (e.g., "ε")
    name: str                     # Variable name (e.g., "emissivity")
    equation_role: VariableRole   # Role in equation
    table_column: str             # Matching table column header
    table_column_index: int       # Column position in table (0-indexed)
    lookup_method: LookupMethod   # How to retrieve data
    lookup_key_column: Optional[str] = None   # Index column for categorical lookup
    units: Optional[UnitInfo] = None


@dataclass
class DataProperties:
    """Properties of data in table column"""
    data_type: str                # "categorical", "continuous", "range", "discrete"
    value_range: Optional[Dict[str, float]] = None    # {"min": 0.01, "max": 0.98}
    lookup_structure: Optional[str] = None            # "categorical_by_material", "continuous_temperature"
    categories: Optional[List[str]] = None            # List of category values
    sample_values: Optional[List[Any]] = None         # Sample data points


@dataclass
class EntityReference:
    """Reference to an entity (equation or table)"""
    entity_id: str
    entity_type: str
    page: int
    section: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageContext:
    """Usage context and examples for dependency"""
    how_to_use: str
    example: Optional[str] = None
    notes: Optional[List[str]] = None


@dataclass
class Provenance:
    """Provenance information for relationship"""
    detector: str = "DataDependencyDetector"
    version: str = "1.0.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
    config_hash: Optional[str] = None


@dataclass
class DataDependency:
    """Complete data dependency relationship between equation and table"""
    # Required fields (no defaults)
    relationship_id: str
    source: str                   # Equation ID (e.g., "eq:9")
    target: str                   # Table ID (e.g., "tbl:3")
    equation: EntityReference
    table: EntityReference
    variable_linkage: List[VariableLinkage]

    # Optional fields (with defaults) - must come after required fields
    edge_type: str = "REQUIRES_DATA_FROM"
    data_properties: Optional[DataProperties] = None
    confidence: Optional[ConfidenceScore] = None
    validation: Optional[ValidationResult] = None
    usage_context: Optional[UsageContext] = None
    provenance: Optional[Provenance] = field(default_factory=Provenance)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert dataclass to dictionary for JSON serialization.

        Returns:
            Dictionary representation with all fields
        """
        def _serialize(obj):
            """Recursively serialize dataclass objects"""
            if isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, (list, tuple)):
                return [_serialize(item) for item in obj]
            elif isinstance(obj, dict):
                return {k: _serialize(v) for k, v in obj.items()}
            elif hasattr(obj, '__dict__'):
                return _serialize(obj.__dict__)
            else:
                return obj

        return _serialize(self.__dict__)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataDependency':
        """
        Create DataDependency from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            DataDependency instance
        """
        # Convert nested dicts back to dataclasses
        if 'equation' in data:
            data['equation'] = EntityReference(**data['equation'])

        if 'table' in data:
            data['table'] = EntityReference(**data['table'])

        if 'variable_linkage' in data:
            linkages = []
            for linkage_data in data['variable_linkage']:
                # Convert enum strings back to enums
                if 'equation_role' in linkage_data:
                    linkage_data['equation_role'] = VariableRole(linkage_data['equation_role'])
                if 'lookup_method' in linkage_data:
                    linkage_data['lookup_method'] = LookupMethod(linkage_data['lookup_method'])
                if 'units' in linkage_data and linkage_data['units']:
                    linkage_data['units'] = UnitInfo(**linkage_data['units'])
                linkages.append(VariableLinkage(**linkage_data))
            data['variable_linkage'] = linkages

        if 'data_properties' in data and data['data_properties']:
            data['data_properties'] = DataProperties(**data['data_properties'])

        if 'confidence' in data and data['confidence']:
            conf_data = data['confidence']
            if 'factors' in conf_data:
                conf_data['factors'] = ConfidenceFactors(**conf_data['factors'])
            data['confidence'] = ConfidenceScore(**conf_data)

        if 'validation' in data and data['validation']:
            val_data = data['validation']
            if 'checks' in val_data:
                checks = []
                for check_data in val_data['checks']:
                    if 'status' in check_data:
                        check_data['status'] = ValidationStatus(check_data['status'])
                    checks.append(ValidationCheck(**check_data))
                val_data['checks'] = checks
            if 'overall_status' in val_data:
                val_data['overall_status'] = ValidationStatus(val_data['overall_status'])
            data['validation'] = ValidationResult(**val_data)

        if 'usage_context' in data and data['usage_context']:
            data['usage_context'] = UsageContext(**data['usage_context'])

        if 'provenance' in data and data['provenance']:
            data['provenance'] = Provenance(**data['provenance'])

        return cls(**data)


# Type aliases for convenience
VariableLinkages = List[VariableLinkage]
DataDependencies = List[DataDependency]
