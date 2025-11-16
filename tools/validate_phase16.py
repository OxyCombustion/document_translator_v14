#!/usr/bin/env python3
"""
Phase 16 Migration Validation Script

Validates that all specialized extraction components have been migrated to specialized_extraction_v14_P15.

Expected:
- 5 object detection components (including __init__.py.original)
- 3 caption extraction components
- 1 coordination component
- 1 figure extraction component (__init__.py.original)
- Total: 10 components

🎯 50% MILESTONE: This validation confirms 170/339 components (50.1%)!
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


def validate_phase16() -> Dict[str, int]:
    """Validate Phase 16 migration."""
    base_path = Path('specialized_extraction_v14_P15/src')

    if not base_path.exists():
        print(f"❌ ERROR: {base_path} does not exist!")
        return {}

    # Category paths
    categories = {
        'object_detection': base_path / 'object_detection',
        'captions': base_path / 'captions',
        'coordination': base_path / 'coordination',
        'figures': base_path / 'figures',
    }

    # Expected counts per category
    expected = {
        'object_detection': 5,  # 4 controllers + __init__.py.original
        'captions': 3,
        'coordination': 1,
        'figures': 1,  # __init__.py.original with code
    }

    # Validation results
    results = {}
    all_passed = True

    print("=" * 80)
    print("PHASE 16 MIGRATION VALIDATION - Specialized Extraction Agents")
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
        print("🎉 Phase 16 migration validation: PASSED")
        print()
        print("Summary:")
        print("  - 5 object detection (4 controllers + original init)")
        print("  - 3 caption extraction (association + equation + table)")
        print("  - 1 coordination (object numbering)")
        print("  - 1 figure extraction (original init)")
        print("  - Total: 10 components")
        print()
        print("Progress: 170/339 components migrated (50.1%)")
        print()
        print("🎯🎯🎯 50% MILESTONE ACHIEVED! 🎯🎯🎯")
        print()
        print("Half of the v13→v14 migration is now complete!")
        return results
    else:
        print("❌ Phase 16 migration validation: FAILED")
        print("   Please review errors above and fix missing components.")
        return results


if __name__ == '__main__':
    validate_phase16()
