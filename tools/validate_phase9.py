#!/usr/bin/env python3
"""
Phase 9 Validation Script

Validates migration of 5 docling agent components across 3 categories.
"""

import sys
from pathlib import Path
from typing import Dict, List

# Color codes for terminal output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def count_python_files(directory: Path) -> int:
    """Count migrated Python files (*.py except __init__.py, plus __init__.py.original)."""
    # Count .py files except __init__.py (which is v14 package infrastructure)
    files = [f for f in directory.glob('*.py') if f.name != '__init__.py']
    # Also count __init__.py.original as a migrated file (the v13 original)
    if (directory / '__init__.py.original').exists():
        files.append(directory / '__init__.py.original')
    return len(files)


def validate_category(category_path: Path, expected_count: int, category_name: str) -> Dict:
    """Validate a category directory."""
    if not category_path.exists():
        return {
            'status': 'ERROR',
            'expected': expected_count,
            'actual': 0,
            'message': f'Directory does not exist: {category_path}'
        }

    actual_count = count_python_files(category_path)

    if actual_count == expected_count:
        status = 'OK'
        message = f'{GREEN}✓{RESET} All {expected_count} components migrated'
    elif actual_count > expected_count:
        status = 'WARNING'
        message = f'{YELLOW}!{RESET} Found {actual_count} files (expected {expected_count})'
    else:
        status = 'ERROR'
        message = f'{RED}✗{RESET} Only {actual_count}/{expected_count} components migrated'

    return {
        'status': status,
        'expected': expected_count,
        'actual': actual_count,
        'message': message
    }


def main():
    """Run Phase 9 validation."""
    print(f"\n{BOLD}Phase 9: Docling Agents Migration Validation{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

    base_path = Path(__file__).parent.parent / 'docling_agents_v14_P8' / 'src'

    # Define expected components per category
    categories = {
        'core': {'expected': 2, 'description': 'Core Docling agent (agent.py + __init__.py.original)'},
        'first': {'expected': 2, 'description': 'First-pass agent (docling_first_agent.py + __init__.py.original)'},
        'roi': {'expected': 1, 'description': 'Region of interest agent (agent.py)'},
    }

    total_expected = sum(cat['expected'] for cat in categories.values())
    total_actual = 0
    all_ok = True

    # Validate each category
    for category, info in categories.items():
        category_path = base_path / category
        result = validate_category(category_path, info['expected'], category)

        print(f"{BOLD}{category}/{RESET}")
        print(f"  Description: {info['description']}")
        print(f"  Status: {result['message']}")
        print(f"  Files: {result['actual']}/{result['expected']}")
        print()

        total_actual += result['actual']
        if result['status'] != 'OK':
            all_ok = False

    # Summary
    print(f"{BLUE}{'-' * 60}{RESET}")
    print(f"\n{BOLD}Summary:{RESET}")
    print(f"  Total components: {total_actual}/{total_expected}")
    print(f"  Categories: {len(categories)}")

    # Check for documentation files
    doc_files = list((base_path / 'first').glob('*.md'))
    print(f"  Documentation files: {len(doc_files)} (ARCHITECTURE.md, README.md, REQUIREMENTS.md)")

    if all_ok and total_actual == total_expected:
        print(f"\n{GREEN}{BOLD}✓ Phase 9 validation PASSED{RESET}")
        print(f"{GREEN}All 5 docling agent components successfully migrated{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{BOLD}✗ Phase 9 validation FAILED{RESET}")
        print(f"{RED}Some components are missing or incorrect{RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
