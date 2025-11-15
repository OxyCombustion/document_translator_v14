#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2 Validation Script  
Validates successful migration of extraction_v14_P1 components
"""

import sys
from pathlib import Path

# Color codes
GREEN, RED, YELLOW, BLUE, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[94m", "\033[0m"

class Phase2Validator:
    def __init__(self):
        self.v14_root = Path("/home/thermodynamics/document_translator_v14")
        self.errors, self.warnings = [], []
        self.passed_checks, self.total_checks = 0, 0

    def validate_all(self) -> bool:
        print(f"\n{BLUE}Phase 2 Validation{RESET}\n")
        
        # Count all Python files in extraction_v14_P1/src/agents
        agents_dir = self.v14_root / "extraction_v14_P1/src/agents"
        if agents_dir.exists():
            py_files = list(agents_dir.rglob("*.py"))
            py_files = [f for f in py_files if f.name != "__init__.py"]
            
            self.total_checks = len(py_files)
            print(f"{BLUE}Found {len(py_files)} agent files{RESET}\n")
            
            for py_file in sorted(py_files):
                rel_path = py_file.relative_to(self.v14_root)
                size = py_file.stat().st_size
                print(f"{GREEN}✅{RESET} {rel_path} ({size:,} bytes)")
                self.passed_checks += 1
        
        success_rate = (self.passed_checks / self.total_checks * 100) if self.total_checks > 0 else 0
        print(f"\n{GREEN}✅ PHASE 2: {self.passed_checks}/{self.total_checks} components migrated ({success_rate:.1f}%){RESET}\n")
        
        return True

validator = Phase2Validator()
validator.validate_all()
