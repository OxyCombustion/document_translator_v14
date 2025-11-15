# Phase 19 Migration Plan: Extraction Utilities

## Overview

**Target Package**: `extraction_utilities_v14_P18`
**Category**: Specialized extraction utility agents
**Component Count**: 8 categories, 12 files total

## Migration Scope

### Components to Migrate

From `/home/thermodynamics/document_translator_v13/agents/`:

#### 1. **equation_extractor/** (2 files)
- `analyze_extracted_text.py` (3.5K) - Text analysis for equation extraction
- `__init__.py` (1.1K) - Package exports

#### 2. **equation_number_ocr_agent/** (1 file)
- `agent.py` (6.5K) - OCR-based equation number detection

#### 3. **equation_refinement_agent/** (2 files)
- `agent.py` (56K) - Equation extraction refinement and enhancement
- `__init__.py` (64 bytes) - Package exports

#### 4. **figure_extraction/** (2 files)
- `data_structures.py` (4.2K) - Figure extraction data structures
- `figure_detection_agent.py` (25K) - Figure detection logic

#### 5. **formula_detector_agent/** (1 file)
- `agent.py` (2.3K) - Formula detection heuristics

#### 6. **frame_box_detector/** (1 file)
- `agent.py` (11K) - Bounding box detection for content framing

#### 7. **table_extraction/** (1 file)
- `table_layout_agent.py` (21K) - Table layout analysis and extraction

#### 8. **table_extractor/** (2 files)
- `enhanced_detection_criteria.py` (16K) - Enhanced table detection
- `validation_filtered_extractor.py` (13K) - Validated table extraction
- `__init__.py` (0 bytes) - Empty package init

**Total**: 12 files (~159KB of Python code)

## Package Structure

```
extraction_utilities_v14_P18/
├── __init__.py                                # Package root with version 14.0.0
├── src/
│   ├── __init__.py                            # Source root with exports
│   ├── equations/
│   │   ├── __init__.py                        # Equation utilities exports
│   │   ├── analyze_extracted_text.py          # From equation_extractor/
│   │   ├── equation_number_ocr_agent.py       # From equation_number_ocr_agent/agent.py
│   │   ├── equation_refinement_agent.py       # From equation_refinement_agent/agent.py
│   │   ├── __init__.py.original_extractor     # Preserved equation_extractor/__init__.py
│   │   └── __init__.py.original_refinement    # Preserved equation_refinement_agent/__init__.py
│   ├── figures/
│   │   ├── __init__.py                        # Figure utilities exports
│   │   ├── data_structures.py                 # From figure_extraction/
│   │   └── figure_detection_agent.py          # From figure_extraction/
│   ├── detection/
│   │   ├── __init__.py                        # Detection utilities exports
│   │   ├── formula_detector_agent.py          # From formula_detector_agent/agent.py
│   │   └── frame_box_detector.py              # From frame_box_detector/agent.py
│   └── tables/
│       ├── __init__.py                        # Table utilities exports
│       ├── table_layout_agent.py              # From table_extraction/
│       ├── enhanced_detection_criteria.py     # From table_extractor/
│       ├── validation_filtered_extractor.py   # From table_extractor/
│       └── __init__.py.original_extractor     # Preserved table_extractor/__init__.py
```

## Migration Steps

### 1. Create Branch
```bash
cd /home/thermodynamics/document_translator_v14
git checkout develop
git checkout -b phase-19
```

### 2. Create Package Structure
```bash
mkdir -p extraction_utilities_v14_P18/src/{equations,figures,detection,tables}
```

### 3. Create Root __init__.py Files

**extraction_utilities_v14_P18/__init__.py**:
```python
"""
Extraction Utilities v14 P18

Specialized extraction utility agents for equations, figures, formulas, and tables.
Provides refinement, detection, analysis, and enhanced extraction capabilities.
"""

__version__ = "14.0.0"

from . import src

__all__ = ['src']
```

**extraction_utilities_v14_P18/src/__init__.py**:
```python
"""Extraction utilities source package."""

from . import equations
from . import figures
from . import detection
from . import tables

__all__ = [
    'equations',
    'figures',
    'detection',
    'tables',
]
```

### 4. Create Category __init__.py Files

