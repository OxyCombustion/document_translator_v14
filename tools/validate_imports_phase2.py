#!/usr/bin/env python3
"""
Validate import paths after Phase 2 package reorganization.

This script tests that all imports are working correctly in the new vertical
pipeline architecture by attempting to import key modules from each package.
"""

import sys
import importlib
from pathlib import Path
from typing import List, Dict, Tuple
import traceback

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Package validation tests - key modules to import from each package
VALIDATION_TESTS = {
    # Extraction pipeline (7 packages)
    'pipelines.extraction.packages.extraction_v14_P1': [
        'pipelines.extraction.packages.extraction_v14_P1',
    ],
    'pipelines.extraction.packages.detection_v14_P14': [
        'pipelines.extraction.packages.detection_v14_P14.src.yolo.unified_detection_module',
        'pipelines.extraction.packages.detection_v14_P14.src.docling.docling_table_detector',
    ],
    'pipelines.extraction.packages.docling_agents_v14_P17': [
        'pipelines.extraction.packages.docling_agents_v14_P17.src.primary.docling_first_agent',
    ],
    'pipelines.extraction.packages.docling_agents_v14_P8': [
        'pipelines.extraction.packages.docling_agents_v14_P8',
    ],
    'pipelines.extraction.packages.specialized_extraction_v14_P15': [
        'pipelines.extraction.packages.specialized_extraction_v14_P15.src.coordination.object_numbering_coordinator',
    ],
    'pipelines.extraction.packages.extraction_comparison_v14_P12': [
        'pipelines.extraction.packages.extraction_comparison_v14_P12',
    ],
    'pipelines.extraction.packages.extraction_utilities_v14_P18': [
        'pipelines.extraction.packages.extraction_utilities_v14_P18',
    ],

    # RAG ingestion pipeline (4 packages)
    'pipelines.rag_ingestion.packages.rag_v14_P2': [
        'pipelines.rag_ingestion.packages.rag_v14_P2.src.orchestrators.unified_pipeline_orchestrator',
    ],
    'pipelines.rag_ingestion.packages.rag_extraction_v14_P16': [
        'pipelines.rag_ingestion.packages.rag_extraction_v14_P16.src.equations.equation_extraction_agent',
    ],
    'pipelines.rag_ingestion.packages.semantic_processing_v14_P4': [
        'pipelines.rag_ingestion.packages.semantic_processing_v14_P4',
    ],
    'pipelines.rag_ingestion.packages.analysis_validation_v14_P19': [
        'pipelines.rag_ingestion.packages.analysis_validation_v14_P19.src.validation.completeness_validation_agent',
    ],

    # Data management pipeline (4 packages)
    'pipelines.data_management.packages.curation_v14_P3': [
        'pipelines.data_management.packages.curation_v14_P3',
    ],
    'pipelines.data_management.packages.database_v14_P6': [
        'pipelines.data_management.packages.database_v14_P6.src.registry.document_registry',
    ],
    'pipelines.data_management.packages.metadata_v14_P13': [
        'pipelines.data_management.packages.metadata_v14_P13.src.zotero.zotero_working_copy_manager',
    ],
    'pipelines.data_management.packages.relationship_detection_v14_P5': [
        'pipelines.data_management.packages.relationship_detection_v14_P5',
    ],

    # Shared foundation (6 packages)
    'pipelines.shared.packages.common': [
        'pipelines.shared.packages.common.src.base.base_extraction_agent',
        'pipelines.shared.packages.common.src.base.base_agent',
    ],
    'pipelines.shared.packages.infrastructure_v14_P10': [
        'pipelines.shared.packages.infrastructure_v14_P10',
    ],
    'pipelines.shared.packages.cli_v14_P7': [
        'pipelines.shared.packages.cli_v14_P7',
    ],
    'pipelines.shared.packages.specialized_utilities_v14_P20': [
        'pipelines.shared.packages.specialized_utilities_v14_P20',
    ],
    'pipelines.shared.packages.analysis_tools_v14_P9': [
        'pipelines.shared.packages.analysis_tools_v14_P9',
    ],
    'pipelines.shared.packages.processing_utilities_v14_P11': [
        'pipelines.shared.packages.processing_utilities_v14_P11',
    ],
}

