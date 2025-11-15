# Phase 15 Migration Plan: Content Detection Agents

**Target**: 5 components from 1 agent category
**Package**: detection_v14_P14
**Priority**: P1 (Critical) - Core content detection for extraction pipeline
**Estimated Size**: ~104KB of code

## Migration Strategy

### Package Decision: Single Package for Detection

**Recommendation**: Create **single package `detection_v14_P14`** for content detection agents

**Rationale**:
1. **Cohesion**: All agents perform content detection tasks (figures, tables, text)
2. **Size**: 5 components (~33KB actual) - small, focused package
3. **Functionality**: Unified approach to content detection across modalities
4. **Integration**: Core dependency for extraction pipeline

**Package Structure**:
```
detection_v14_P14/
├── __init__.py
├── src/
│   ├── __init__.py
│   ├── docling/               # 3 components - Docling-based detectors
│   └── unified/               # 2 components - Unified detection + original init
```

## Components to Migrate (5 components)

### Category 1: Docling Detection (3 components, ~18KB)

**Source**: `document_translator_v13/agents/detection/`
**Destination**: `detection_v14_P14/src/docling/`

1. **docling_figure_detector.py** (~7.8KB)
   - Figure detection using Docling
   - Visual content identification
   - Figure boundary detection

2. **docling_table_detector.py** (~4.5KB)
   - Table detection using Docling
   - Table boundary extraction
   - Markdown generation support

3. **docling_text_detector.py** (~5.5KB)
   - Text block detection using Docling
   - Layout analysis
   - Text region identification

**Priority**: P1 - Critical
**Reason**: Core detection for Docling-based extraction
**Dependencies**: Docling library, docling_agents_v14_P8

### Category 2: Unified Detection (2 components, ~15.5KB)

**Source**: `document_translator_v13/agents/detection/`
**Destination**: `detection_v14_P14/src/unified/`

1. **unified_detection_module.py** (~15KB)
   - Single-pass YOLO detection
   - Parallel detection (YOLO + Docling)
   - Zone pairing and deduplication
   - Multi-method detection orchestration

2. **__init__.py.original** (~441 bytes)
   - Original v13 package init
   - Preserved for reference

**Priority**: P1 - Critical
**Reason**: High-performance unified detection system
**Dependencies**: DocLayout-YOLO, PyMuPDF, Docling

## Migration Steps

### Step 1: Create Package Structure
1. Create `detection_v14_P14/` directory
2. Create `detection_v14_P14/__init__.py`
3. Create `detection_v14_P14/src/__init__.py`
4. Create category subdirectories with `__init__.py`:
   - `src/docling/__init__.py`
   - `src/unified/__init__.py`

### Step 2: Copy Components
1. Copy 3 files to docling/
2. Copy 2 files to unified/ (including __init__.py.original)

### Step 3: Create Validation Script
1. Create `tools/validate_phase15.py`
2. Validate all 5 components migrated
3. Report by category (docling/unified)

### Step 4: Documentation and Commit
1. Create `PHASE_15_COMPLETE_SUMMARY.md`
2. Commit to phase-15 branch
3. Merge to develop
4. Tag v14.0.0-phase15

## Known Challenges

### Import Path Dependencies

**Expected**: Detection agents likely have:
- Imports from docling_agents_v14_P8 (Docling integration)
- Imports from extraction_v14_P1 (zone data structures)
- DocLayout-YOLO model dependencies
- Old v13 import paths
- Potential sys.path manipulation

**Strategy**:
- Migrate first, update imports in follow-up
- Document YOLO model requirements
- Note parallel detection architecture

### External Dependencies

**DocLayout-YOLO**:
- Model file: doclayout_yolo_docstructbench_imgsz1280_2501.pt
- Pre-trained model download required
- GPU/CPU mode support

**Docling**:
- Docling library for Docling-based detectors
- Integration with docling_agents_v14_P8
- Parallel execution with YOLO

**PyMuPDF**:
- PDF page rendering for detection
- Zone coordinate system
- Bbox extraction

## Integration Points

### With Existing v14 Packages

**extraction_v14_P1**:
- Detection provides zones for extraction
- Core dependency for extraction pipeline
- Zone data structures and coordinate systems

**docling_agents_v14_P8**:
- Docling detectors use Docling integration
- Shared Docling infrastructure
- Parallel detection with YOLO

**extraction_comparison_v14_P12**:
- Unified detection supports multi-method comparison
- Detection quality metrics
- Method validation

## Success Metrics

- ✅ 5/5 components migrated (100% success rate)
- ✅ Proper package structure with __init__.py files
- ✅ Validation script confirms all components present
- ✅ Zero component loss from v13
- ✅ Documentation complete (summary + plan)
- ✅ Git workflow: branch → commit → merge → tag

## Post-Migration Progress

**After Phase 15**:
- Total components: 160/339 (47.2% complete)
- Packages: 14 specialized packages + common
- Remaining: 179 components (~52.8%)
- **Nearly 50% milestone!**

## Timeline Estimate

**Phase 15 Execution**: ~20-25 minutes
- Package structure: 5 minutes
- Component copying: 3 minutes (5 small files)
- __init__.py creation: 5 minutes
- Validation script: 5 minutes
- Documentation: 7 minutes
- Git workflow: 5 minutes

**Ready to proceed with user's blanket permission.**

---

**Status**: PLANNED
**Next Step**: Create phase-15 branch and begin migration
**Approval**: Covered by user's blanket permission to proceed
