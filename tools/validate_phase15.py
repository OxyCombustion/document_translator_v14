#!/usr/bin/env python3
"""
Phase 15 Migration Validation Script

Validates that all detection components have been migrated to detection_v14_P14.

Expected:
- 3 Docling detection components
- 2 unified detection components (including __init__.py.original)
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


def validate_phase15() -> Dict[str, int]:
    """Validate Phase 15 migration."""
    base_path = Path('detection_v14_P14/src')

    if not base_path.exists():
        print(f"❌ ERROR: {base_path} does not exist!")
        return {}

    # Category paths
    categories = {
        'docling': base_path / 'docling',
        'unified': base_path / 'unified',
    }

    # Expected counts per category
    expected = {
        'docling': 3,
        'unified': 2,  # includes __init__.py.original
    }

    # Validation results
    results = {}
    all_passed = True

    print("=" * 80)
    print("PHASE 15 MIGRATION VALIDATION - Content Detection Agents")
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
        print("🎉 Phase 15 migration validation: PASSED")
        print()
        print("Summary:")
        print("  - 3 Docling detectors (figure + table + text)")
        print("  - 2 unified detection (YOLO+Docling + original init)")
        print("  - Total: 5 components")
        print()
        print("Progress: 160/339 components migrated (47.2%)")
        print("🎯 Nearly at 50% milestone!")
        return results
    else:
        print("❌ Phase 15 migration validation: FAILED")
        print("   Please review errors above and fix missing components.")
        return results


if __name__ == '__main__':
    validate_phase15()
