#!/usr/bin/env python3
"""Validate Phase 21 migration: Final Specialized Utilities."""

from pathlib import Path

def count_python_files(directory: Path) -> int:
    """Count migrated Python files (*.py except __init__.py, plus __init__.py.original* if present)."""
    files = [f for f in directory.glob('*.py') if f.name != '__init__.py']
    # Count __init__.py.original* files
    files.extend(directory.glob('__init__.py.original*'))
    return len(files)

def main():
    print("\n" + "="*70)
    print("Phase 21 Migration Validation: Final Specialized Utilities")
    print("="*70 + "\n")

    base = Path("specialized_utilities_v14_P20/src")

    categories = {
        'context': ('context/', 1),           # agent_context_lifecycle_manager.py
        'session': ('session/', 2),           # session_preservation_agent.py + __init__.py.original_session
        'figure': ('figure/', 1),             # __init__.py.original_extractor
        'gpu': ('gpu/', 1),                   # gpu_compatibility_monitor.py
        'visualization': ('visualization/', 1), # grid_overlay_agent.py
        'detection': ('detection/', 1),       # heuristic_formula_probe.py
        'mathematica': ('mathematica/', 1),   # document_structure_analyzer.py
        'image': ('image/', 1),               # raster_tightener.py
        'text': ('text/', 2),                 # basic_agent.py + __init__.py.original_text
        'refinement': ('refinement/', 1),     # table_figure_refiner.py
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
            if name == 'context':
                print(f"    - agent_context_lifecycle_manager.py")
            elif name == 'session':
                print(f"    - session_preservation_agent.py")
                print(f"    - __init__.py.original_session")
            elif name == 'figure':
                print(f"    - __init__.py.original_extractor")
            elif name == 'gpu':
                print(f"    - gpu_compatibility_monitor.py")
            elif name == 'visualization':
                print(f"    - grid_overlay_agent.py")
            elif name == 'detection':
                print(f"    - heuristic_formula_probe.py")
            elif name == 'mathematica':
                print(f"    - document_structure_analyzer.py")
            elif name == 'image':
                print(f"    - raster_tightener.py")
            elif name == 'text':
                print(f"    - basic_agent.py")
                print(f"    - __init__.py.original_text")
            elif name == 'refinement':
                print(f"    - table_figure_refiner.py")

    print("\n" + "-"*70)
    if all_pass:
        print(f"\033[92m✓ PHASE 21 COMPLETE: {total_found}/{total_expected} components migrated\033[0m")
        print(f"\033[92m✓ V13→V14 MIGRATION COMPLETE!\033[0m")
    else:
        print(f"\033[91m✗ PHASE 21 INCOMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    print("-"*70 + "\n")

    return 0 if all_pass else 1

if __name__ == '__main__':
    exit(main())
