#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test GUI Viewer Agent - V14

Tests the migrated GUI viewer agent with Chapter 4 extraction outputs.
Validates the v13→v14 migration was successful.

Usage:
    python test_gui_viewer.py --text        # View text extractions
    python test_gui_viewer.py --images      # View image extractions
    python test_gui_viewer.py --unified     # View all content types
    python test_gui_viewer.py --cli         # Interactive CLI mode
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

import argparse
import tkinter as tk
from pathlib import Path

# Import GUI viewer agent from v14 package
from specialized_utilities_v14_P20.src.visualization.gui_viewer_agent import GUIViewerAgent


def test_viewer_import():
    """Test that GUIViewerAgent can be imported"""
    print("Testing GUI Viewer Agent import...")
    try:
        agent = GUIViewerAgent()
        print("✅ GUIViewerAgent imported successfully")
        print(f"   Project root: {agent.project_root}")
        print(f"   Current font size: {agent.current_font_size}pt")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_context_loading():
    """Test context loading"""
    print("\nTesting context loading...")
    try:
        agent = GUIViewerAgent()
        context = agent.load_project_context()
        print("✅ Context loaded successfully")
        print(f"   Loaded files: {len(context['loaded_files'])}")
        return True
    except Exception as e:
        print(f"❌ Context loading failed: {e}")
        return False


def test_data_sources():
    """Test data source availability"""
    print("\nTesting data source availability...")
    agent = GUIViewerAgent()

    available_sources = 0
    total_sources = 0

    for content_type, sources in agent.data_sources.items():
        for source_type, path in sources.items():
            total_sources += 1
            source_path = agent.project_root / path
            if source_path.exists():
                available_sources += 1
                print(f"✅ {content_type}/{source_type}: {path}")
            else:
                print(f"❌ {content_type}/{source_type}: {path} (NOT FOUND)")

    print(f"\n📊 Data sources: {available_sources}/{total_sources} available")
    return available_sources > 0


def launch_text_viewer():
    """Launch text viewer"""
    print("\nLaunching text viewer...")
    agent = GUIViewerAgent()
    agent.load_project_context()

    root = tk.Tk()
    root.withdraw()

    viewer = agent.create_text_viewer()
    if viewer:
        print("✅ Text viewer launched successfully")
        print("   Close the viewer window when done")
        root.mainloop()
    else:
        print("❌ Text viewer launch failed")


def launch_image_viewer():
    """Launch image viewer"""
    print("\nLaunching image viewer...")
    agent = GUIViewerAgent()
    agent.load_project_context()

    root = tk.Tk()
    root.withdraw()

    viewer = agent.create_image_viewer()
    if viewer:
        print("✅ Image viewer launched successfully")
        print("   Close the viewer window when done")
        root.mainloop()
    else:
        print("❌ Image viewer launch failed")


def launch_unified_viewer():
    """Launch unified viewer"""
    print("\nLaunching unified viewer...")
    agent = GUIViewerAgent()
    agent.load_project_context()

    root = tk.Tk()
    root.withdraw()

    viewer = agent.create_unified_viewer()
    if viewer:
        print("✅ Unified viewer launched successfully")
        print("   Close the viewer window when done")
        root.mainloop()
    else:
        print("❌ Unified viewer launch failed")


def run_cli():
    """Run interactive CLI"""
    print("\nLaunching interactive CLI...")
    agent = GUIViewerAgent()
    agent.run_cli()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test V14 GUI Viewer Agent")
    parser.add_argument("--test", action="store_true", help="Run import and data source tests")
    parser.add_argument("--text", action="store_true", help="Launch text viewer")
    parser.add_argument("--images", action="store_true", help="Launch image viewer")
    parser.add_argument("--unified", action="store_true", help="Launch unified viewer")
    parser.add_argument("--cli", action="store_true", help="Run interactive CLI")

    args = parser.parse_args()

    print("=" * 80)
    print("V14 GUI Viewer Agent Test")
    print("=" * 80)

    if args.test:
        # Run tests
        print("\nRunning tests...\n")

        results = []
        results.append(("Import Test", test_viewer_import()))
        results.append(("Context Loading", test_context_loading()))
        results.append(("Data Sources", test_data_sources()))

        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80)

        for test_name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name:30s} {status}")

        total_passed = sum(1 for _, passed in results if passed)
        print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    elif args.text:
        launch_text_viewer()
    elif args.images:
        launch_image_viewer()
    elif args.unified:
        launch_unified_viewer()
    elif args.cli:
        run_cli()
    else:
        # Default: run tests
        print("\nNo action specified. Running tests...\n")
        print("Usage:")
        print("  python test_gui_viewer.py --test      # Run tests")
        print("  python test_gui_viewer.py --text      # Launch text viewer")
        print("  python test_gui_viewer.py --images    # Launch image viewer")
        print("  python test_gui_viewer.py --unified   # Launch unified viewer")
        print("  python test_gui_viewer.py --cli       # Interactive CLI")
        print()

        results = []
        results.append(("Import Test", test_viewer_import()))
        results.append(("Context Loading", test_context_loading()))
        results.append(("Data Sources", test_data_sources()))

        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80)

        for test_name, passed in results:
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"{test_name:30s} {status}")

        total_passed = sum(1 for _, passed in results if passed)
        print(f"\nTotal: {total_passed}/{len(results)} tests passed")


if __name__ == "__main__":
    main()