**extraction_utilities_v14_P18/src/equations/__init__.py**:
```python
"""Equation extraction utilities."""

from .analyze_extracted_text import *
from .equation_number_ocr_agent import *
from .equation_refinement_agent import *

__all__ = []  # Will be populated during import cleanup
```

**extraction_utilities_v14_P18/src/figures/__init__.py**:
```python
"""Figure extraction utilities."""

from .data_structures import *
from .figure_detection_agent import *

__all__ = []  # Will be populated during import cleanup
```

**extraction_utilities_v14_P18/src/detection/__init__.py**:
```python
"""Detection utilities for formulas and frames."""

from .formula_detector_agent import *
from .frame_box_detector import *

__all__ = []  # Will be populated during import cleanup
```

**extraction_utilities_v14_P18/src/tables/__init__.py**:
```python
"""Table extraction utilities."""

from .table_layout_agent import *
from .enhanced_detection_criteria import *
from .validation_filtered_extractor import *

__all__ = []  # Will be populated during import cleanup
```

### 5. Copy Components from v13
```bash
# Equation utilities
cp /home/thermodynamics/document_translator_v13/agents/equation_extractor/analyze_extracted_text.py \
   extraction_utilities_v14_P18/src/equations/
cp /home/thermodynamics/document_translator_v13/agents/equation_extractor/__init__.py \
   extraction_utilities_v14_P18/src/equations/__init__.py.original_extractor

cp /home/thermodynamics/document_translator_v13/agents/equation_number_ocr_agent/agent.py \
   extraction_utilities_v14_P18/src/equations/equation_number_ocr_agent.py

cp /home/thermodynamics/document_translator_v13/agents/equation_refinement_agent/agent.py \
   extraction_utilities_v14_P18/src/equations/equation_refinement_agent.py
cp /home/thermodynamics/document_translator_v13/agents/equation_refinement_agent/__init__.py \
   extraction_utilities_v14_P18/src/equations/__init__.py.original_refinement

# Figure utilities
cp /home/thermodynamics/document_translator_v13/agents/figure_extraction/data_structures.py \
   extraction_utilities_v14_P18/src/figures/
cp /home/thermodynamics/document_translator_v13/agents/figure_extraction/figure_detection_agent.py \
   extraction_utilities_v14_P18/src/figures/

# Detection utilities
cp /home/thermodynamics/document_translator_v13/agents/formula_detector_agent/agent.py \
   extraction_utilities_v14_P18/src/detection/formula_detector_agent.py
cp /home/thermodynamics/document_translator_v13/agents/frame_box_detector/agent.py \
   extraction_utilities_v14_P18/src/detection/frame_box_detector.py

# Table utilities
cp /home/thermodynamics/document_translator_v13/agents/table_extraction/table_layout_agent.py \
   extraction_utilities_v14_P18/src/tables/
cp /home/thermodynamics/document_translator_v13/agents/table_extractor/enhanced_detection_criteria.py \
   extraction_utilities_v14_P18/src/tables/
cp /home/thermodynamics/document_translator_v13/agents/table_extractor/validation_filtered_extractor.py \
   extraction_utilities_v14_P18/src/tables/
cp /home/thermodynamics/document_translator_v13/agents/table_extractor/__init__.py \
   extraction_utilities_v14_P18/src/tables/__init__.py.original_extractor
```

### 6. Create Validation Script

