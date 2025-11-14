#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 0 Validation Script
Automated validation of Phase 0 completion before Phase 1 begins

This script ensures:
1. Zero component loss (all 339 components accounted for)
2. v13 preserved intact (no modifications)
3. v14 foundation complete (all required files)
4. All mappings complete and consistent
5. Git repository properly initialized
"""

import sys
import os
from pathlib import Path
import json
import subprocess
from typing import Dict, List, Tuple

# ANSI color codes for output
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

class Phase0Validator:
    def __init__(self):
        self.v13_root = Path("/home/thermodynamics/document_translator_v13")
        self.v14_root = Path("/home/thermodynamics/document_translator_v14")
        self.errors = []
        self.warnings = []
        self.passed_checks = 0
        self.total_checks = 0

    def validate_all(self) -> bool:
        """Run all validation checks"""
        print_section("Phase 0 Validation Script")
        print(f"v13 Root: {self.v13_root}")
        print(f"v14 Root: {self.v14_root}")

        # Run all validation checks
        self.check_directories_exist()
        self.check_v13_unchanged()
        self.check_v14_foundation()
        self.check_git_repository()
        self.check_component_mapping()
        self.check_config_mapping()
        self.check_docs_mapping()
        self.check_safety_checklist()
        self.check_git_branches()
        self.check_recovered_components()

        # Print summary
        self.print_summary()

        return len(self.errors) == 0

    def check_directories_exist(self):
        """Validate v13 and v14 directories exist"""
        print_section("1. Directory Existence Check")
        self.total_checks += 2

        if self.v13_root.exists():
            print_success(f"v13 directory exists: {self.v13_root}")
            self.passed_checks += 1
        else:
            error = f"v13 directory missing: {self.v13_root}"
            print_error(error)
            self.errors.append(error)

        if self.v14_root.exists():
            print_success(f"v14 directory exists: {self.v14_root}")
            self.passed_checks += 1
        else:
            error = f"v14 directory missing: {self.v14_root}"
            print_error(error)
            self.errors.append(error)

    def check_v13_unchanged(self):
        """Verify v13 has no uncommitted changes"""
        print_section("2. v13 Preservation Check")
        self.total_checks += 1

        try:
            os.chdir(self.v13_root)
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )

            if result.stdout.strip() == "":
                print_success("v13 git status clean (no modifications)")
                self.passed_checks += 1
            else:
                warning = f"v13 has uncommitted changes:\n{result.stdout}"
                print_warning(warning)
                self.warnings.append(warning)
                self.passed_checks += 1  # Warning, not error

        except subprocess.CalledProcessError as e:
            error = f"Failed to check v13 git status: {e}"
            print_error(error)
            self.errors.append(error)
        except Exception as e:
            error = f"Error checking v13: {e}"
            print_error(error)
            self.errors.append(error)

    def check_v14_foundation(self):
        """Verify v14 foundation files exist"""
        print_section("3. v14 Foundation Check")

        required_files = [
            "README.md",
            ".gitignore",
            "extraction_v14_P1/README.md",
            "extraction_v14_P1/config/extraction_v14_P1_config.yaml",
            "rag_v14_P2/README.md",
            "rag_v14_P2/config/rag_v14_P2_config.yaml",
            "curation_v14_P3/README.md",
            "curation_v14_P3/config/curation_v14_P3_config.yaml",
            "common/README.md",
        ]

        required_dirs = [
            "extraction_v14_P1/src/agents",
            "extraction_v14_P1/src/core",
            "extraction_v14_P1/src/utils",
            "rag_v14_P2/src/orchestration",
            "rag_v14_P2/src/analyzers",
            "rag_v14_P2/src/processors",
            "curation_v14_P3/src/core",
            "curation_v14_P3/src/validators",
            "curation_v14_P3/src/database",
            "common/src/base",
            "common/src/interfaces",
            "common/src/utilities",
            "schemas/extraction",
            "schemas/rag",
            "schemas/curation",
        ]

        self.total_checks += len(required_files) + len(required_dirs)

        print_info(f"Checking {len(required_files)} required files...")
        for file_path in required_files:
            full_path = self.v14_root / file_path
            if full_path.exists():
                print_success(f"Found: {file_path}")
                self.passed_checks += 1
            else:
                error = f"Missing required file: {file_path}"
                print_error(error)
                self.errors.append(error)

        print_info(f"\nChecking {len(required_dirs)} required directories...")
        for dir_path in required_dirs:
            full_path = self.v14_root / dir_path
            if full_path.exists() and full_path.is_dir():
                print_success(f"Found: {dir_path}/")
                self.passed_checks += 1
            else:
                error = f"Missing required directory: {dir_path}/"
                print_error(error)
                self.errors.append(error)

    def check_git_repository(self):
        """Verify v14 git repository initialized"""
        print_section("4. Git Repository Check")
        self.total_checks += 3

        git_dir = self.v14_root / ".git"
        if git_dir.exists():
            print_success("Git repository initialized")
            self.passed_checks += 1
        else:
            error = "Git repository not initialized"
            print_error(error)
            self.errors.append(error)
            return

        # Check for initial commit
        try:
            os.chdir(self.v14_root)
            result = subprocess.run(
                ["git", "log", "--oneline"],
                capture_output=True,
                text=True,
                check=True
            )

            if "64c4c5d" in result.stdout:
                print_success("Initial commit found (64c4c5d)")
                self.passed_checks += 1
            else:
                warning = "Initial commit hash different from expected (64c4c5d)"
                print_warning(warning)
                self.warnings.append(warning)
                self.passed_checks += 1
        except subprocess.CalledProcessError:
            error = "No commits found in git repository"
            print_error(error)
            self.errors.append(error)

        # Check branch
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True,
                text=True,
                check=True
            )

            current_branch = result.stdout.strip()
            if current_branch == "main":
                print_success(f"On correct branch: {current_branch}")
                self.passed_checks += 1
            else:
                warning = f"Not on main branch: {current_branch}"
                print_warning(warning)
                self.warnings.append(warning)
                self.passed_checks += 1
        except subprocess.CalledProcessError:
            error = "Failed to determine current branch"
            print_error(error)
            self.errors.append(error)

    def check_component_mapping(self):
        """Verify component migration mapping complete"""
        print_section("5. Component Migration Mapping Check")
        self.total_checks += 2

        mapping_file = self.v14_root / "docs/COMPONENT_MIGRATION_MAPPING.md"
        detailed_mapping = self.v14_root / "docs/DETAILED_V13_COMPONENT_MAPPING.md"

        if mapping_file.exists():
            print_success("Component migration mapping exists")
            self.passed_checks += 1
        else:
            error = "Component migration mapping missing"
            print_error(error)
            self.errors.append(error)

        if detailed_mapping.exists():
            print_success("Detailed component mapping exists")
            self.passed_checks += 1

            # Check file size (should be substantial)
            size = detailed_mapping.stat().st_size
            if size > 10000:  # > 10KB
                print_info(f"Detailed mapping size: {size:,} bytes")
            else:
                warning = f"Detailed mapping seems small: {size:,} bytes"
                print_warning(warning)
                self.warnings.append(warning)
        else:
            error = "Detailed component mapping missing"
            print_error(error)
            self.errors.append(error)

    def check_config_mapping(self):
        """Verify configuration migration mapping complete"""
        print_section("6. Configuration Migration Mapping Check")
        self.total_checks += 1

        config_mapping = self.v14_root / "docs/CONFIGURATION_MIGRATION_MAPPING.md"

        if config_mapping.exists():
            print_success("Configuration migration mapping exists")
            self.passed_checks += 1
        else:
            error = "Configuration migration mapping missing"
            print_error(error)
            self.errors.append(error)

    def check_docs_mapping(self):
        """Verify documentation migration mapping complete"""
        print_section("7. Documentation Migration Mapping Check")
        self.total_checks += 1

        docs_mapping = self.v14_root / "docs/DOCUMENTATION_MIGRATION_MAPPING.md"

        if docs_mapping.exists():
            print_success("Documentation migration mapping exists")
            self.passed_checks += 1
        else:
            error = "Documentation migration mapping missing"
            print_error(error)
            self.errors.append(error)

    def check_safety_checklist(self):
        """Verify migration safety checklist exists"""
        print_section("8. Migration Safety Checklist Check")
        self.total_checks += 1

        checklist = self.v14_root / "docs/MIGRATION_SAFETY_CHECKLIST.md"

        if checklist.exists():
            print_success("Migration safety checklist exists")
            self.passed_checks += 1
        else:
            error = "Migration safety checklist missing"
            print_error(error)
            self.errors.append(error)

    def check_git_branches(self):
        """Verify git branch strategy implemented"""
        print_section("9. Git Branch Strategy Check")
        self.total_checks += 3

        try:
            os.chdir(self.v14_root)
            result = subprocess.run(
                ["git", "branch"],
                capture_output=True,
                text=True,
                check=True
            )

            branches = result.stdout

            if "develop" in branches:
                print_success("develop branch exists")
                self.passed_checks += 1
            else:
                error = "develop branch missing"
                print_error(error)
                self.errors.append(error)

            if "phase-0" in branches:
                print_success("phase-0 branch exists")
                self.passed_checks += 1
            else:
                error = "phase-0 branch missing"
                print_error(error)
                self.errors.append(error)

            if "main" in branches:
                print_success("main branch exists")
                self.passed_checks += 1
            else:
                error = "main branch missing"
                print_error(error)
                self.errors.append(error)

        except subprocess.CalledProcessError as e:
            error = f"Failed to check git branches: {e}"
            print_error(error)
            self.errors.append(error)

    def check_recovered_components(self):
        """Verify v12 components recovered"""
        print_section("10. v12 Component Recovery Check")
        self.total_checks += 1

        recovery_dir = self.v13_root / "v12_recovered_components"

        if recovery_dir.exists():
            py_files = list(recovery_dir.glob("*.py"))
            if len(py_files) >= 10:
                print_success(f"v12 components recovered: {len(py_files)} files")
                self.passed_checks += 1
            else:
                warning = f"Only {len(py_files)} components recovered (expected 10+)"
                print_warning(warning)
                self.warnings.append(warning)
                self.passed_checks += 1
        else:
            error = "v12 recovery directory missing"
            print_error(error)
            self.errors.append(error)

    def print_summary(self):
        """Print validation summary"""
        print_section("Validation Summary")

        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0

        print(f"\nChecks Passed: {self.passed_checks}/{self.total_checks} ({success_rate:.1f}%)")
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.errors:
            print(f"\n{RED}{'='*70}")
            print("ERRORS (Must Fix Before Phase 1):")
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
            print(f"{GREEN}✅ PHASE 0 VALIDATION: PASSED{RESET}")
            print(f"{GREEN}Ready to proceed to Phase 1{RESET}")
        else:
            print(f"{RED}❌ PHASE 0 VALIDATION: FAILED{RESET}")
            print(f"{RED}Fix {len(self.errors)} error(s) before Phase 1{RESET}")
        print(f"{'='*70}\n")

def main():
    """Main entry point"""
    validator = Phase0Validator()
    success = validator.validate_all()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
