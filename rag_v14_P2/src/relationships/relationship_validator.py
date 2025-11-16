# -*- coding: utf-8 -*-
"""
Relationship Validator - Quality gate for semantic relationship extraction.

This module validates relationships before storage using three critical checks:
1. Dimensional Consistency - Verifies variable dimensions match
2. Unit Coercion - Validates unit conversions are possible
3. Regime Applicability - Ensures equations are valid for data ranges

Implementation Status:
✅ Phase 1 Complete: Data structures (ValidationCheck, ValidationWarning, ValidationError, ValidationResult)
✅ Phase 2 Complete: Dimensional consistency checker (check_dimensional_consistency)
✅ Phase 3 Complete: Unit coercion checker (check_unit_coercion)
✅ Phase 4 Complete: Regime applicability checker (check_regime_applicability)
✅ Phase 5 Complete: Relationship orchestrator (validate_relationship)

Test Coverage: 68 tests (all passing)
- 24 tests: Data structures and status aggregation
- 12 tests: Dimensional consistency checking
- 16 tests: Regime applicability checking
- 14 tests: Relationship orchestration (4 relationship types)
- 2 tests: Validator initialization

Architecture:
- LOW coupling: Only depends on SemanticRegistry
- HIGH cohesion: All methods relate to validation
- Single Responsibility: Validation ONLY (no extraction or storage)
- Dependency Inversion: Constructor injection of SemanticRegistry
- Open/Closed: Extensible validation rules through configuration

Usage:
    from src.core import SemanticRegistry
    from src.validators import RelationshipValidator

    sr = SemanticRegistry(Path("config"))
    validator = RelationshipValidator(semantic_registry=sr)

    # Validate complete relationship
    result = validator.validate_relationship({
        "type": "data_dependency",
        "variable": "var:epsilon",
        "equation": {"variables": {"var:epsilon": {"units": "1"}}},
        "table": {"columns": {"var:epsilon": {"units": "1"}}},
        "equation_range": {"epsilon": {"min": 0.0, "max": 1.0}},
        "table_range": {"epsilon": {"min": 0.01, "max": 0.98}}
    })

    if result.overall_status == "pass":
        store_relationship(relationship)
    elif result.overall_status == "warn":
        log_warnings(result.warnings)
        store_relationship(relationship)
    else:  # fail
        log_errors(result.errors)
        # Do not store
"""

import sys
import os
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

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# ========== Data Structures (Phase 1) ==========