**tools/validate_phase19.py**:
```python
#!/usr/bin/env python3
"""Validate Phase 19 migration: Extraction Utilities."""

from pathlib import Path

def count_python_files(directory: Path) -> int:
    """Count migrated Python files (*.py except __init__.py, plus __init__.py.original* if present)."""
    files = [f for f in directory.glob('*.py') if f.name != '__init__.py']
    # Count __init__.py.original* files
    files.extend(directory.glob('__init__.py.original*'))
    return len(files)

def main():
    print("\n" + "="*70)
    print("Phase 19 Migration Validation: Extraction Utilities")
    print("="*70 + "\n")

    base = Path("extraction_utilities_v14_P18/src")

    categories = {
        'equations': ('equations/', 5),   # 3 agents + 2 original inits
        'figures': ('figures/', 2),       # 2 files
        'detection': ('detection/', 2),   # 2 agents
        'tables': ('tables/', 4),         # 3 agents + 1 original init
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
            print(f"  Expected files in {path}:")
            if name == 'equations':
                print(f"    - analyze_extracted_text.py")
                print(f"    - equation_number_ocr_agent.py")
                print(f"    - equation_refinement_agent.py")
                print(f"    - __init__.py.original_extractor")
                print(f"    - __init__.py.original_refinement")
            elif name == 'figures':
                print(f"    - data_structures.py")
                print(f"    - figure_detection_agent.py")
            elif name == 'detection':
                print(f"    - formula_detector_agent.py")
                print(f"    - frame_box_detector.py")
            elif name == 'tables':
                print(f"    - table_layout_agent.py")
                print(f"    - enhanced_detection_criteria.py")
                print(f"    - validation_filtered_extractor.py")
                print(f"    - __init__.py.original_extractor")

    print("\n" + "-"*70)
    if all_pass:
        print(f"\033[92m✓ PHASE 19 COMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    else:
        print(f"\033[91m✗ PHASE 19 INCOMPLETE: {total_found}/{total_expected} components migrated\033[0m")
    print("-"*70 + "\n")

    return 0 if all_pass else 1

if __name__ == '__main__':
    exit(main())
```

### 7. Validate Migration
```bash
cd /home/thermodynamics/document_translator_v14
python3 tools/validate_phase19.py
```

Expected output:
```
✓ equations              5/5 files
✓ figures                2/2 files
✓ detection              2/2 files
✓ tables                 4/4 files
✓ PHASE 19 COMPLETE: 13/13 components migrated
```

### 8. Create Documentation

**PHASE_19_COMPLETE_SUMMARY.md** documenting:
- Migration success
- Component list
- Package structure
- Utility functions and capabilities
- Integration notes

### 9. Commit and Merge
```bash
git add extraction_utilities_v14_P18/ tools/validate_phase19.py
git add PHASE_19_MIGRATION_PLAN.md PHASE_19_COMPLETE_SUMMARY.md
git commit -m "feat: Complete Phase 19 migration - Extraction utilities (13 components)

Phase 19 delivers specialized extraction utility agents.

Key Deliverables:
✅ 4 utility categories migrated to extraction_utilities_v14_P18
✅ Equation utilities (5 components): refinement, OCR, analysis
✅ Figure utilities (2 components): detection, data structures
✅ Detection utilities (2 components): formula, frame detection
✅ Table utilities (4 components): layout, enhanced detection, validation

Migration Quality:
- 100% component migration rate (13/13)
- Zero component loss from v13
- Proper package structure with __init__.py exports
- Automated validation script
- Comprehensive documentation

Cumulative Progress:
- Phases 1-18: 183 components ✅
- Phase 19: 13 components ✅
- Total: 196/339 components (57.8%)

Package Architecture:
- equations/: Refinement, OCR, analysis utilities
- figures/: Detection and data structures
- detection/: Formula and frame detection
- tables/: Layout, enhanced detection, validation

External Dependencies:
- PyMuPDF for PDF access
- OCR libraries for equation number detection
- OpenCV for image processing

Next Phase:
- Phase 20: Analysis and validation components (~15-20 components)
"

git checkout develop
git merge phase-19 --no-ff -m "Merge phase-19: Extraction utilities migration complete"
git tag -a v14.0.0-phase19 -m "Release v14.0.0-phase19: Extraction Utilities Migration Complete"
```

## Success Criteria

- ✅ All 13 extraction utility files migrated from v13
- ✅ Package structure created with proper __init__.py files
- ✅ Validation script passes (13/13 components)
- ✅ Zero component loss from v13
- ✅ Documentation complete
- ✅ Git workflow complete (commit, merge, tag)

## Progress Tracking

- **Starting Progress**: 183/339 components (54.0%)
- **This Phase**: +13 components
- **Ending Progress**: 196/339 components (57.8%)
- **Milestone**: Approaching 60%!

## External Dependencies

- **PyMuPDF**: PDF document access and processing
- **OCR Libraries**: Equation number detection (Tesseract, pix2tex)
- **OpenCV**: Image processing for detection
- **NumPy**: Numerical operations
- **Python**: 3.11+ required

## Notes

- Equation refinement agent (56K) is the largest component
- Figure detection provides complementary functionality to Phase 17 figure extraction
- Table utilities complement Phase 17 table extraction
- Detection utilities provide formula and frame detection capabilities
- Import cleanup deferred to later phase
