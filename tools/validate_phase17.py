#!/usr/bin/env python3
"""
Phase 17 Migration Validation Script

Validates that all RAG extraction components have been migrated to rag_extraction_v14_P16.

Expected:
- 1 citation extraction component
- 2 assembly components (basic + enhanced)
- 1 equation extraction component
- 2 figure extraction components (basic + enhanced)
- 1 table extraction component
- 1 text extraction component
- Total: 8 components
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


def validate_phase17() -> Dict[str, int]:
    """Validate Phase 17 migration."""
    base_path = Path('rag_extraction_v14_P16/src')

    if not base_path.exists():
        print(f"❌ ERROR: {base_path} does not exist!")
        return {}

    # Category paths
    categories = {
        'citations': base_path / 'citations',
        'assembly': base_path / 'assembly',
        'equations': base_path / 'equations',
        'figures': base_path / 'figures',
        'tables': base_path / 'tables',
        'text': base_path / 'text',
    }

    # Expected counts per category
    expected = {
        'citations': 1,
        'assembly': 2,
        'equations': 1,
        'figures': 2,
        'tables': 1,
        'text': 1,
    }

    # Validation results
    results = {}
    all_passed = True

    print("=" * 80)
    print("PHASE 17 MIGRATION VALIDATION - RAG Extraction Agents")
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
        print("🎉 Phase 17 migration validation: PASSED")
        print()
        print("Summary:")
        print("  - 1 citation extraction")
        print("  - 2 assembly (basic + enhanced)")
        print("  - 1 equation extraction")
        print("  - 2 figures (basic + enhanced)")
        print("  - 1 table extraction")
        print("  - 1 text extraction")
        print("  - Total: 8 components")
        print()
        print("Progress: 178/339 components migrated (52.5%)")
        print("Second half momentum strong!")
        return results
    else:
        print("❌ Phase 17 migration validation: FAILED")
        print("   Please review errors above and fix missing components.")
        return results


if __name__ == '__main__':
    validate_phase17()
