#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module Registry Checker - Prevents Redundant Development

This module MUST be consulted before any new module development to:
1. Check if functionality already exists
2. Identify working modules that can be used instead
3. Prevent wasting time on redundant development

Integration Points:
- Task tool should call this before creating new modules
- Agents should consult this in planning phase
- Development workflow should require registry check
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class ModuleRegistryChecker:
    """Prevents redundant module development by checking existing functionality"""

    def __init__(self):
        self.registry_path = Path("MODULE_REGISTRY.json")
        self.registry = self.load_registry()

    def load_registry(self) -> Dict:
        """Load the module registry"""
        if not self.registry_path.exists():
            raise FileNotFoundError(
                f"MODULE_REGISTRY.json not found. This is required to prevent redundant development."
            )

        with open(self.registry_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def check_before_development(self, requirement: str, functionality_type: str) -> Dict:
        """
        MANDATORY check before any new module development.

        Args:
            requirement: What functionality is needed (e.g., "extract equations")
            functionality_type: Category (e.g., "equation_extraction", "table_extraction")

        Returns:
            Dict with recommendations: use_existing, enhance_existing, or build_new
        """
        print(f"\nMODULE REGISTRY CHECK")
        print(f"   Requirement: {requirement}")
        print(f"   Category: {functionality_type}")
        print("=" * 50)

        # Find existing modules in this category
        existing_modules = self.find_existing_modules(functionality_type)
        working_modules = [(name, info) for name, info in existing_modules if info.get("status") == "WORKING"]
        excellent_modules = [(name, info) for name, info in existing_modules if info.get("status") == "EXCELLENT"]
        breakthrough_modules = [(name, info) for name, info in existing_modules if info.get("status") == "BREAKTHROUGH"]

        recommendation = {
            "action": None,
            "existing_modules": existing_modules,
            "working_modules": working_modules,
            "recommendations": [],
            "justification_required": False
        }

        # Decision logic
        if excellent_modules or breakthrough_modules:
            recommendation["action"] = "USE_EXISTING"
            recommendation["recommendations"] = excellent_modules + breakthrough_modules
            print(f"RECOMMENDATION: USE EXISTING MODULE")
            print(f"   Found {len(excellent_modules + breakthrough_modules)} excellent/breakthrough modules")
            for name, info in excellent_modules + breakthrough_modules:
                print(f"   {name}: {info.get('performance', 'N/A')}")
                print(f"      Status: {info.get('status')} | Use case: {info.get('use_case', 'N/A')}")

        elif working_modules:
            recommendation["action"] = "USE_OR_ENHANCE_EXISTING"
            recommendation["recommendations"] = working_modules
            print(f"RECOMMENDATION: USE OR ENHANCE EXISTING")
            print(f"   Found {len(working_modules)} working modules")
            for name, info in working_modules:
                print(f"   {name}: {info.get('performance', 'N/A')}")
                print(f"      Status: {info.get('status')} | Last tested: {info.get('last_tested', 'Unknown')}")
            print(f"   Question: Can these be enhanced instead of building new?")

        elif existing_modules:
            # Found modules but they're broken/deprecated
            recommendation["action"] = "ENHANCE_OR_BUILD_NEW"
            recommendation["justification_required"] = True
            print(f"RECOMMENDATION: ENHANCE OR BUILD NEW")
            print(f"   Found {len(existing_modules)} modules but they may need repair")
            for name, info in existing_modules:
                print(f"   {name}: Status {info.get('status', 'UNKNOWN')}")
            print(f"   Question: Can existing be repaired vs building new?")

        else:
            # No existing modules found
            recommendation["action"] = "BUILD_NEW"
            print(f"RECOMMENDATION: BUILD NEW MODULE")
            print(f"   No existing modules found for this functionality")

        # Always show protocol reminder
        self.show_protocol_reminder(recommendation["action"])

        return recommendation

    def find_existing_modules(self, functionality_type: str) -> List[Tuple[str, Dict]]:
        """Find existing modules for a functionality type"""
        existing = []

        # Search all categories for related functionality
        for category, modules in self.registry.items():
            if category.endswith("_modules") and isinstance(modules, dict):
                for subcategory, submodules in modules.items():
                    if functionality_type in subcategory or subcategory in functionality_type:
                        if isinstance(submodules, dict):
                            for module_name, module_info in submodules.items():
                                existing.append((module_name, module_info))

        return existing

    def show_protocol_reminder(self, action: str):
        """Show protocol reminders based on action"""
        print(f"\nPROTOCOL REMINDER:")

        if action == "USE_EXISTING":
            print("   1. Test the existing module first to verify it works")
            print("   2. Check its current output format matches your needs")
            print("   3. Only proceed if existing module fails or is insufficient")

        elif action == "USE_OR_ENHANCE_EXISTING":
            print("   1. Test existing modules first")
            print("   2. Identify what specific enhancement is needed")
            print("   3. Modify existing module rather than building new")
            print("   4. Update MODULE_REGISTRY.json with changes")

        elif action == "ENHANCE_OR_BUILD_NEW":
            print("   1. Attempt to repair existing modules first")
            print("   2. Document why repair is not feasible")
            print("   3. Justify why building new is better than fixing")

        elif action == "BUILD_NEW":
            print("   1. Confirm no similar functionality exists elsewhere")
            print("   2. Document why new module is necessary")
            print("   3. Add new module to MODULE_REGISTRY.json when complete")

        print("   Remember: Building new modules wastes time and electricity when working ones exist!")

    def get_working_modules_for_task(self, task_description: str) -> List[Dict]:
        """Get specifically working modules that could handle a task"""
        working_modules = []

        task_lower = task_description.lower()

        # Search for relevant working modules
        for category, modules in self.registry.items():
            if category.endswith("_modules") and isinstance(modules, dict):
                for subcategory, submodules in modules.items():
                    if isinstance(submodules, dict):
                        for module_name, module_info in submodules.items():
                            if module_info.get("status") in ["WORKING", "EXCELLENT", "BREAKTHROUGH"]:
                                # Check if module is relevant to task
                                use_case = module_info.get("use_case", "").lower()
                                purpose = module_info.get("purpose", "").lower()

                                if (any(keyword in use_case for keyword in task_lower.split()) or
                                    any(keyword in purpose for keyword in task_lower.split())):
                                    working_modules.append({
                                        "name": module_name,
                                        "category": f"{category}.{subcategory}",
                                        "info": module_info
                                    })

        return working_modules

    def update_module_status(self, module_name: str, new_status: str,
                           performance: str = None, last_tested: str = None):
        """Update a module's status in the registry"""
        if last_tested is None:
            last_tested = datetime.now().strftime("%Y-%m-%d")

        # Find and update the module
        updated = False
        for category, modules in self.registry.items():
            if category.endswith("_modules") and isinstance(modules, dict):
                for subcategory, submodules in modules.items():
                    if isinstance(submodules, dict) and module_name in submodules:
                        submodules[module_name]["status"] = new_status
                        submodules[module_name]["last_tested"] = last_tested
                        if performance:
                            submodules[module_name]["performance"] = performance
                        updated = True
                        break

        if updated:
            # Save updated registry
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                json.dump(self.registry, f, indent=2)
            print(f"Updated {module_name} status to {new_status}")
        else:
            print(f"Module {module_name} not found in registry")


def check_before_building_module(requirement: str, functionality_type: str) -> Dict:
    """
    MANDATORY function to call before any new module development.

    Usage:
        result = check_before_building_module("extract equations", "equation_extraction")
        if result["action"] == "USE_EXISTING":
            # Use the recommended existing module
            recommended = result["recommendations"][0]
            module_name = recommended[0]
            # Test the existing module...
    """
    checker = ModuleRegistryChecker()
    return checker.check_before_development(requirement, functionality_type)


def main():
    """Test the module registry checker"""
    print("MODULE REGISTRY CHECKER TEST")
    print("=" * 60)

    # Test equation extraction check
    result = check_before_building_module("extract equations from PDF", "equation_extraction")

    print(f"\nRESULT: {result['action']}")
    print(f"Found {len(result['working_modules'])} working modules")

    if result['working_modules']:
        print("\nWORKING MODULES YOU SHOULD USE:")
        for name, info in result['working_modules']:
            print(f"  {name}")
            print(f"     Performance: {info.get('performance', 'N/A')}")
            print(f"     Use case: {info.get('use_case', 'N/A')}")


if __name__ == "__main__":
    main()