#!/usr/bin/env python3
"""Validate Phase 18 migration: Docling Agents."""

from pathlib import Path

def count_python_files(directory: Path) -> int:
    """Count migrated Python files (*.py except __init__.py, plus __init__.py.original if present)."""
    files = [f for f in directory.glob('*.py') if f.name != '__init__.py']
    if (directory / '__init__.py.original').exists():
        files.append(directory / '__init__.py.original')
    return len(files)

def main():
    print("\n" + "="*70)
    print("Phase 18 Migration Validation: Docling Agents")
    print("="*70 + "\n")

    base = Path("docling_agents_v14_P17/src")

    categories = {
        'basic': ('basic/', 2),           # agent.py + __init__.py.original
        'primary': ('primary/', 2),       # docling_first_agent.py + __init__.py.original
        'roi': ('roi/', 1),               # agent.py
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
            print(f"  Expected files:")
            if name == 'basic':
                print(f"    - agent.py")
                print(f"    - __init__.py.original")
            elif name == 'primary':
                print(f"    - docling_first_agent.py")
                print(f"    - __init__.py.original")
            elif name == 'roi':
                print(f"    - agent.py")

    print("\n" + "-"*70)
    if all_pass:
        print(f"\033[92m✓ PHASE 18 COMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    else:
        print(f"\033[91m✗ PHASE 18 INCOMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    print("-"*70 + "\n")

    return 0 if all_pass else 1

if __name__ == '__main__':
    exit(main())
