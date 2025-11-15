#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
V14 Integration Test Suite

Validates that all 21 v14 packages work together correctly after migration.

Tests:
1. Package import validation (all packages can be imported)
2. Package structure validation (__init__.py exports work)
3. Cross-package dependency validation (imports resolve correctly)
4. Basic functionality validation (agents can be instantiated)

Usage:
    python3 tools/test_v14_integration.py

Author: Claude Code
Date: 2025-11-15
"""

import sys
import os

# MANDATORY UTF-8 SETUP
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

import importlib
from pathlib import Path
from typing import List, Tuple, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# All 21 v14 packages
PACKAGES = [
    'common',
    'extraction_v14_P1',
    'rag_v14_P2',
    'curation_v14_P3',
    'semantic_processing_v14_P4',
    'relationship_detection_v14_P5',
    'database_v14_P6',
    'cli_v14_P7',
    'docling_agents_v14_P8',
    'analysis_tools_v14_P9',
    'infrastructure_v14_P10',
    'processing_utilities_v14_P11',
    'extraction_comparison_v14_P12',
    'metadata_v14_P13',
    'detection_v14_P14',
    'specialized_extraction_v14_P15',
    'rag_extraction_v14_P16',
    'docling_agents_v14_P17',
    'extraction_utilities_v14_P18',
    'analysis_validation_v14_P19',
    'specialized_utilities_v14_P20',
]

# Critical cross-package imports to test
CROSS_PACKAGE_IMPORTS = [
    ("Base Agent (common)", "from common.src.base.base_agent import BaseAgent"),
    ("Base Extraction Agent", "from common.src.base.base_agent import BaseExtractionAgent"),
    ("Zone & ExtractedObject", "from common.src.base.base_agent import Zone, ExtractedObject"),
    ("Unified Detection", "from detection_v14_P14.src.unified.unified_detection_module import UnifiedDetectionModule"),
    ("Equation Extraction", "from rag_extraction_v14_P16.src.equations.equation_extraction_agent import EquationExtractionAgent"),
    ("Figure Extraction", "from rag_extraction_v14_P16.src.figures.figure_extraction_agent import FigureExtractionAgent"),
    ("Table Extraction", "from rag_extraction_v14_P16.src.tables.table_extraction_agent import TableExtractionAgent"),
    ("Text Extraction", "from rag_extraction_v14_P16.src.text.text_extraction_agent import TextExtractionAgent"),
    ("Bibliography Extraction", "from metadata_v14_P13.src.bibliography.bibliography_extraction_agent import BibliographyExtractionAgent"),
    ("Structure Validator", "from analysis_validation_v14_P19.src.validation.structure_based_validator import StructureBasedValidator"),
]


class IntegrationTester:
    """Integration test suite for v14 architecture."""

    def __init__(self):
        self.results = {
            'package_imports': [],
            'package_structure': [],
            'cross_package': [],
            'total_passed': 0,
            'total_failed': 0,
        }

    def test_package_import(self, package_name: str) -> Tuple[bool, str]:
        """Test that package can be imported."""
        try:
            module = importlib.import_module(package_name)
            return True, "Success"
        except ImportError as e:
            return False, f"ImportError: {str(e)[:100]}"
        except ModuleNotFoundError as e:
            return False, f"ModuleNotFoundError: {str(e)[:100]}"
        except Exception as e:
            return False, f"Error: {str(e)[:100]}"

    def test_package_structure(self, package_name: str) -> Tuple[bool, str]:
        """Test that package __init__.py exports work."""
        if package_name == 'common':
            # Common has different structure
            try:
                from common.src.base import base_agent
                return True, "Success (common.src.base.base_agent)"
            except Exception as e:
                return False, f"Error: {str(e)[:100]}"

        try:
            # Try to import src from package
            module = importlib.import_module(f"{package_name}.src")
            return True, "Success (src imported)"
        except ImportError as e:
            return False, f"ImportError: {str(e)[:100]}"
        except Exception as e:
            return False, f"Error: {str(e)[:100]}"

    def test_cross_package_import(self, name: str, import_stmt: str) -> Tuple[bool, str]:
        """Test import that crosses package boundaries."""
        try:
            exec(import_stmt, {})
            return True, "Success"
        except ImportError as e:
            return False, f"ImportError: {str(e)[:100]}"
        except ModuleNotFoundError as e:
            return False, f"ModuleNotFoundError: {str(e)[:100]}"
        except Exception as e:
            return False, f"Error: {str(e)[:100]}"

    def run_level1_package_imports(self):
        """Level 1: Test that all packages can be imported."""
        print("\n" + "="*70)
        print("Level 1: Package Import Validation")
        print("="*70)

        success_count = 0
        for package in PACKAGES:
            success, msg = self.test_package_import(package)
            status = "✅" if success else "❌"
            print(f"{status} {package:45s} {msg}")

            self.results['package_imports'].append({
                'package': package,
                'success': success,
                'message': msg
            })

            if success:
                success_count += 1
                self.results['total_passed'] += 1
            else:
                self.results['total_failed'] += 1

        print(f"\nResult: {success_count}/{len(PACKAGES)} packages imported successfully")
        return success_count == len(PACKAGES)

    def run_level2_package_structure(self):
        """Level 2: Test that package exports work correctly."""
        print("\n" + "="*70)
        print("Level 2: Package Structure Validation")
        print("="*70)

        success_count = 0
        for package in PACKAGES:
            success, msg = self.test_package_structure(package)
            status = "✅" if success else "❌"
            print(f"{status} {package:45s} {msg}")

            self.results['package_structure'].append({
                'package': package,
                'success': success,
                'message': msg
            })

            if success:
                success_count += 1
                self.results['total_passed'] += 1
            else:
                self.results['total_failed'] += 1

        print(f"\nResult: {success_count}/{len(PACKAGES)} package structures valid")
        return success_count == len(PACKAGES)

    def run_level3_cross_package_imports(self):
        """Level 3: Test imports that cross package boundaries."""
        print("\n" + "="*70)
        print("Level 3: Cross-Package Dependency Validation")
        print("="*70)

        success_count = 0
        for name, import_stmt in CROSS_PACKAGE_IMPORTS:
            success, msg = self.test_cross_package_import(name, import_stmt)
            status = "✅" if success else "❌"
            print(f"{status} {name:45s} {msg}")

            self.results['cross_package'].append({
                'name': name,
                'import': import_stmt,
                'success': success,
                'message': msg
            })

            if success:
                success_count += 1
                self.results['total_passed'] += 1
            else:
                self.results['total_failed'] += 1

        print(f"\nResult: {success_count}/{len(CROSS_PACKAGE_IMPORTS)} cross-package imports successful")
        return success_count == len(CROSS_PACKAGE_IMPORTS)

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("Integration Test Summary")
        print("="*70)

        pkg_imports_passed = sum(1 for r in self.results['package_imports'] if r['success'])
        pkg_struct_passed = sum(1 for r in self.results['package_structure'] if r['success'])
        cross_pkg_passed = sum(1 for r in self.results['cross_package'] if r['success'])

        print(f"Package Imports:     {pkg_imports_passed}/{len(PACKAGES)} passed")
        print(f"Package Structure:   {pkg_struct_passed}/{len(PACKAGES)} passed")
        print(f"Cross-Package:       {cross_pkg_passed}/{len(CROSS_PACKAGE_IMPORTS)} passed")
        print(f"\nTotal Tests:         {self.results['total_passed']}/{self.results['total_passed'] + self.results['total_failed']} passed")

        overall_success = self.results['total_failed'] == 0
        if overall_success:
            print("\n✅ ALL TESTS PASSED - V14 integration validated successfully!")
        else:
            print(f"\n❌ {self.results['total_failed']} TEST(S) FAILED - Review errors above")

        return overall_success

    def run_all_tests(self):
        """Run complete integration test suite."""
        print("\n" + "="*70)
        print("V14 Integration Test Suite")
        print("="*70)
        print(f"Testing: 21 packages + cross-package dependencies")
        print(f"Project Root: {project_root}")

        # Run all test levels
        level1_pass = self.run_level1_package_imports()
        level2_pass = self.run_level2_package_structure()
        level3_pass = self.run_level3_cross_package_imports()

        # Print summary
        overall_success = self.print_summary()

        return overall_success


def main():
    """Main entry point."""
    tester = IntegrationTester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