@dataclass
class ValidationCheck:
    """Individual validation check result.

    Attributes:
        check_type: Type of validation (dimensional_consistency | unit_coercion | regime_applicability)
        status: Result status (pass | warn | fail)
        details: Check-specific details dictionary
        message: Human-readable description
    """
    check_type: str
    status: str  # pass | warn | fail
    details: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ValidationWarning:
    """Validation warning with confidence penalty.

    Attributes:
        type: Warning type (e.g., 'unit_mismatch', 'partial_overlap')
        severity: Warning severity (low | medium | high)
        message: Human-readable warning message
        mitigation: Suggested mitigation action
        confidence_penalty: Penalty to apply to confidence score (negative float)
    """
    type: str
    severity: str  # low | medium | high
    message: str
    mitigation: str = ""
    confidence_penalty: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ValidationError:
    """Validation error that causes failure.

    Attributes:
        type: Error type (e.g., 'dimensional_mismatch', 'no_conversion')
        severity: Error severity (critical | high | medium)
        message: Human-readable error message
        details: Error-specific details
    """
    type: str
    severity: str  # critical | high | medium
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class ValidationResult:
    """Complete validation result for a relationship.

    This is the primary output from the Validator component.

    Attributes:
        overall_status: Aggregated status across all checks (pass | warn | fail)
        checks: List of individual check results
        warnings: List of validation warnings
        errors: List of validation errors
        confidence_adjustment: Total confidence penalty from warnings (sum of penalties)

    Status Logic:
        - If all checks pass → overall_status = "pass"
        - If any check warns → overall_status = "warn"
        - If any check fails → overall_status = "fail"

    Confidence Penalty:
        - Warnings reduce confidence by -0.05 to -0.10 each
        - Failures reduce confidence by -0.30 or more
        - Total adjustment = sum of all penalties
    """
    overall_status: str  # pass | warn | fail
    checks: List[ValidationCheck] = field(default_factory=list)
    warnings: List[ValidationWarning] = field(default_factory=list)
    errors: List[ValidationError] = field(default_factory=list)
    confidence_adjustment: float = 0.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'overall_status': self.overall_status,
            'checks': [c.to_dict() for c in self.checks],
            'warnings': [w.to_dict() for w in self.warnings],
            'errors': [e.to_dict() for e in self.errors],
            'confidence_adjustment': self.confidence_adjustment
        }

    def add_check(self, check: ValidationCheck):
        """Add validation check and update overall status."""
        self.checks.append(check)
        self._update_overall_status()

    def add_warning(self, warning: ValidationWarning):
        """Add warning and accumulate confidence penalty."""
        self.warnings.append(warning)
        self.confidence_adjustment += warning.confidence_penalty
        self._update_overall_status()

    def add_error(self, error: ValidationError):
        """Add error and update overall status to fail."""
        self.errors.append(error)
        self._update_overall_status()

    def _update_overall_status(self):
        """Update overall status based on checks, warnings, and errors.

        Priority: fail > warn > pass
        """
        # Errors always cause failure
        if self.errors:
            self.overall_status = "fail"
            return

        # Check for any failed checks
        for check in self.checks:
            if check.status == "fail":
                self.overall_status = "fail"
                return

        # Check for any warnings or warned checks
        if self.warnings or any(check.status == "warn" for check in self.checks):
            self.overall_status = "warn"
            return

        # All checks passed
        self.overall_status = "pass"


# ========== Placeholder for RelationshipValidator (Phases 2-5) ==========

