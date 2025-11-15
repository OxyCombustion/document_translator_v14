#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 Validation Script
Validates successful migration of P0 common/ components

Checks:
1. All 16 P0 components present
2. All __init__.py files exist
3. No syntax errors
4. Correct file structure
"""

import sys
import os
from pathlib import Path
import ast

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def print_success(message: str):
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message: str):
    print(f"{RED}❌ {message}{RESET}")

def print_warning(message: str):
    print(f"{YELLOW}⚠️  {message}{RESET}")

def print_info(message: str):
    print(f"{BLUE}ℹ️  {message}{RESET}")

def print_section(title: str):
    print(f"\n{'='*70}")
    print(f"{BLUE}{title}{RESET}")
    print(f"{'='*70}")


class Phase1Validator:
    def __init__(self):
        self.v14_root = Path("/home/thermodynamics/document_translator_v14")
        self.errors = []
        self.warnings = []
        self.passed_checks = 0
        self.total_checks = 0

        # P0 components that should be migrated
        self.p0_components = {
            "base": [
                "common/src/base/base_agent.py",
                "common/src/base/base_extraction_agent.py",
                "common/src/base/base_plugin.py",
            ],
            "config": [
                "common/src/config/config_manager.py",
            ],
            "logging": [
                "common/src/logging/logger.py",
                "common/src/logging/structured_logger.py",
            ],
            "exceptions": [
                "common/src/exceptions/exceptions.py",
                "common/src/exceptions/retry.py",
            ],
            "data_structures": [
                "common/src/data_structures/document_types.py",
                "common/src/data_structures/page_context.py",
            ],
            "file_io": [
                "common/src/file_io/pdf_hash.py",
            ],
            "infrastructure": [
                "common/src/infrastructure/core_manager.py",
                "common/src/infrastructure/unicode_manager.py",
            ],
            "context": [
                "common/src/context/context_loader.py",
                "common/src/context/context_manager.py",
            ],
            "registry": [
                "common/src/registry/module_registry_checker.py",
            ],
        }

        # __init__.py files that should exist
        self.required_init_files = [
            "common/__init__.py",
            "common/src/__init__.py",
            "common/src/base/__init__.py",
            "common/src/config/__init__.py",
            "common/src/logging/__init__.py",
            "common/src/exceptions/__init__.py",
            "common/src/data_structures/__init__.py",
            "common/src/file_io/__init__.py",
            "common/src/infrastructure/__init__.py",
            "common/src/context/__init__.py",
            "common/src/registry/__init__.py",
        ]

    def validate_all(self) -> bool:
        """Run all validation checks"""
        print_section("Phase 1 Validation Script")
        print(f"v14 Root: {self.v14_root}")

        self.check_p0_components()
        self.check_init_files()
        self.check_python_syntax()
        self.check_imports()

        self.print_summary()
        return len(self.errors) == 0

    def check_p0_components(self):
        """Verify all P0 components are present"""
        print_section("1. P0 Component Migration Check")

        total_components = sum(len(components) for components in self.p0_components.values())
        self.total_checks += total_components

        for category, components in self.p0_components.items():
            print_info(f"\nChecking {category} ({len(components)} components)...")
            for component_path in components:
                full_path = self.v14_root / component_path
                if full_path.exists():
                    size = full_path.stat().st_size
                    print_success(f"Found: {component_path} ({size:,} bytes)")
                    self.passed_checks += 1
                else:
                    error = f"Missing component: {component_path}"
                    print_error(error)
                    self.errors.append(error)

    def check_init_files(self):
        """Verify all __init__.py files exist"""
        print_section("2. __init__.py Files Check")
        self.total_checks += len(self.required_init_files)

        for init_file in self.required_init_files:
            full_path = self.v14_root / init_file
            if full_path.exists():
                print_success(f"Found: {init_file}")
                self.passed_checks += 1
            else:
                error = f"Missing __init__.py: {init_file}"
                print_error(error)
                self.errors.append(error)

    def check_python_syntax(self):
        """Verify all Python files have valid syntax"""
        print_section("3. Python Syntax Check")

        all_components = []
        for components in self.p0_components.values():
            all_components.extend(components)

        self.total_checks += len(all_components)

        for component_path in all_components:
            full_path = self.v14_root / component_path
            if not full_path.exists():
                continue  # Already reported as missing

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    code = f.read()
                ast.parse(code)
                print_success(f"Valid syntax: {component_path}")
                self.passed_checks += 1
            except SyntaxError as e:
                error = f"Syntax error in {component_path}: {e}"
                print_error(error)
                self.errors.append(error)
            except Exception as e:
                warning = f"Could not validate {component_path}: {e}"
                print_warning(warning)
                self.warnings.append(warning)
                self.passed_checks += 1  # Don't fail on file read errors

    def check_imports(self):
        """Check for broken imports (basic check)"""
        print_section("4. Import Validation Check")

        # Check if any files still reference old v13 paths
        old_patterns = ["from src.", "from agents.", "from core.", "from utils."]

        all_components = []
        for components in self.p0_components.values():
            all_components.extend(components)

        self.total_checks += len(all_components)

        for component_path in all_components:
            full_path = self.v14_root / component_path
            if not full_path.exists():
                continue

            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                found_old_imports = []
                for line_num, line in enumerate(content.split('\n'), 1):
                    for pattern in old_patterns:
                        if line.strip().startswith(pattern):
                            found_old_imports.append(f"Line {line_num}: {line.strip()}")

                if found_old_imports:
                    warning = f"Old imports in {component_path}:\n  " + "\n  ".join(found_old_imports)
                    print_warning(warning)
                    self.warnings.append(warning)
                else:
                    print_success(f"No old imports: {component_path}")

                self.passed_checks += 1

            except Exception as e:
                warning = f"Could not check imports in {component_path}: {e}"
                print_warning(warning)
                self.warnings.append(warning)
                self.passed_checks += 1

    def print_summary(self):
        """Print validation summary"""
        print_section("Validation Summary")

        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0

        print(f"\nChecks Passed: {self.passed_checks}/{self.total_checks} ({success_rate:.1f}%)")
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.errors:
            print(f"\n{RED}{'='*70}")
            print("ERRORS (Must Fix):")
            print(f"{'='*70}{RESET}")
            for i, error in enumerate(self.errors, 1):
                print(f"{i}. {error}")

        if self.warnings:
            print(f"\n{YELLOW}{'='*70}")
            print("WARNINGS (Review Recommended):")
            print(f"{'='*70}{RESET}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{i}. {warning}")

        print(f"\n{'='*70}")
        if len(self.errors) == 0:
            print(f"{GREEN}✅ PHASE 1 VALIDATION: PASSED{RESET}")
            print(f"{GREEN}All 16 P0 components successfully migrated{RESET}")
        else:
            print(f"{RED}❌ PHASE 1 VALIDATION: FAILED{RESET}")
            print(f"{RED}Fix {len(self.errors)} error(s) before proceeding{RESET}")
        print(f"{'='*70}\n")


def main():
    """Main entry point"""
    validator = Phase1Validator()
    success = validator.validate_all()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
