#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Dependency Detector - Main Orchestrator

Coordinates all components to detect equation→table data dependencies:
1. Extract variables from equations
2. Analyze table columns
3. Match variables to columns
4. Generate lookup methods
5. Validate relationships (MANDATORY)
6. Export to JSON

Author: V12 Development Team
Created: 2025-11-04
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
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
from src.validators.relationship_validator import RelationshipValidator
from src.detectors.equation_variable_extractor import EquationVariableExtractor
from src.detectors.table_column_analyzer import TableColumnAnalyzer
from src.detectors.variable_matching_engine import VariableMatchingEngine
from src.detectors.lookup_method_generator import LookupMethodGenerator
from src.detectors.data_structures import (
    DataDependency, EntityReference, VariableLinkage,
    UsageContext, Provenance, DataProperties,
    ConfidenceScore, ConfidenceFactors, ValidationResult
)


class DataDependencyDetector:
    """
    Main orchestrator for equation→table data dependency detection.

    Coordinates all sub-components:
    - EquationVariableExtractor: Extract variables from equations
    - TableColumnAnalyzer: Analyze table columns
    - VariableMatchingEngine: Match variables to columns
    - LookupMethodGenerator: Generate lookup methods
    - RelationshipValidator: Validate dependencies (MANDATORY)

    Architecture:
    - Dependency injection (SemanticRegistry, Validator)
    - Configuration-driven (YAML)
    - Comprehensive validation before export
    """

    def __init__(
        self,
        semantic_registry: SemanticRegistry,
        validator: RelationshipValidator,
        config_path: Path
    ):
        """
        Initialize data dependency detector.

        Args:
            semantic_registry: SemanticRegistry for symbol resolution
            validator: RelationshipValidator for validation (MANDATORY)
            config_path: Path to data_dependency_config.yaml
        """
        self.semantic_registry = semantic_registry
        self.validator = validator
        self.config_path = config_path
        self.config = self._load_config(config_path)

        # Initialize sub-components
        self.equation_extractor = EquationVariableExtractor(semantic_registry, self.config)
        self.table_analyzer = TableColumnAnalyzer(semantic_registry, self.config)
        self.matching_engine = VariableMatchingEngine(semantic_registry, self.config)
        self.lookup_generator = LookupMethodGenerator(self.config)

    def _load_config(self, config_path: Path) -> Dict:
        """
        Load configuration from YAML.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def detect_all_dependencies(
        self,
        equation_metadata: List[Dict[str, Any]],
        table_metadata: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect all equation→table data dependencies.

        Main orchestrator method that coordinates:
        1. Extract variables from all equations
        2. Analyze all table columns
        3. For each equation-table pair:
           a. Match equation variables to table columns
           b. Filter by confidence threshold (≥0.75)
           c. Generate lookup methods
           d. Build relationship dicts
           e. Validate relationships (MANDATORY via Validator)
        4. Export validated relationships to JSON

        Args:
            equation_metadata: List of equation metadata dicts
            table_metadata: List of table metadata dicts

        Returns:
            List of validated DataDependency dicts (only relationships that passed validation)
        """
        all_dependencies = []

        # Step 1: Extract variables from all equations
        print(f"\n📐 Extracting variables from {len(equation_metadata)} equations...")
        equation_variables = {}  # eq_id → List[EquationVariable]
        for eq in equation_metadata:
            try:
                vars = self.equation_extractor.extract_variables(eq)
                equation_variables[eq['equation_id']] = vars
                print(f"  • {eq['equation_id']}: {len(vars)} variables")
            except Exception as e:
                print(f"  ⚠️  Error extracting from {eq['equation_id']}: {e}")
                equation_variables[eq['equation_id']] = []

        # Step 2: Analyze all table columns
        print(f"\n📊 Analyzing columns from {len(table_metadata)} tables...")
        table_columns = {}  # tbl_id → List[TableColumnInfo]
        for tbl in table_metadata:
            try:
                cols = self.table_analyzer.analyze_table_columns(tbl)
                table_columns[tbl['table_id']] = cols
                print(f"  • {tbl['table_id']}: {len(cols)} columns")
            except Exception as e:
                print(f"  ⚠️  Error analyzing {tbl['table_id']}: {e}")
                table_columns[tbl['table_id']] = []

        # Step 3: Match and build dependencies
        print(f"\n🔗 Matching variables to table columns...")
        confidence_threshold = self.config['matching']['thresholds']['minimum_confidence']
        print(f"   Confidence threshold: {confidence_threshold}")

        match_count = 0
        for eq_id, eq_vars in equation_variables.items():
            if not eq_vars:
                continue

            # Find corresponding equation metadata
            eq_metadata = next((e for e in equation_metadata if e['equation_id'] == eq_id), None)
            if not eq_metadata:
                continue

            for tbl_id, tbl_cols in table_columns.items():
                if not tbl_cols:
                    continue

                # Find corresponding table metadata
                tbl_metadata = next((t for t in table_metadata if t['table_id'] == tbl_id), None)
                if not tbl_metadata:
                    continue

                # Match variables to columns
                try:
                    linkages, confidences = self.matching_engine.match_variables(eq_vars, tbl_cols)

                    # Process each match
                    for linkage, confidence in zip(linkages, confidences):
                        if confidence.score >= confidence_threshold:
                            match_count += 1
                            print(f"  ✅ Match {match_count}: {eq_id} → {tbl_id} via {linkage.symbol} (conf: {confidence.score:.3f})")

                            # Generate lookup method
                            lookup_info = self.lookup_generator.generate_lookup_method(
                                tbl_metadata,
                                tbl_cols,
                                linkage
                            )

                            # Update linkage with lookup info
                            linkage.lookup_method = lookup_info.method
                            linkage.lookup_key_column = lookup_info.lookup_key_column

                            # Build dependency dict
                            dependency = self._build_dependency(
                                eq_metadata,
                                tbl_metadata,
                                linkage,
                                confidence,
                                lookup_info
                            )

                            # MANDATORY: Validate dependency
                            validated_dependency = self._validate_dependency(dependency)

                            # Only include if validation passed or warned (not failed)
                            if validated_dependency['validation']['overall_status'] in ['pass', 'warn']:
                                all_dependencies.append(validated_dependency)
                            else:
                                print(f"    ⚠️  Validation failed - dependency rejected")

                except Exception as e:
                    print(f"  ❌ Error matching {eq_id} → {tbl_id}: {e}")

        print(f"\n✅ Total dependencies detected: {len(all_dependencies)}")
        return all_dependencies

    def _build_dependency(
        self,
        eq_metadata: Dict[str, Any],
        tbl_metadata: Dict[str, Any],
        linkage: VariableLinkage,
        confidence: ConfidenceScore,
        lookup_info: Any
    ) -> Dict[str, Any]:
        """
        Build DataDependency relationship dictionary.

        Format matches SEMANTIC_RELATIONSHIP_EXTRACTION_FINAL_PLAN.md Part 4.2

        Args:
            eq_metadata: Equation metadata dict
            tbl_metadata: Table metadata dict
            linkage: VariableLinkage between equation var and table column
            confidence: ConfidenceScore for the match
            lookup_info: LookupMethodInfo from generator

        Returns:
            DataDependency dict ready for validation
        """
        # Generate relationship ID
        var_suffix = linkage.variable_id.split(':')[-1][:3] if ':' in linkage.variable_id else linkage.symbol[:3]
        relationship_id = f"datadep:{eq_metadata['equation_id']}_{tbl_metadata['table_id']}_{var_suffix}"

        # Build dependency dict
        dependency = {
            "relationship_id": relationship_id,
            "edge_type": "REQUIRES_DATA_FROM",
            "source": eq_metadata['equation_id'],
            "target": tbl_metadata['table_id'],
            "equation": {
                "entity_id": eq_metadata['equation_id'],
                "entity_type": "equation",
                "page": eq_metadata.get('page', 0),
                "section": eq_metadata.get('section'),
                "metadata": eq_metadata
            },
            "table": {
                "entity_id": tbl_metadata['table_id'],
                "entity_type": "table",
                "page": tbl_metadata.get('page', 0),
                "section": tbl_metadata.get('section'),
                "metadata": tbl_metadata
            },
            "variable_linkage": [
                {
                    "variable_id": linkage.variable_id,
                    "symbol": linkage.symbol,
                    "name": linkage.name,
                    "equation_role": linkage.equation_role.value,
                    "table_column": linkage.table_column,
                    "table_column_index": linkage.table_column_index,
                    "lookup_method": lookup_info.method_name,
                    "lookup_key_column": lookup_info.lookup_key_column,
                    "units": {
                        "equation_units": linkage.units.equation_units if linkage.units else "dimensionless",
                        "table_units": linkage.units.table_units if linkage.units else "dimensionless",
                        "conversion_needed": linkage.units.conversion_needed if linkage.units else False,
                        "conversion_factor": linkage.units.conversion_factor if linkage.units else None
                    }
                }
            ],
            "confidence": {
                "score": confidence.score,
                "method": confidence.method,
                "factors": {
                    "symbol_exact_match": confidence.factors.symbol_exact_match,
                    "dimensional_consistency": confidence.factors.dimensional_consistency,
                    "semantic_tag_overlap": confidence.factors.semantic_tag_overlap,
                    "name_similarity": confidence.factors.name_similarity
                }
            },
            "validation": {
                "overall_status": "pending",
                "checks": []
            },
            "provenance": {
                "detector": "DataDependencyDetector",
                "version": "1.0.0",
                "config_hash": None
            }
        }

        return dependency

    def _validate_dependency(
        self,
        dependency: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        MANDATORY: Validate dependency using RelationshipValidator.

        The Validator checks:
        1. Dimensional consistency (equation units vs table units)
        2. Unit coercion (conversion feasibility)
        3. Regime applicability (equation range vs table data range)

        Args:
            dependency: Dependency dict to validate

        Returns:
            Dependency dict with validation block updated
        """
        try:
            # Prepare relationship format for validator
            relationship = {
                'type': 'data_dependency',
                'variable': dependency['variable_linkage'][0]['variable_id'],
                'equation': {
                    'equation_id': dependency['source'],
                    'variables': {
                        dependency['variable_linkage'][0]['variable_id']: {
                            'units': dependency['variable_linkage'][0]['units']['equation_units']
                        }
                    }
                },
                'table': {
                    'table_id': dependency['target'],
                    'columns': {
                        dependency['variable_linkage'][0]['variable_id']: {
                            'units': dependency['variable_linkage'][0]['units']['table_units']
                        }
                    }
                }
            }

            # Call validator
            validation_result = self.validator.validate_relationship(relationship)

            # Update validation block
            dependency['validation'] = {
                'overall_status': validation_result.overall_status,
                'checks': [
                    {
                        'check_type': check.check_type,
                        'status': check.status,
                        'details': check.details,
                        'message': check.message
                    }
                    for check in validation_result.checks
                ],
                'warnings': validation_result.warnings,
                'issues': validation_result.issues
            }

        except Exception as e:
            # Validation error - mark as failed
            print(f"  ⚠️  Validation error: {e}")
            dependency['validation'] = {
                'overall_status': 'fail',
                'checks': [],
                'warnings': [],
                'issues': [f"Validation error: {str(e)}"]
            }

        return dependency

    def export_to_json(
        self,
        dependencies: List[Dict[str, Any]],
        output_path: Path
    ) -> None:
        """
        Export dependencies to JSON file.

        Args:
            dependencies: List of validated DataDependency dicts
            output_path: Path to output JSON file
        """
        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(dependencies, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Exported {len(dependencies)} dependencies to {output_path}")

    def get_statistics(
        self,
        dependencies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate statistics for detected dependencies.

        Returns:
            Statistics dictionary
        """
        if not dependencies:
            return {
                'total_dependencies': 0,
                'by_validation_status': {},
                'by_confidence': {},
                'by_lookup_method': {}
            }

        # Count by validation status
        validation_counts = {}
        for dep in dependencies:
            status = dep['validation']['overall_status']
            validation_counts[status] = validation_counts.get(status, 0) + 1

        # Count by confidence range
        confidence_ranges = {
            '0.95+': 0,
            '0.85-0.95': 0,
            '0.75-0.85': 0,
            'below_0.75': 0
        }
        for dep in dependencies:
            score = dep['confidence']['score']
            if score >= 0.95:
                confidence_ranges['0.95+'] += 1
            elif score >= 0.85:
                confidence_ranges['0.85-0.95'] += 1
            elif score >= 0.75:
                confidence_ranges['0.75-0.85'] += 1
            else:
                confidence_ranges['below_0.75'] += 1

        # Count by lookup method
        lookup_counts = {}
        for dep in dependencies:
            for linkage in dep['variable_linkage']:
                method = linkage['lookup_method']
                lookup_counts[method] = lookup_counts.get(method, 0) + 1

        return {
            'total_dependencies': len(dependencies),
            'by_validation_status': validation_counts,
            'by_confidence': confidence_ranges,
            'by_lookup_method': lookup_counts
        }
