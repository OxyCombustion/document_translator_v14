#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test GUI Viewer Agent Migration - V14 (No Display Required)

Tests the migrated GUI viewer agent structure without launching GUI.
Validates the v13→v14 migration was successful.

This test script validates:
- Import paths are correct
- Agent structure follows v14 architecture
- Data source paths are properly configured
- All methods are accessible
"""

import sys
import os

# UTF-8 encoding setup - MANDATORY
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

from pathlib import Path
import inspect


def test_import():
    """Test that GUIViewerAgent can be imported from v14 package"""
    print("Test 1: Import GUIViewerAgent from v14 package...")
    try:
        from specialized_utilities_v14_P20.src.visualization.gui_viewer_agent import GUIViewerAgent
        print("✅ PASSED - GUIViewerAgent imported successfully")
        return True, GUIViewerAgent
    except Exception as e:
        print(f"❌ FAILED - Import error: {e}")
        return False, None


def test_agent_structure(GUIViewerAgent):
    """Test agent has proper v14 structure"""
    print("\nTest 2: Agent structure validation...")
    try:
        # Check inheritance
        from common.src.base.base_agent import BaseAgent
        if not issubclass(GUIViewerAgent, BaseAgent):
            print("❌ FAILED - GUIViewerAgent does not inherit from BaseAgent")
            return False

        # Check required methods exist
        required_methods = ['load_project_context', 'show_status']
        agent = GUIViewerAgent()

        missing_methods = []
        for method in required_methods:
            if not hasattr(agent, method) or not callable(getattr(agent, method)):
                missing_methods.append(method)

        if missing_methods:
            print(f"❌ FAILED - Missing methods: {', '.join(missing_methods)}")
            return False

        print("✅ PASSED - Agent structure is correct")
        print(f"   - Inherits from BaseAgent: ✅")
        print(f"   - Has required methods: ✅")
        return True
    except Exception as e:
        print(f"❌ FAILED - Structure validation error: {e}")
        return False


def test_initialization(GUIViewerAgent):
    """Test agent can be initialized"""
    print("\nTest 3: Agent initialization...")
    try:
        agent = GUIViewerAgent()

        # Check attributes
        required_attrs = ['project_root', 'data_sources', 'current_font_size']
        missing_attrs = []
        for attr in required_attrs:
            if not hasattr(agent, attr):
                missing_attrs.append(attr)

        if missing_attrs:
            print(f"❌ FAILED - Missing attributes: {', '.join(missing_attrs)}")
            return False, None

        print("✅ PASSED - Agent initialized successfully")
        print(f"   - Project root: {agent.project_root}")
        print(f"   - Font size: {agent.current_font_size}pt")
        print(f"   - Data sources: {len(agent.data_sources)} content types")
        return True, agent
    except Exception as e:
        print(f"❌ FAILED - Initialization error: {e}")
        return False, None


def test_data_sources(agent):
    """Test data source configuration"""
    print("\nTest 4: Data source configuration...")
    try:
        expected_types = ['equations', 'tables', 'figures', 'text', 'plots']

        missing_types = []
        for content_type in expected_types:
            if content_type not in agent.data_sources:
                missing_types.append(content_type)

        if missing_types:
            print(f"❌ FAILED - Missing data source types: {', '.join(missing_types)}")
            return False

        # Check data source structure
        for content_type, sources in agent.data_sources.items():
            if 'primary' not in sources or 'secondary' not in sources:
                print(f"❌ FAILED - {content_type} missing primary/secondary sources")
                return False

        print("✅ PASSED - Data sources properly configured")
        print(f"   - Content types: {', '.join(agent.data_sources.keys())}")
        return True
    except Exception as e:
        print(f"❌ FAILED - Data source validation error: {e}")
        return False


def test_data_availability(agent):
    """Test actual data file availability"""
    print("\nTest 5: Data file availability...")
    try:
        available_sources = 0
        total_sources = 0

        for content_type, sources in agent.data_sources.items():
            for source_type, path in sources.items():
                total_sources += 1
                source_path = agent.project_root / path
                if source_path.exists():
                    available_sources += 1
                    if source_path.is_file():
                        size = source_path.stat().st_size / 1024
                        print(f"   ✅ {content_type}/{source_type}: {path} ({size:.1f} KB)")
                    else:
                        print(f"   ✅ {content_type}/{source_type}: {path} (directory)")
                else:
                    print(f"   ❌ {content_type}/{source_type}: {path} (NOT FOUND)")

        if available_sources == 0:
            print("❌ FAILED - No data sources found")
            return False

        print(f"\n✅ PASSED - {available_sources}/{total_sources} data sources available")
        return True
    except Exception as e:
        print(f"❌ FAILED - Data availability check error: {e}")
        return False


def test_methods_callable(agent):
    """Test that key methods are callable"""
    print("\nTest 6: Method accessibility...")
    try:
        # Test methods that don't require GUI
        methods_to_test = {
            'load_project_context': [],
            'show_status': [],
        }

        all_callable = True
        for method_name, args in methods_to_test.items():
            if not hasattr(agent, method_name):
                print(f"   ❌ {method_name}: NOT FOUND")
                all_callable = False
                continue

            method = getattr(agent, method_name)
            if not callable(method):
                print(f"   ❌ {method_name}: NOT CALLABLE")
                all_callable = False
                continue

            print(f"   ✅ {method_name}: accessible")

        if all_callable:
            print("\n✅ PASSED - All key methods are accessible")
            return True
        else:
            print("\n❌ FAILED - Some methods not accessible")
            return False
    except Exception as e:
        print(f"❌ FAILED - Method accessibility check error: {e}")
        return False


def test_v14_compliance(GUIViewerAgent):
    """Test v14 compliance (no sys.path manipulation)"""
    print("\nTest 7: V14 compliance check...")
    try:
        # Read agent source code
        agent_file = inspect.getfile(GUIViewerAgent)
        with open(agent_file, 'r', encoding='utf-8') as f:
            source = f.read()

        # Check for sys.path manipulation (should not be present in v14)
        if 'sys.path.insert' in source or 'sys.path.append' in source:
            print("❌ FAILED - Agent still uses sys.path manipulation (v13 pattern)")
            return False

        # Check for v14 import pattern
        if 'from common.src.base.base_agent import BaseAgent' not in source:
            print("❌ FAILED - Missing v14 import pattern for BaseAgent")
            return False

        print("✅ PASSED - Agent follows v14 architecture")
        print("   - No sys.path manipulation: ✅")
        print("   - Uses v14 imports: ✅")
        return True
    except Exception as e:
        print(f"❌ FAILED - Compliance check error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 80)
    print("GUI Viewer Agent Migration Test - V14")
    print("=" * 80)
    print()

    results = []

    # Test 1: Import
    passed, GUIViewerAgentClass = test_import()
    results.append(("Import", passed))
    if not passed:
        print("\n⚠️ Cannot continue - import failed")
        return

    # Test 2: Agent structure
    passed = test_agent_structure(GUIViewerAgentClass)
    results.append(("Agent Structure", passed))

    # Test 3: Initialization
    passed, agent = test_initialization(GUIViewerAgentClass)
    results.append(("Initialization", passed))
    if not passed:
        print("\n⚠️ Cannot continue - initialization failed")
        return

    # Test 4: Data sources
    passed = test_data_sources(agent)
    results.append(("Data Source Config", passed))

    # Test 5: Data availability
    passed = test_data_availability(agent)
    results.append(("Data Availability", passed))

    # Test 6: Methods
    passed = test_methods_callable(agent)
    results.append(("Method Accessibility", passed))

    # Test 7: V14 compliance
    passed = test_v14_compliance(GUIViewerAgentClass)
    results.append(("V14 Compliance", passed))

    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:30s} {status}")

    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)

    print(f"\nTotal: {total_passed}/{total_tests} tests passed ({total_passed/total_tests*100:.1f}%)")

    if total_passed == total_tests:
        print("\n🎉 GUI Viewer Agent migration to v14 is COMPLETE!")
        print("\nNote: GUI display requires tkinter package and graphical environment.")
        print("      The agent structure and imports have been successfully migrated.")
    else:
        print("\n⚠️ Some tests failed. Review the output above for details.")


if __name__ == "__main__":
    main()
