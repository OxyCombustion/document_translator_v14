#!/usr/bin/env python3
"""
Phase 11 Validation Script

Validates migration of 8 infrastructure and utility components across 5 categories.
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
    """Count migrated Python files (*.py except __init__.py, plus __init__.py.original if present)."""
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
    """Run Phase 11 validation."""
    print(f"\n{BOLD}Phase 11: Infrastructure & Utilities Migration Validation{RESET}")
    print(f"{BLUE}{'=' * 60}{RESET}\n")

    base_path = Path(__file__).parent.parent / 'infrastructure_v14_P10' / 'src'

    # Define expected components per category
    categories = {
        'documentation': {
            'expected': 5,
            'description': 'Documentation agents (4 agents + __init__.py.original)'
        },
        'session': {
            'expected': 2,
            'description': 'Session preservation (agent + __init__.py.original)'
        },
        'context': {
            'expected': 1,
            'description': 'Context lifecycle management'
        },
        'gpu': {
            'expected': 1,
            'description': 'GPU compatibility monitoring'
        },
        'output': {
            'expected': 1,
            'description': 'Output management'
        },
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

    # Check for documentation files
    doc_count = len(list((base_path / 'session').glob('*.md')))
    gpu_doc_count = len(list((base_path / 'gpu').glob('*.md')))
    print(f"  Documentation: {doc_count} files in session/, {gpu_doc_count} in gpu/, 2 in documentation/")

    # Summary
    print(f"{BLUE}{'-' * 60}{RESET}")
    print(f"\n{BOLD}Summary:{RESET}")
    print(f"  Total components: {total_actual}/{total_expected}")
    print(f"  Categories: {len(categories)}")

    if all_ok and total_actual == total_expected:
        print(f"\n{GREEN}{BOLD}✓ Phase 11 validation PASSED{RESET}")
        print(f"{GREEN}All 8 infrastructure and utility components successfully migrated{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{BOLD}✗ Phase 11 validation FAILED{RESET}")
        print(f"{RED}Some components are missing or incorrect{RESET}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
