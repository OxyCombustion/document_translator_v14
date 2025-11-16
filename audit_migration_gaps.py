#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit V13→V14 Migration Gaps

Analyzes what was migrated from v13 to v14 and identifies missing components.
Creates a comprehensive inventory for migration tracking.

Usage:
    python audit_migration_gaps.py
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

from pathlib import Path
import json


def scan_v13_agents():
    """Scan v13 agents directory"""
    v13_root = Path("/home/thermodynamics/document_translator_v13")
    agents_dir = v13_root / "agents"

    if not agents_dir.exists():
        print(f"❌ v13 agents directory not found: {agents_dir}")
        return None

    agents = {
        'directories': [],
        'python_files': [],
        'total_size': 0
    }

    # Scan directories
    for item in agents_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            agents['directories'].append({
                'name': item.name,
                'path': str(item.relative_to(v13_root)),
                'python_files': len(list(item.rglob("*.py")))
            })

    # Scan Python files in root
    for item in agents_dir.glob("*.py"):
        agents['python_files'].append({
            'name': item.name,
            'size': item.stat().st_size,
            'path': str(item.relative_to(v13_root))
        })
        agents['total_size'] += item.stat().st_size

    return agents


def scan_v14_packages():
    """Scan v14 package directories"""
    v14_root = Path("/home/thermodynamics/document_translator_v14")

    packages = []

    # Find all v14 packages
    for package_dir in v14_root.glob("*_v14_P*"):
        if package_dir.is_dir():
            python_files = list(package_dir.rglob("*.py"))
            packages.append({
                'name': package_dir.name,
                'python_files': len(python_files),
                'path': str(package_dir.relative_to(v14_root))
            })

    return packages


def analyze_gui_agents(v13_agents):
    """Analyze GUI-related agents in v13"""
    gui_related = []

    # Check root Python files
    for pf in v13_agents['python_files']:
        if 'gui' in pf['name'].lower() or 'viewer' in pf['name'].lower():
            gui_related.append({
                'name': pf['name'],
                'type': 'file',
                'size': pf['size'],
                'path': pf['path']
            })

    # Check directories
    for d in v13_agents['directories']:
        if 'gui' in d['name'].lower() or 'viewer' in d['name'].lower():
            gui_related.append({
                'name': d['name'],
                'type': 'directory',
                'python_files': d['python_files'],
                'path': d['path']
            })

    return gui_related


def main():
    """Main analysis function"""
    print("=" * 80)
    print("V13→V14 Migration Gap Analysis")
    print("=" * 80)

    # Scan v13
    print("\n📊 Scanning v13 agents directory...")
    v13_agents = scan_v13_agents()

    if v13_agents:
        print(f"✅ Found {len(v13_agents['directories'])} agent directories")
        print(f"✅ Found {len(v13_agents['python_files'])} root Python files")
        total_size_kb = v13_agents['total_size'] / 1024
        print(f"✅ Total size: {total_size_kb:.1f} KB")

    # Scan v14
    print("\n📊 Scanning v14 packages...")
    v14_packages = scan_v14_packages()

    if v14_packages:
        print(f"✅ Found {len(v14_packages)} v14 packages")
        total_py_files = sum(p['python_files'] for p in v14_packages)
        print(f"✅ Total Python files: {total_py_files}")

    # Analyze GUI agents
    print("\n📊 Analyzing GUI-related agents in v13...")
    gui_agents = analyze_gui_agents(v13_agents)

    if gui_agents:
        print(f"✅ Found {len(gui_agents)} GUI-related components:")
        for ga in gui_agents:
            if ga['type'] == 'file':
                print(f"   📄 {ga['name']} ({ga['size']/1024:.1f} KB)")
            else:
                print(f"   📁 {ga['name']} ({ga['python_files']} Python files)")

    # Generate report
    print("\n" + "=" * 80)
    print("MIGRATION STATUS SUMMARY")
    print("=" * 80)

    print("\nV13 Baseline:")
    print(f"  Agent directories: {len(v13_agents['directories'])}")
    print(f"  Root Python files: {len(v13_agents['python_files'])}")
    print(f"  Total size: {v13_agents['total_size']/1024:.1f} KB")

    print("\nV14 Current State:")
    print(f"  Packages: {len(v14_packages)}")
    print(f"  Total Python files: {sum(p['python_files'] for p in v14_packages)}")

    print("\nGUI Components:")
    print(f"  V13 GUI components: {len(gui_agents)}")
    print(f"  V14 GUI components: 1 (gui_viewer_agent.py - just migrated)")
    print(f"  Migration gap: {len(gui_agents) - 1} components not migrated")

    # Top 10 largest v13 agent directories
    print("\n" + "=" * 80)
    print("TOP 10 V13 AGENT DIRECTORIES (by Python file count)")
    print("=" * 80)

    sorted_dirs = sorted(v13_agents['directories'],
                        key=lambda x: x['python_files'],
                        reverse=True)[:10]

    for idx, d in enumerate(sorted_dirs, 1):
        print(f"{idx:2d}. {d['name']:40s} {d['python_files']:3d} Python files")

    # Save detailed report
    report = {
        'v13_agents': v13_agents,
        'v14_packages': v14_packages,
        'gui_components': gui_agents,
        'summary': {
            'v13_directories': len(v13_agents['directories']),
            'v13_root_files': len(v13_agents['python_files']),
            'v14_packages': len(v14_packages),
            'v14_total_files': sum(p['python_files'] for p in v14_packages),
            'gui_gap': len(gui_agents) - 1
        }
    }

    report_file = Path("migration_gap_report.json")
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Detailed report saved to: {report_file}")


if __name__ == "__main__":
    main()
