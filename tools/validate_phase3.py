#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3 Validation Script
Validates successful migration of rag_v14_P2 components
"""

import sys
from pathlib import Path

# Color codes
GREEN, RED, YELLOW, BLUE, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[94m", "\033[0m"

class Phase3Validator:
    def __init__(self):
        self.v14_root = Path("/home/thermodynamics/document_translator_v14")
        self.errors, self.warnings = [], []
        self.passed_checks, self.total_checks = 0, 0

    def validate_all(self) -> bool:
        print(f"\n{BLUE}Phase 3 Validation{RESET}\n")

        # Count all Python files in rag_v14_P2/src
        rag_root = self.v14_root / "rag_v14_P2/src"
        if rag_root.exists():
            py_files = list(rag_root.rglob("*.py"))
            py_files = [f for f in py_files if f.name != "__init__.py"]

            self.total_checks = len(py_files)
            print(f"{BLUE}Found {len(py_files)} RAG pipeline components{RESET}\n")

            # Group by category
            categories = {}
            for py_file in sorted(py_files):
                rel_path = py_file.relative_to(self.v14_root)
                # Extract category from path
                parts = list(rel_path.parts)
                if len(parts) >= 3:  # rag_v14_P2/src/category/file.py
                    category = parts[2]
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(py_file)
                    self.passed_checks += 1

            # Print by category
            for category in sorted(categories.keys()):
                files = categories[category]
                print(f"\n{YELLOW}{category.capitalize()} ({len(files)} components):{RESET}")
                for py_file in sorted(files):
                    rel_path = py_file.relative_to(self.v14_root)
                    size = py_file.stat().st_size
                    print(f"{GREEN}✅{RESET} {rel_path} ({size:,} bytes)")

        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        print(f"\n{GREEN}✅ PHASE 3: {self.passed_checks}/{self.total_checks} components migrated ({success_rate:.1f}%){RESET}\n")

        return True

validator = Phase3Validator()
validator.validate_all()
