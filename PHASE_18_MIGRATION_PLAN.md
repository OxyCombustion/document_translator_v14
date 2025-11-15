# Phase 18 Migration Plan: Docling Agents

## Overview

**Target Package**: `docling_agents_v14_P17`
**Category**: Docling-based document processing agents
**Component Count**: 3 categories, 5 files total

## Migration Scope

### Components to Migrate

From `/home/thermodynamics/document_translator_v13/agents/`:

#### 1. **docling_agent/** (2 files)
- `agent.py` (8.1K) - Basic Docling agent wrapper
- `__init__.py` (28 bytes) - Package initialization

#### 2. **docling_first_agent/** (2 files)
- `docling_first_agent.py` (114K) - Primary Docling extraction agent
- `__init__.py` (793 bytes) - Package exports

#### 3. **docling_roi_agent/** (1 file)
- `agent.py` (4.7K) - Region of Interest Docling agent

**Total**: 5 files (~127KB of Python code)

## Package Structure

```
docling_agents_v14_P17/
├── __init__.py                          # Package root with version 14.0.0
├── src/
│   ├── __init__.py                      # Source root with exports
│   ├── basic/
│   │   ├── __init__.py                  # Basic Docling agent exports
│   │   ├── agent.py                     # From docling_agent/agent.py
│   │   └── __init__.py.original         # Preserved v13 __init__.py
│   ├── primary/
│   │   ├── __init__.py                  # Primary agent exports
│   │   ├── docling_first_agent.py       # From docling_first_agent/docling_first_agent.py
│   │   └── __init__.py.original         # Preserved v13 __init__.py
│   └── roi/
│       ├── __init__.py                  # ROI agent exports
│       └── agent.py                     # From docling_roi_agent/agent.py
```

## Migration Steps

### 1. Create Branch
```bash
cd /home/thermodynamics/document_translator_v14
git checkout develop
git pull origin develop
git checkout -b phase-18
```

### 2. Create Package Structure
```bash
mkdir -p docling_agents_v14_P17/src/{basic,primary,roi}
```

### 3. Create Root __init__.py Files

**docling_agents_v14_P17/__init__.py**:
```python
"""
Docling Agents v14 P17

Docling-based document processing agents.
Provides basic Docling wrapper, primary extraction agent, and region-of-interest processing.
"""

__version__ = "14.0.0"

from . import src

__all__ = ['src']
```

**docling_agents_v14_P17/src/__init__.py**:
```python
"""Docling agents source package."""

from . import basic
from . import primary
from . import roi

__all__ = [
    'basic',
    'primary',
    'roi',
]
```

### 4. Create Category __init__.py Files

**docling_agents_v14_P17/src/basic/__init__.py**:
```python
"""Basic Docling agent wrapper."""

from .agent import *

__all__ = []  # Will be populated during import cleanup
```

**docling_agents_v14_P17/src/primary/__init__.py**:
```python
"""Primary Docling extraction agent."""

from .docling_first_agent import *

__all__ = []  # Will be populated during import cleanup
```

**docling_agents_v14_P17/src/roi/__init__.py**:
```python
"""Docling region-of-interest agent."""

from .agent import *

__all__ = []  # Will be populated during import cleanup
```

### 5. Copy Components from v13
```bash
# Basic Docling agent
cp /home/thermodynamics/document_translator_v13/agents/docling_agent/agent.py \
   docling_agents_v14_P17/src/basic/
cp /home/thermodynamics/document_translator_v13/agents/docling_agent/__init__.py \
   docling_agents_v14_P17/src/basic/__init__.py.original

# Primary Docling agent
cp /home/thermodynamics/document_translator_v13/agents/docling_first_agent/docling_first_agent.py \
   docling_agents_v14_P17/src/primary/
cp /home/thermodynamics/document_translator_v13/agents/docling_first_agent/__init__.py \
   docling_agents_v14_P17/src/primary/__init__.py.original

# ROI Docling agent
cp /home/thermodynamics/document_translator_v13/agents/docling_roi_agent/agent.py \
   docling_agents_v14_P17/src/roi/
```

### 6. Create Validation Script

**tools/validate_phase18.py**:
```python
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
```

### 7. Validate Migration
```bash
cd /home/thermodynamics/document_translator_v14
python3 tools/validate_phase18.py
```

Expected output:
```
✓ basic                  2/2 files
✓ primary                2/2 files
✓ roi                    1/1 files
✓ PHASE 18 COMPLETE: 5/5 components migrated
```

### 8. Create Documentation

**PHASE_18_COMPLETE_SUMMARY.md** documenting:
- Migration success
- Component list
- Package structure
- External dependencies (Docling library)
- Integration notes

