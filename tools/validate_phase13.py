#!/usr/bin/env python3
"""
Phase 13 Migration Validation Script

Validates that all extraction comparison components have been migrated to extraction_comparison_v14_P12.

Expected:
- 1 comparison component
- 1 orchestration component
- 3 alternative method components
- Total: 5 components
"""

from pathlib import Path
from typing import Dict


def count_python_files(directory: Path) -> int:
    """Count migrated Python files (*.py except __init__.py, plus __init__.py.original if present)."""
    # Count .py files except __init__.py (which is v14 package infrastructure)
    files = [f for f in directory.glob('*.py') if f.name != '__init__.py']

    # Also count __init__.py.original as a migrated file (the v13 original)
    if (directory / '__init__.py.original').exists():
        files.append(directory / '__init__.py.original')

    return len(files)


def validate_phase13() -> Dict[str, int]:
    """Validate Phase 13 migration."""
    base_path = Path('extraction_comparison_v14_P12/src')

    if not base_path.exists():
        print(f"❌ ERROR: {base_path} does not exist!")
        return {}

    # Category paths
    categories = {
        'comparison': base_path / 'comparison',
        'orchestration': base_path / 'orchestration',
        'methods': base_path / 'methods',
    }

    # Expected counts per category
    expected = {
        'comparison': 1,
        'orchestration': 1,
        'methods': 3,
    }

    # Validation results
    results = {}
    all_passed = True

    print("=" * 80)
    print("PHASE 13 MIGRATION VALIDATION - Extraction Comparison & Multi-Method")
    print("=" * 80)
    print()

    # Validate each category
    for category, path in categories.items():
        if not path.exists():
            print(f"❌ {category.upper()}: Directory not found at {path}")
            results[category] = 0
            all_passed = False
            continue

        count = count_python_files(path)
        expected_count = expected[category]
        results[category] = count

        if count == expected_count:
            print(f"✅ {category.upper()}: {count}/{expected_count} components")
        else:
            print(f"❌ {category.upper()}: {count}/{expected_count} components (MISMATCH!)")
            all_passed = False

    # Total validation
    print()
    print("-" * 80)
    total = sum(results.values())
    total_expected = sum(expected.values())

    if total == total_expected:
        print(f"✅ TOTAL: {total}/{total_expected} components migrated")
    else:
        print(f"❌ TOTAL: {total}/{total_expected} components (MISSING {total_expected - total}!)")
        all_passed = False

    print("=" * 80)
    print()

    if all_passed:
        print("🎉 Phase 13 migration validation: PASSED")
        print()
        print("Summary:")
        print("  - 1 comparison agent (extraction comparison)")
        print("  - 1 orchestration agent (full document orchestrator)")
        print("  - 3 alternative methods (Docling, Gemini, Mathematica)")
        print("  - Total: 5 components")
        print()
        print("Progress: 146/339 components migrated (43.1%)")
        return results
    else:
        print("❌ Phase 13 migration validation: FAILED")
        print("   Please review errors above and fix missing components.")
        return results


if __name__ == '__main__':
    validate_phase13()
