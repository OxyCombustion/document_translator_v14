#!/usr/bin/env python3
"""Validate Phase 19 migration: Extraction Utilities."""

from pathlib import Path

def count_python_files(directory: Path) -> int:
    """Count migrated Python files (*.py except __init__.py, plus __init__.py.original* if present)."""
    files = [f for f in directory.glob('*.py') if f.name != '__init__.py']
    # Count __init__.py.original* files
    files.extend(directory.glob('__init__.py.original*'))
    return len(files)

def main():
    print("\n" + "="*70)
    print("Phase 19 Migration Validation: Extraction Utilities")
    print("="*70 + "\n")

    base = Path("extraction_utilities_v14_P18/src")

    categories = {
        'equations': ('equations/', 5),   # 3 agents + 2 original inits
        'figures': ('figures/', 2),       # 2 files
        'detection': ('detection/', 2),   # 2 agents
        'tables': ('tables/', 4),         # 3 agents + 1 original init
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
            if name == 'equations':
                print(f"    - analyze_extracted_text.py")
                print(f"    - equation_number_ocr_agent.py")
                print(f"    - equation_refinement_agent.py")
                print(f"    - __init__.py.original_extractor")
                print(f"    - __init__.py.original_refinement")
            elif name == 'figures':
                print(f"    - data_structures.py")
                print(f"    - figure_detection_agent.py")
            elif name == 'detection':
                print(f"    - formula_detector_agent.py")
                print(f"    - frame_box_detector.py")
            elif name == 'tables':
                print(f"    - table_layout_agent.py")
                print(f"    - enhanced_detection_criteria.py")
                print(f"    - validation_filtered_extractor.py")
                print(f"    - __init__.py.original_extractor")

    print("\n" + "-"*70)
    if all_pass:
        print(f"\033[92m✓ PHASE 19 COMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    else:
        print(f"\033[91m✗ PHASE 19 INCOMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    print("-"*70 + "\n")

    return 0 if all_pass else 1

if __name__ == '__main__':
    exit(main())
