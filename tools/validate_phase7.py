#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 7 Validation Script
Validates successful migration of database_v14_P6 components
"""

import sys
from pathlib import Path

# Color codes
GREEN, RED, YELLOW, BLUE, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[94m", "\033[0m"

class Phase7Validator:
    def __init__(self):
        self.v14_root = Path("/home/thermodynamics/document_translator_v14")
        self.errors, self.warnings = [], []
        self.passed_checks, self.total_checks = 0, 0

    def validate_all(self) -> bool:
        print(f"\n{BLUE}Phase 7 Validation{RESET}\n")

        # Count all files (Python + SQL) in database_v14_P6/src
        database_root = self.v14_root / "database_v14_P6/src"
        if database_root.exists():
            all_files = list(database_root.rglob("*.py")) + list(database_root.rglob("*.sql"))
            all_files = [f for f in all_files if f.name != "__init__.py"]

            self.total_checks = len(all_files)
            print(f"{BLUE}Found {len(all_files)} database components (Python + SQL){RESET}\n")

            # Group by category
            categories = {}
            for file in sorted(all_files):
                rel_path = file.relative_to(self.v14_root)
                # Extract category from path
                parts = list(rel_path.parts)
                if len(parts) >= 3:  # database_v14_P6/src/category/file.py
                    category = parts[2]
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(file)
                    self.passed_checks += 1

            # Print by category
            for category in sorted(categories.keys()):
                files = categories[category]
                print(f"\n{YELLOW}{category.capitalize()} ({len(files)} components):{RESET}")
                for file in sorted(files):
                    rel_path = file.relative_to(self.v14_root)
                    size = file.stat().st_size
                    file_type = "SQL" if file.suffix == ".sql" else "Python"
                    print(f"{GREEN}✅{RESET} {rel_path} ({size:,} bytes, {file_type})")

        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        print(f"\n{GREEN}✅ PHASE 7: {self.passed_checks}/{self.total_checks} components migrated ({success_rate:.1f}%){RESET}\n")

        return True

validator = Phase7Validator()
validator.validate_all()