### 9. Commit and Merge
```bash
git add docling_agents_v14_P17/ tools/validate_phase18.py
git add PHASE_18_MIGRATION_PLAN.md PHASE_18_COMPLETE_SUMMARY.md
git commit -m "feat: Complete Phase 18 migration - Docling agents (5 components)

Phase 18 delivers Docling-based document processing capabilities.

Key Deliverables:
✅ 3 Docling agent categories migrated to docling_agents_v14_P17
✅ Basic Docling agent wrapper
✅ Primary extraction agent (114K - comprehensive Docling integration)
✅ Region-of-interest processing agent

Migration Quality:
- 100% component migration rate (5/5)
- Zero component loss from v13
- Proper package structure with __init__.py exports
- Automated validation script
- Comprehensive documentation

Cumulative Progress:
- Phases 1-17: 178 components ✅
- Phase 18: 5 components ✅
- Total: 183/339 components (54.0%)

Package Architecture:
- basic/: Basic Docling wrapper
- primary/: Primary extraction agent
- roi/: Region-of-interest processing

External Dependencies:
- Docling library for document conversion
- PyMuPDF for PDF access
- Python 3.11+

Next Phase:
- Phase 19: Extraction utilities (~15-20 components)
"

git checkout develop
git merge phase-18 --no-ff -m "Merge phase-18: Docling agents migration complete"
git tag -a v14.0.0-phase18 -m "Release v14.0.0-phase18: Docling Agents Migration Complete

Phase 18 delivers Docling-based document processing capabilities.

Key Deliverables:
✅ 3 Docling agent categories migrated to docling_agents_v14_P17
✅ Basic Docling agent wrapper
✅ Primary extraction agent (114K - comprehensive Docling integration)
✅ Region-of-interest processing agent
✅ 54% milestone: 183/339 components migrated (over halfway)

Migration Quality:
- 100% component migration rate (5/5)
- Zero component loss from v13
- Proper package structure with __init__.py exports
- Automated validation script
- Comprehensive documentation

Cumulative Progress:
- Phase 1: 16 common utilities ✅
- Phase 2: 34 extraction components ✅
- Phase 3: 37 RAG components ✅
- Phase 4: 9 curation components ✅
- Phase 5: 7 semantic processing components ✅
- Phase 6: 9 relationship detection components ✅
- Phase 7: 5 database components ✅
- Phase 8: 1 CLI component ✅
- Phase 9: 9 agent infrastructure components ✅
- Phase 10: 9 parallel processing components ✅
- Phase 11: 6 chunking components ✅
- Phase 12: 8 cross-referencing components ✅
- Phase 13: 5 extraction comparison components ✅
- Phase 14: 9 metadata components ✅
- Phase 15: 5 detection components ✅
- Phase 16: 10 specialized extraction components ✅
- Phase 17: 8 RAG extraction components ✅
- Phase 18: 5 Docling agent components ✅
- Total: 183/339 components (54.0%) ✅

Eighteen-Package Architecture:
- extraction_v14_P1: PDF → JSON extraction
- rag_v14_P2: JSON → JSONL+Graph RAG preparation
- curation_v14_P3: JSONL → Database curation
- semantic_processing_v14_P4: Document understanding
- relationship_detection_v14_P5: Relationship analysis
- database_v14_P6: Document registry & storage
- cli_v14_P7: Command line interface
- agent_infrastructure_v14_P8: Agent base classes
- parallel_processing_v14_P9: Multi-core optimization
- chunking_v14_P10: Semantic chunking
- cross_referencing_v14_P11: Citation & reference linking
- extraction_comparison_v14_P12: Multi-method comparison
- metadata_v14_P13: Bibliographic integration
- detection_v14_P14: Content detection
- specialized_extraction_v14_P15: Object detection
- rag_extraction_v14_P16: RAG-specific extraction
- docling_agents_v14_P17: Docling processing ✅ NEW

Next Phases:
- Phase 19: Extraction utilities (~15-20 components)
- Phase 20+: Remaining categories (~156 components)

Documentation:
- PHASE_18_MIGRATION_PLAN.md (planning document)
- PHASE_18_COMPLETE_SUMMARY.md (complete summary)
- tools/validate_phase18.py (validation script)
"
```

## Success Criteria

- ✅ All 5 Docling agent files migrated from v13
- ✅ Package structure created with proper __init__.py files
- ✅ Validation script passes (5/5 components)
- ✅ Zero component loss from v13
- ✅ Documentation complete
- ✅ Git workflow complete (commit, merge, tag)

## Progress Tracking

- **Starting Progress**: 178/339 components (52.5%)
- **This Phase**: +5 components
- **Ending Progress**: 183/339 components (54.0%)
- **Milestone**: Over 50% complete!

## External Dependencies

- **Docling**: Document conversion library
- **PyMuPDF**: PDF document access
- **Python**: 3.11+ required

## Notes

- Docling agents provide ML-powered document processing
- Primary agent (114K) is comprehensive Docling integration
- ROI agent enables region-specific processing
- These agents complement the detection agents from Phase 15
- Import cleanup deferred to later phase