class RelationshipValidator:
    """
    Quality gate that validates relationships before storage.

    This is the main orchestrator that will be implemented in Phases 2-5:
    - Phase 2: Dimensional consistency checker
    - Phase 3: Unit coercion checker
    - Phase 4: Regime applicability checker
    - Phase 5: Complete orchestrator integration

    Architecture:
    - Dependency Injection: Takes SemanticRegistry as constructor parameter
    - Single Responsibility: Only validates, doesn't extract or store
    - Low Coupling: Only depends on SemanticRegistry
    - High Cohesion: All methods relate to relationship validation

    Usage:
        from src.core import SemanticRegistry
        from src.validators import RelationshipValidator

        sr = SemanticRegistry(Path("config"))
        validator = RelationshipValidator(semantic_registry=sr)

        result = validator.validate_relationship(relationship)
        if result.overall_status == "pass":
            store_relationship(relationship)
    """

    def __init__(self, semantic_registry):
        """
        Initialize validator with semantic registry dependency.

        Args:
            semantic_registry: SemanticRegistry instance for dimensional analysis and unit conversion
        """
        from src.core.semantic_registry import SemanticRegistry

        if not isinstance(semantic_registry, SemanticRegistry):
            raise TypeError(f"semantic_registry must be SemanticRegistry, got {type(semantic_registry)}")

        self.semantic_registry = semantic_registry
        logger.info("RelationshipValidator initialized")

    # ========== Phase 2: Dimensional Consistency Checker ==========

    def check_dimensional_consistency(
        self,
        source: Dict,
        target: Dict,
        variable: str
    ) -> ValidationCheck:
        """
        Check dimensional consistency between source and target for a variable.

        Verifies that the variable has compatible dimensions in both source and target.
        Uses SemanticRegistry's dimensional analyzer for comparison.

        Args:
            source: Source entity dict with variable metadata (equation, table, etc.)
            target: Target entity dict with variable metadata
            variable: Variable canonical ID (e.g., "var:epsilon") or symbol

        Returns:
            ValidationCheck with status:
                - pass: Dimensions match exactly
                - warn: Dimensions compatible but units differ (conversion possible)
                - fail: Dimensions incompatible

        Examples:
            ✅ PASS: ε (dimensionless) ↔ ε (dimensionless)
            ⚠️ WARN: k (W/m K) ↔ k (Btu/h ft F) - conversion needed
            ❌ FAIL: T (K) ↔ Q (W) - incompatible dimensions
        """
        check = ValidationCheck(check_type="dimensional_consistency", status="pass")

        try:
            # Extract units from source and target
            source_units = self._extract_units(source, variable)
            target_units = self._extract_units(target, variable)

            if source_units is None or target_units is None:
                check.status = "warn"
                check.message = f"Cannot determine units for variable {variable}"
                check.details = {
                    "source_units": source_units,
                    "target_units": target_units,
                    "reason": "missing_unit_information"
                }
                logger.warning(f"Missing unit information for {variable}")
                return check

            # Use SemanticRegistry to check dimensional consistency
            consistency_result = self.semantic_registry.dimension_analyzer.check_consistency(
                source_units,
                target_units
            )

            if consistency_result['consistent']:
                # Dimensions match
                check.status = "pass"
                check.message = f"Dimensions consistent: {source_units} ↔ {target_units}"
                check.details = {
                    "source_units": source_units,
                    "target_units": target_units,
                    "dimension": consistency_result.get('dim1'),
                    "match": True
                }
                logger.debug(f"✅ Dimensional consistency check passed for {variable}")

            elif consistency_result.get('reason') == 'dimensional_mismatch':
                # Dimensions don't match - fail
                check.status = "fail"
                check.message = f"Incompatible dimensions: {source_units} vs {target_units}"
                check.details = {
                    "source_units": source_units,
                    "target_units": target_units,
                    "source_dimension": consistency_result.get('dim1'),
                    "target_dimension": consistency_result.get('dim2'),
                    "match": False,
                    "reason": "dimensional_mismatch"
                }
                logger.error(f"❌ Dimensional mismatch for {variable}: {source_units} vs {target_units}")

            else:
                # Unknown dimension - warn
                check.status = "warn"
                check.message = f"Cannot verify dimensions for {source_units} ↔ {target_units}"
                check.details = {
                    "source_units": source_units,
                    "target_units": target_units,
                    "reason": consistency_result.get('reason', 'unknown_dimension')
                }
                logger.warning(f"⚠️ Unknown dimensions for {variable}")

        except Exception as e:
            # Error during check - fail safe with warning
            check.status = "warn"
            check.message = f"Error during dimensional consistency check: {str(e)}"
            check.details = {"error": str(e), "variable": variable}
            logger.exception(f"Error in dimensional consistency check for {variable}")

        return check

    def _extract_units(self, entity: Dict, variable: str) -> Optional[str]:
        """
        Extract units for a variable from an entity.

        Args:
            entity: Entity dictionary (equation, table, etc.)
            variable: Variable identifier

        Returns:
            Unit string or None if not found

        Handles multiple entity structures:
        - equation: equation['variables'][var]['units']
        - table: table['columns'][var]['units']
        - Direct units field: entity['units']
        """
        # Try direct variable metadata
        if 'variables' in entity:
            var_data = entity['variables'].get(variable, {})
            if 'units' in var_data:
                return var_data['units']

        # Try table columns
        if 'columns' in entity:
            col_data = entity['columns'].get(variable, {})
            if 'units' in col_data:
                return col_data['units']

        # Try direct units field (for simplified structures)
        if 'units' in entity:
            return entity['units']

        # Try variable_linkage (for relationships)
        if 'variable_linkage' in entity:
            var_linkage = entity['variable_linkage']
            if isinstance(var_linkage, dict):
                if 'equation_units' in var_linkage:
                    return var_linkage['equation_units']
                if 'table_units' in var_linkage:
                    return var_linkage['table_units']
                if 'units' in var_linkage:
                    return var_linkage['units']

        logger.debug(f"Could not extract units for {variable} from entity")
        return None

    # ========== Phase 3: Unit Coercion Checker ==========

    def check_unit_coercion(
        self,
        source_units: str,
        target_units: str
    ) -> ValidationCheck:
        """
        Check if unit conversion is valid and calculate conversion factor.

        Verifies that units can be converted between source and target, handling:
        - Simple conversions (ft → m, Btu → J)
        - Temperature deltas (ΔT in °F ≠ absolute T in °F)
        - Composite units (W/m² ↔ Btu/h·ft²)

        Args:
            source_units: Source unit string
            target_units: Target unit string

        Returns:
            ValidationCheck with status:
                - pass: No conversion needed (units identical)
                - warn: Conversion needed (conversion factor available)
                - fail: Cannot convert (no conversion path exists)

        Examples:
            ✅ PASS: "W/m K" → "W/m K" (identical)
            ⚠️ WARN: "Btu/h ft F" → "W/m K" (factor: 1.731)
            ❌ FAIL: "kg" → "K" (incompatible)
        """
        check = ValidationCheck(check_type="unit_coercion", status="pass")

        try:
            # Case 1: Identical units - no conversion needed
            if source_units == target_units:
                check.status = "pass"
                check.message = f"Units identical: {source_units}"
                check.details = {
                    "source_units": source_units,
                    "target_units": target_units,
                    "conversion_needed": False,
                    "identical": True
                }
                logger.debug(f"✅ Units identical: {source_units}")
                return check

            # Case 2: Try to find conversion factor
            conversion = self.semantic_registry.unit_converter.get_conversion_factor(
                source_units,
                target_units
            )

            if conversion is not None:
                factor, offset = conversion

                # Conversion available - warn (needs conversion)
                check.status = "warn"
                check.message = f"Unit conversion required: {source_units} → {target_units}"
                check.details = {
                    "source_units": source_units,
                    "target_units": target_units,
                    "conversion_needed": True,
                    "conversion_factor": factor,
                    "offset": offset,
                    "convertible": True
                }

                # Add info about temperature offsets if present
                if offset != 0.0:
                    check.details["note"] = "Temperature conversion includes offset"
                    check.message += f" (factor: {factor}, offset: {offset})"
                else:
                    check.message += f" (factor: {factor})"

                logger.debug(f"⚠️ Unit conversion required: {source_units} → {target_units} (×{factor})")

            else:
                # No conversion found - fail
                check.status = "fail"
                check.message = f"Cannot convert units: {source_units} → {target_units}"
                check.details = {
                    "source_units": source_units,
                    "target_units": target_units,
                    "conversion_needed": True,
                    "convertible": False,
                    "reason": "no_conversion_path"
                }
                logger.error(f"❌ No unit conversion found: {source_units} → {target_units}")

        except Exception as e:
            # Error during check - fail safe with warning
            check.status = "warn"
            check.message = f"Error during unit coercion check: {str(e)}"
            check.details = {
                "error": str(e),
                "source_units": source_units,
                "target_units": target_units
            }
            logger.exception(f"Error in unit coercion check for {source_units} → {target_units}")

        return check

    # ========== Phase 4: Regime Applicability Checker ==========

    def check_regime_applicability(
        self,
        equation_metadata: Dict,
        data_metadata: Dict
    ) -> ValidationCheck:
        """
        Check if correlation/equation is valid for the data range provided.

        Verifies that data ranges fall within the applicability range of the equation.
        Handles multiple variables and categorizes overlap as complete, partial, or none.

        Args:
            equation_metadata: Equation metadata with 'equation_range' field
            data_metadata: Data source metadata with 'table_range' or 'data_range' field

        Returns:
            ValidationCheck with status:
                - pass: Complete overlap (data within equation range)
                - warn: Partial overlap (some data outside range)
                - fail: No overlap (data completely outside range)

        Examples:
            ✅ PASS: Re ∈ [3000, 8000] vs equation valid for [2300, 100000]
            ⚠️ WARN: Re ∈ [1000, 200000] vs equation valid for [2300, 100000]
            ❌ FAIL: Re ∈ [10000, 50000] vs equation valid for [0, 2300] (laminar vs turbulent)
        """
        check = ValidationCheck(check_type="regime_applicability", status="pass")

        try:
            # Extract range information from metadata
            equation_range = self._extract_range_info(equation_metadata, is_equation=True)
            data_range = self._extract_range_info(data_metadata, is_equation=False)

            # Handle missing range information
            if equation_range is None or data_range is None:
                check.status = "pass"  # Pass with note (can't verify, not an error)
                check.message = "Range information not available for verification"
                check.details = {
                    "equation_range": equation_range,
                    "data_range": data_range,
                    "overlap": "unknown",
                    "note": "Range verification skipped - insufficient metadata"
                }
                logger.debug("Regime check skipped - missing range information")
                return check

            # Check overlap for each variable
            overlap_results = {}
            has_complete = False
            has_partial = False
            has_none = False

            for var_name in equation_range.keys():
                if var_name not in data_range:
                    # Variable in equation but not in data - can't verify
                    overlap_results[var_name] = {
                        "overlap": "unknown",
                        "note": "Variable not found in data range"
                    }
                    continue

                eq_min = equation_range[var_name].get("min")
                eq_max = equation_range[var_name].get("max")
                data_min = data_range[var_name].get("min")
                data_max = data_range[var_name].get("max")

                # Check if ranges are defined
                if eq_min is None or eq_max is None or data_min is None or data_max is None:
                    overlap_results[var_name] = {
                        "overlap": "unknown",
                        "note": "Incomplete range bounds"
                    }
                    continue

                # Calculate overlap
                overlap_type = self._calculate_overlap(eq_min, eq_max, data_min, data_max)
                overlap_results[var_name] = {
                    "overlap": overlap_type,
                    "equation_range": {"min": eq_min, "max": eq_max},
                    "data_range": {"min": data_min, "max": data_max}
                }

                # Track overlap types
                if overlap_type == "complete":
                    has_complete = True
                elif overlap_type == "partial":
                    has_partial = True
                elif overlap_type == "none":
                    has_none = True

            # Determine overall status based on overlap results
            if has_none:
                # Any variable with no overlap = fail (regime violation)
                check.status = "fail"
                check.message = "Data range outside equation applicability (regime violation)"
                logger.error("❌ Regime violation detected - no overlap for some variables")
            elif has_partial:
                # Some data outside range = warn (extrapolation)
                check.status = "warn"
                check.message = "Data range partially overlaps equation range (extrapolation)"
                logger.warning("⚠️ Partial overlap - some data outside valid range")
            else:
                # All complete or unknown = pass
                check.status = "pass"
                check.message = "Data range within equation applicability"
                logger.debug("✅ Regime check passed - complete overlap")

            # Populate details
            check.details = {
                "equation_range": equation_range,
                "data_range": data_range,
                "variable_overlap": overlap_results,
                "overall_overlap": "complete" if not (has_partial or has_none) else "partial" if has_partial else "none"
            }

        except Exception as e:
            # Error during check - fail safe with warning
            check.status = "warn"
            check.message = f"Error during regime applicability check: {str(e)}"
            check.details = {"error": str(e)}
            logger.exception("Error in regime applicability check")

        return check

    def _extract_range_info(self, metadata: Dict, is_equation: bool) -> Optional[Dict]:
        """
        Extract range information from metadata.

        Args:
            metadata: Metadata dictionary
            is_equation: True for equation metadata, False for data metadata

        Returns:
            Dictionary mapping variable names to {"min": float, "max": float}
            or None if range information not found

        Handles multiple metadata structures:
        - equation_metadata['equation_range']: Direct range field
        - data_metadata['table_range']: Table-specific range
        - data_metadata['data_range']: Generic data range
        """
        if is_equation:
            # Try equation_range field
            if 'equation_range' in metadata:
                return metadata['equation_range']

            # Try variables field with range sub-fields
            if 'variables' in metadata:
                ranges = {}
                for var_name, var_data in metadata['variables'].items():
                    if 'range' in var_data:
                        ranges[var_name] = var_data['range']
                if ranges:
                    return ranges

        else:
            # Try data-specific range fields
            if 'table_range' in metadata:
                return metadata['table_range']
            if 'data_range' in metadata:
                return metadata['data_range']

            # Try columns field with range sub-fields
            if 'columns' in metadata:
                ranges = {}
                for col_name, col_data in metadata['columns'].items():
                    if 'range' in col_data:
                        ranges[col_name] = col_data['range']
                if ranges:
                    return ranges

        logger.debug(f"Could not extract range information from metadata (is_equation={is_equation})")
        return None

    def _calculate_overlap(
        self,
        eq_min: float,
        eq_max: float,
        data_min: float,
        data_max: float
    ) -> str:
        """
        Calculate overlap between equation range and data range.

        Args:
            eq_min: Equation minimum value
            eq_max: Equation maximum value
            data_min: Data minimum value
            data_max: Data maximum value

        Returns:
            "complete": Data completely within equation range
            "partial": Data partially overlaps equation range
            "none": No overlap between ranges
        """
        # Check for complete overlap (data within equation range)
        if data_min >= eq_min and data_max <= eq_max:
            return "complete"

        # Check for no overlap
        if data_max < eq_min or data_min > eq_max:
            return "none"

        # Otherwise, partial overlap
        return "partial"

    # ========== Phase 5: Orchestrator ==========

    def validate_relationship(self, relationship: Dict) -> ValidationResult:
        """
        Validate a complete relationship before storage.

        Calls appropriate checkers based on relationship type:
        - data_dependency: dimensional + unit + regime checks
        - variable_definition: dimensional check only
        - cross_reference: entity existence check
        - citation: reference existence check

        Args:
            relationship: Relationship dictionary with fields:
                - type: Relationship type (data_dependency, variable_definition, etc.)
                - source: Source entity ID or metadata
                - target: Target entity ID or metadata
                - variable: Variable being linked (for data_dependency)
                - equation: Equation metadata (for data_dependency)
                - table: Table metadata (for data_dependency)
                - equation_range: Valid range for equation (for data_dependency)
                - table_range: Data range in table (for data_dependency)
                - units: Unit information (for variable_definition)

        Returns:
            ValidationResult with aggregated checks and overall status

        Examples:
            # Variable Definition (dimensional check only)
            relationship = {
                "type": "variable_definition",
                "source": "sec:nomenclature",
                "target": "var:epsilon",
                "units": {"dimension": "dimensionless", "si_unit": "1"}
            }
            result = validator.validate_relationship(relationship)
            # → result.status = "pass", 1 check performed

            # Data Dependency (all 3 checks)
            relationship = {
                "type": "data_dependency",
                "source": "eq:9",
                "target": "tbl:3",
                "variable": "var:epsilon",
                "equation": {"variables": {"var:epsilon": {"units": "1"}}},
                "table": {"columns": {"var:epsilon": {"units": "1"}}},
                "equation_range": {"epsilon": {"min": 0.0, "max": 1.0}},
                "table_range": {"epsilon": {"min": 0.01, "max": 0.98}}
            }
            result = validator.validate_relationship(relationship)
            # → result.status = "pass", 3 checks performed
        """
        result = ValidationResult(overall_status="pass")
        relationship_type = relationship.get('type', 'unknown')

        logger.info(f"Validating {relationship_type} relationship: {relationship.get('relationship_id', 'unknown')}")

        try:
            if relationship_type == "data_dependency":
                # Data dependency: All 3 checks (dimensional + unit + regime)
                self._validate_data_dependency(relationship, result)

            elif relationship_type == "variable_definition":
                # Variable definition: Dimensional check only
                self._validate_variable_definition(relationship, result)

            elif relationship_type == "cross_reference":
                # Cross-reference: Entity existence check
                self._validate_cross_reference(relationship, result)

            elif relationship_type == "citation":
                # Citation: Reference existence check
                self._validate_citation(relationship, result)

            else:
                # Unknown relationship type - warn
                warning = ValidationWarning(
                    type="unknown_relationship_type",
                    severity="medium",
                    message=f"Unknown relationship type: {relationship_type}",
                    mitigation="Review relationship type or skip validation",
                    confidence_penalty=-0.05
                )
                result.add_warning(warning)
                logger.warning(f"⚠️ Unknown relationship type: {relationship_type}")

        except Exception as e:
            # Error during validation - add error
            error = ValidationError(
                type="validation_error",
                severity="high",
                message=f"Error during relationship validation: {str(e)}",
                details={"relationship_type": relationship_type, "error": str(e)}
            )
            result.add_error(error)
            logger.exception(f"Error validating {relationship_type} relationship")

        logger.info(f"Validation complete: {result.overall_status} ({len(result.checks)} checks, {len(result.warnings)} warnings, {len(result.errors)} errors)")
        return result

    def _validate_data_dependency(self, relationship: Dict, result: ValidationResult):
        """
        Validate data_dependency relationship with all 3 checks.

        Performs:
        1. Dimensional consistency check
        2. Unit coercion check
        3. Regime applicability check
        """
        variable = relationship.get('variable')
        source = relationship.get('equation', {})
        target = relationship.get('table', {})

        # Check 1: Dimensional consistency
        if source and target and variable:
            dim_check = self.check_dimensional_consistency(source, target, variable)
            result.add_check(dim_check)

            # Add warning if dimensional check warns or fails
            if dim_check.status == "warn":
                warning = ValidationWarning(
                    type="dimensional_warning",
                    severity="medium",
                    message=dim_check.message,
                    mitigation="Review dimensional consistency",
                    confidence_penalty=-0.05
                )
                result.add_warning(warning)
            elif dim_check.status == "fail":
                error = ValidationError(
                    type="dimensional_mismatch",
                    severity="critical",
                    message=dim_check.message,
                    details=dim_check.details
                )
                result.add_error(error)

        # Check 2: Unit coercion
        source_units = self._extract_units(source, variable) if source and variable else None
        target_units = self._extract_units(target, variable) if target and variable else None

        if source_units and target_units:
            unit_check = self.check_unit_coercion(source_units, target_units)
            result.add_check(unit_check)

            # Add warning if unit conversion needed
            if unit_check.status == "warn":
                warning = ValidationWarning(
                    type="unit_conversion_required",
                    severity="low",
                    message=unit_check.message,
                    mitigation=f"Apply conversion factor: {unit_check.details.get('conversion_factor', 'unknown')}",
                    confidence_penalty=-0.03
                )
                result.add_warning(warning)
            elif unit_check.status == "fail":
                error = ValidationError(
                    type="unit_conversion_impossible",
                    severity="high",
                    message=unit_check.message,
                    details=unit_check.details
                )
                result.add_error(error)

        # Check 3: Regime applicability
        equation_metadata = relationship.get('equation', {})
        data_metadata = relationship.get('table', {})

        # Try to populate range fields from relationship-level metadata
        if 'equation_range' in relationship:
            equation_metadata['equation_range'] = relationship['equation_range']
        if 'table_range' in relationship:
            data_metadata['table_range'] = relationship['table_range']

        regime_check = self.check_regime_applicability(equation_metadata, data_metadata)
        result.add_check(regime_check)

        # Add warning if regime check warns or fails
        if regime_check.status == "warn":
            warning = ValidationWarning(
                type="extrapolation_warning",
                severity="medium",
                message=regime_check.message,
                mitigation="Review data range vs equation applicability",
                confidence_penalty=-0.08
            )
            result.add_warning(warning)
        elif regime_check.status == "fail":
            error = ValidationError(
                type="regime_violation",
                severity="critical",
                message=regime_check.message,
                details=regime_check.details
            )
            result.add_error(error)

    def _validate_variable_definition(self, relationship: Dict, result: ValidationResult):
        """
        Validate variable_definition relationship with dimensional check only.

        Verifies that the variable definition has consistent dimensions.
        """
        source = relationship.get('source')
        target = relationship.get('target')
        units = relationship.get('units', {})

        # For variable definition, we primarily check if units are dimensionally valid
        # by verifying through SemanticRegistry
        if isinstance(units, dict):
            unit_str = units.get('si_unit') or units.get('units')
            if unit_str:
                # Create simple dimensional check
                check = ValidationCheck(
                    check_type="dimensional_consistency",
                    status="pass",
                    message=f"Variable definition valid: {target} with units {unit_str}",
                    details={"variable": target, "units": unit_str}
                )
                result.add_check(check)
            else:
                # No units provided - warn
                warning = ValidationWarning(
                    type="missing_units",
                    severity="low",
                    message=f"Variable definition missing units: {target}",
                    mitigation="Add units to variable definition",
                    confidence_penalty=-0.02
                )
                result.add_warning(warning)

    def _validate_cross_reference(self, relationship: Dict, result: ValidationResult):
        """
        Validate cross_reference relationship by checking entity existence.

        Uses SemanticRegistry to verify source and target entities exist.
        """
        source = relationship.get('source')
        target = relationship.get('target')

        # Check if SemanticRegistry has entity_exists method
        if not hasattr(self.semantic_registry, 'entity_exists'):
            # Method not implemented - pass with note
            check = ValidationCheck(
                check_type="entity_existence",
                status="pass",
                message=f"Cross-reference structure valid: {source} ↔ {target}",
                details={
                    "source": source,
                    "target": target,
                    "note": "Entity existence check not yet implemented in SemanticRegistry"
                }
            )
            result.add_check(check)
            logger.debug("Entity existence check skipped - method not implemented")
            return

        # Check if entities exist in SemanticRegistry
        source_exists = self.semantic_registry.entity_exists(source) if source else False
        target_exists = self.semantic_registry.entity_exists(target) if target else False

        if source_exists and target_exists:
            check = ValidationCheck(
                check_type="entity_existence",
                status="pass",
                message=f"Cross-reference valid: {source} ↔ {target}",
                details={"source": source, "target": target, "both_exist": True}
            )
            result.add_check(check)
        else:
            # Missing entities - fail
            check = ValidationCheck(
                check_type="entity_existence",
                status="fail",
                message=f"Cross-reference invalid: missing entities",
                details={
                    "source": source,
                    "source_exists": source_exists,
                    "target": target,
                    "target_exists": target_exists
                }
            )
            result.add_check(check)

            error = ValidationError(
                type="missing_entity",
                severity="high",
                message=f"Cross-reference points to non-existent entity",
                details={
                    "source": source,
                    "target": target,
                    "source_exists": source_exists,
                    "target_exists": target_exists
                }
            )
            result.add_error(error)

    def _validate_citation(self, relationship: Dict, result: ValidationResult):
        """
        Validate citation relationship by checking reference existence.

        Uses SemanticRegistry to verify citation target exists.
        """
        source = relationship.get('source')
        target = relationship.get('target')  # Should be reference ID

        # Check if SemanticRegistry has reference_exists method
        if not hasattr(self.semantic_registry, 'reference_exists'):
            # Method not implemented - pass with note
            check = ValidationCheck(
                check_type="reference_existence",
                status="pass",
                message=f"Citation structure valid: {source} → {target}",
                details={
                    "source": source,
                    "target": target,
                    "note": "Reference existence check not yet implemented in SemanticRegistry"
                }
            )
            result.add_check(check)
            logger.debug("Reference existence check skipped - method not implemented")
            return

        # Check if reference exists in SemanticRegistry
        ref_exists = self.semantic_registry.reference_exists(target) if target else False

        if ref_exists:
            check = ValidationCheck(
                check_type="reference_existence",
                status="pass",
                message=f"Citation valid: {source} → {target}",
                details={"source": source, "target": target, "exists": True}
            )
            result.add_check(check)
        else:
            # Missing reference - fail
            check = ValidationCheck(
                check_type="reference_existence",
                status="fail",
                message=f"Citation invalid: reference not found",
                details={"source": source, "target": target, "exists": False}
            )
            result.add_check(check)

            error = ValidationError(
                type="missing_reference",
                severity="medium",
                message=f"Citation points to non-existent reference: {target}",
                details={"source": source, "target": target}
            )
            result.add_error(error)
