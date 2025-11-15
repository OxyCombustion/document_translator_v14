#!/usr/bin/env python3
"""
Phase 14 Migration Validation Script

Validates that all metadata components have been migrated to metadata_v14_P13.

Expected:
- 2 bibliography components
- 2 metadata components
- 1 assessment component
- 1 TRL component
- 3 Zotero components (including __init__.py.original)
- Total: 9 components
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


def validate_phase14() -> Dict[str, int]:
    """Validate Phase 14 migration."""
    base_path = Path('metadata_v14_P13/src')

    if not base_path.exists():
        print(f"❌ ERROR: {base_path} does not exist!")
        return {}

    # Category paths
    categories = {
        'bibliography': base_path / 'bibliography',
        'metadata': base_path / 'metadata',
        'assessment': base_path / 'assessment',
        'trl': base_path / 'trl',
        'zotero': base_path / 'zotero',
    }

    # Expected counts per category
    expected = {
        'bibliography': 2,
        'metadata': 2,
        'assessment': 1,
        'trl': 1,
        'zotero': 3,  # includes __init__.py.original
    }

    # Validation results
    results = {}
    all_passed = True

    print("=" * 80)
    print("PHASE 14 MIGRATION VALIDATION - Metadata & Bibliographic Integration")
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
        print("🎉 Phase 14 migration validation: PASSED")
        print()
        print("Summary:")
        print("  - 2 bibliography agents (extraction + citation graph)")
        print("  - 2 metadata agents (basic + enhanced)")
        print("  - 1 assessment agent (impact assessment)")
        print("  - 1 TRL agent (library manager)")
        print("  - 3 Zotero components (integration + working copy + original init)")
        print("  - Total: 9 components")
        print()
        print("Progress: 155/339 components migrated (45.7%)")
        print("🎯 45% MILESTONE ACHIEVED!")
        return results
    else:
        print("❌ Phase 14 migration validation: FAILED")
        print("   Please review errors above and fix missing components.")
        return results


if __name__ == '__main__':
    validate_phase14()
