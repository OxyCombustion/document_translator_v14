#!/usr/bin/env python3
"""Validate Phase 20 migration: Analysis, Validation & Documentation."""

from pathlib import Path

def count_python_files(directory: Path) -> int:
    """Count migrated Python files (*.py except __init__.py, plus __init__.py.original* if present)."""
    files = [f for f in directory.glob('*.py') if f.name != '__init__.py']
    # Count __init__.py.original* files
    files.extend(directory.glob('__init__.py.original*'))
    return len(files)

def main():
    print("\n" + "="*70)
    print("Phase 20 Migration Validation: Analysis, Validation & Documentation")
    print("="*70 + "\n")

    base = Path("analysis_validation_v14_P19/src")

    categories = {
        'equation_analysis': ('equation_analysis/', 4),   # 4 analysis agents
        'validation': ('validation/', 5),                 # 4 agents + 1 original init
        'documentation': ('documentation/', 5),           # 4 agents + 1 original init
    }

    total_expected = sum(count for _, count in categories.values())
    total_found = 0
    all_pass = True

    for name, (path, expected) in categories.items():
        category_path = base / path
        actual = count_python_files(category_path)
        total_found += actual
        status = "✓" if actual == expected else "✗"
        color = "\033[92m" if actual == expected else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{status}{reset} {name:20s} {actual:2d}/{expected:2d} files")

        if actual != expected:
            all_pass = False
            print(f"  Expected files in {path}:")
            if name == 'equation_analysis':
                print(f"    - computational_code_generator_agent.py")
                print(f"    - equation_classifier_agent.py")
                print(f"    - equation_zone_refiner.py")
                print(f"    - relational_documentation_agent.py")
            elif name == 'validation':
                print(f"    - completeness_validation_agent.py")
                print(f"    - document_reference_inventory_agent.py")
                print(f"    - structure_based_validator.py")
                print(f"    - validation_agent.py")
                print(f"    - __init__.py.original_validation_agent")
            elif name == 'documentation':
                print(f"    - context_aware_documentation_agent.py")
                print(f"    - enhanced_documentation_agent.py")
                print(f"    - real_time_monitor.py")
                print(f"    - test_tracking.py")
                print(f"    - __init__.py.original_documentation")

    print("\n" + "-"*70)
    if all_pass:
        print(f"\033[92m✓ PHASE 20 COMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    else:
        print(f"\033[91m✗ PHASE 20 INCOMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    print("-"*70 + "\n")

    return 0 if all_pass else 1

if __name__ == '__main__':
    exit(main())