def test_import(module_name: str) -> Tuple[bool, str]:
    """
    Test importing a module.

    Returns:
        Tuple of (success, error_message)
    """
    try:
        importlib.import_module(module_name)
        return (True, "")
    except ModuleNotFoundError as e:
        return (False, f"Module not found: {e}")
    except ImportError as e:
        return (False, f"Import error: {e}")
    except Exception as e:
        return (False, f"Unexpected error: {e}\n{traceback.format_exc()}")

def validate_all_imports() -> Dict[str, List[Tuple[str, bool, str]]]:
    """
    Validate all package imports.

    Returns:
        Dictionary mapping package names to lists of (module, success, error) tuples
    """
    results = {}

    for package, modules in VALIDATION_TESTS.items():
        package_results = []
        for module in modules:
            success, error = test_import(module)
            package_results.append((module, success, error))
        results[package] = package_results

    return results

def print_results(results: Dict[str, List[Tuple[str, bool, str]]]):
    """Print validation results with statistics."""
    print("=" * 80)
    print("Phase 2 Import Validation Results")
    print("=" * 80)
    print()

    total_tests = 0
    total_passed = 0
    total_failed = 0
    failed_packages = []

    # Group by pipeline
    pipelines = {
        'Extraction Pipeline': [],
        'RAG Ingestion Pipeline': [],
        'Data Management Pipeline': [],
        'Shared Foundation': []
    }

    for package, package_results in results.items():
        if 'extraction' in package and 'rag_' not in package:
            pipelines['Extraction Pipeline'].append((package, package_results))
        elif 'rag_ingestion' in package:
            pipelines['RAG Ingestion Pipeline'].append((package, package_results))
        elif 'data_management' in package:
            pipelines['Data Management Pipeline'].append((package, package_results))
        elif 'shared' in package:
            pipelines['Shared Foundation'].append((package, package_results))

    for pipeline_name, pipeline_packages in pipelines.items():
        if not pipeline_packages:
            continue

        print(f"\n{'─' * 80}")
        print(f"{pipeline_name}")
        print(f"{'─' * 80}")

        for package, package_results in pipeline_packages:
            package_name = package.split('.')[-1]
            passed = sum(1 for _, success, _ in package_results if success)
            failed = len(package_results) - passed
            total_tests += len(package_results)
            total_passed += passed
            total_failed += failed

            status = "✅ PASS" if failed == 0 else "❌ FAIL"
            print(f"\n{status} {package_name} ({passed}/{len(package_results)} tests)")

            if failed > 0:
                failed_packages.append(package_name)
                for module, success, error in package_results:
                    if not success:
                        print(f"  ❌ {module}")
                        print(f"     Error: {error}")

    print(f"\n{'=' * 80}")
    print("Summary")
    print(f"{'=' * 80}")
    print(f"Total Packages Tested: {len(results)}")
    print(f"Total Import Tests: {total_tests}")
    print(f"Passed: {total_passed} ({100 * total_passed / total_tests:.1f}%)")
    print(f"Failed: {total_failed} ({100 * total_failed / total_tests:.1f}%)")

    if failed_packages:
        print(f"\nPackages with Failed Imports: {', '.join(failed_packages)}")
    else:
        print("\n✅ All imports validated successfully!")

    print(f"{'=' * 80}")

    return total_failed == 0

def main():
    """Main execution function."""
    print("Starting Phase 2 import validation...")
    print(f"Project root: {project_root}")
    print()

    results = validate_all_imports()
    success = print_results(results)

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
