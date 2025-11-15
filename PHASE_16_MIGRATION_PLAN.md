# Phase 16 Migration Plan: Specialized Extraction Agents

**Target**: 10 components from 4 agent categories
**Package**: specialized_extraction_v14_P15
**Priority**: P1 (Critical) - Specialized extraction controllers and caption handling
**Estimated Size**: ~220KB of code

🎯 **50% MILESTONE ACHIEVEMENT**: This phase will reach 170/339 components (50.1%)!

## Migration Strategy

### Package Decision: Single Package for Specialized Extraction

**Recommendation**: Create **single package `specialized_extraction_v14_P15`** for specialized extraction agents

**Rationale**:
1. **Cohesion**: All agents perform specialized extraction tasks (objects, captions, coordination)
2. **Size**: 10 components (~220KB) - moderate, focused package
3. **Functionality**: Unified approach to extraction control and caption association
4. **Milestone**: Achieves 50% completion milestone! 🎯

**Package Structure**:
```
specialized_extraction_v14_P15/
├── __init__.py
├── src/
│   ├── __init__.py
│   ├── object_detection/     # 5 components - Object detection & controllers
│   ├── captions/             # 3 components - Caption extraction & association
│   ├── coordination/         # 1 component - Object numbering coordination
│   └── figures/              # 1 component - Figure extraction
```

## Components to Migrate (10 components)

### Category 1: Object Detection & Controllers (5 components, ~92KB)

**Source**: `document_translator_v13/agents/object_detector/`
**Destination**: `specialized_extraction_v14_P15/src/object_detection/`

1. **document_object_agent.py** (~23KB)
   - Document object classification
   - Multi-class object detection
   - PyTorch-based neural network

2. **object_extraction_controller.py** (~14KB)
   - Extraction pipeline orchestration
   - Object-based extraction control
   - Multi-agent coordination

3. **gemini_extraction_controller.py** (~12KB)
   - Gemini AI-powered extraction control
   - Vision-language model integration
   - Alternative extraction method

4. **mathematica_extraction_controller.py** (~11KB)
   - Mathematica-based extraction control
   - Computational notebook generation
   - Symbolic computation integration

5. **__init__.py.original** (~210 bytes)
   - Original v13 package init
   - Preserved for reference

**Priority**: P1 - Critical
**Reason**: Core extraction controllers for multi-method pipeline
**Dependencies**: PyTorch, Gemini API, Mathematica

### Category 2: Caption Extraction (3 components, ~76KB)

**Source**: `document_translator_v13/agents/caption_extraction/`
**Destination**: `specialized_extraction_v14_P15/src/captions/`

1. **caption_association_engine.py** (~15KB)
   - Caption-to-object association
   - Spatial proximity analysis
   - Caption linking algorithms

2. **equation_context_extractor.py** (~15KB)
   - Equation context extraction
   - Surrounding text analysis
   - Mathematical context linking

3. **table_caption_extractor.py** (~15KB)
   - Table caption detection
   - Caption text extraction
   - Table-caption pairing

**Priority**: P1 - Critical
**Reason**: Essential for complete object extraction with context
**Dependencies**: Text extraction, spatial analysis

### Category 3: Coordination (1 component, ~36KB)

**Source**: `document_translator_v13/agents/coordination/`
**Destination**: `specialized_extraction_v14_P15/src/coordination/`

1. **object_numbering_coordinator.py** (~12KB)
   - Object numbering coordination
   - Sequential numbering across document
   - Cross-reference resolution

**Priority**: P2 - Important
**Reason**: Ensures consistent object numbering
**Dependencies**: Object detection, extraction pipeline

### Category 4: Figure Extraction (1 component, ~8KB)

**Source**: `document_translator_v13/agents/figure_extractor/`
**Destination**: `specialized_extraction_v14_P15/src/figures/`

1. **__init__.py.original** (~1.1KB with code)
   - Figure extraction utilities
   - Original v13 implementation
   - Preserved for compatibility

**Priority**: P2 - Important
**Reason**: Figure extraction support
**Dependencies**: Image processing, detection

## Migration Steps

### Step 1: Create Package Structure
1. Create `specialized_extraction_v14_P15/` directory
2. Create `specialized_extraction_v14_P15/__init__.py`
3. Create `specialized_extraction_v14_P15/src/__init__.py`
4. Create category subdirectories with `__init__.py`:
   - `src/object_detection/__init__.py`
   - `src/captions/__init__.py`
   - `src/coordination/__init__.py`
   - `src/figures/__init__.py`

### Step 2: Copy Components
1. Copy 5 files to object_detection/
2. Copy 3 files to captions/
3. Copy 1 file to coordination/
4. Copy 1 file (__init__.py) to figures/

### Step 3: Create Validation Script
1. Create `tools/validate_phase16.py`
2. Validate all 10 components migrated
3. Report by category (object_detection/captions/coordination/figures)

### Step 4: Documentation and Commit
1. Create `PHASE_16_COMPLETE_SUMMARY.md`
2. Commit to phase-16 branch
3. Merge to develop
4. Tag v14.0.0-phase16

## Known Challenges

### Import Path Dependencies

**Expected**: Specialized extraction agents likely have:
- Imports from extraction_v14_P1 (extraction pipeline)
- Imports from detection_v14_P14 (object detection)
- PyTorch dependencies for neural networks
- External API dependencies (Gemini, Mathematica)
- Old v13 import paths
- Potential sys.path manipulation

**Strategy**:
- Migrate first, update imports in follow-up
- Document external API requirements
- Note PyTorch model dependencies

### External Dependencies

**Gemini API**:
- gemini_extraction_controller requires API key
- Vision-language model access
- Rate limiting considerations

**Mathematica**:
- mathematica_extraction_controller requires Mathematica installation
- Kernel integration
- Notebook generation capabilities

**PyTorch**:
- document_object_agent uses PyTorch models
- GPU/CPU mode support
- Model weight files

## Integration Points

### With Existing v14 Packages

**extraction_v14_P1**:
- Object detection feeds extraction pipeline
- Controllers orchestrate extraction workflows
- Caption association enriches extracted objects

**detection_v14_P14**:
- Object detection provides zones
- Caption extraction uses detection results
- Coordination ensures consistent numbering

**extraction_comparison_v14_P12**:
- Gemini and Mathematica controllers provide alternative methods
- Multi-method comparison validation
- Quality assessment across methods

**analysis_tools_v14_P9**:
- Mathematica controller integrates with analysis tools
- Computational notebook generation
- Symbolic computation

## Success Metrics

- ✅ 10/10 components migrated (100% success rate)
- ✅ Proper package structure with __init__.py files
- ✅ Validation script confirms all components present
- ✅ Zero component loss from v13
- ✅ Documentation complete (summary + plan)
- ✅ Git workflow: branch → commit → merge → tag
- 🎯 **50% MILESTONE ACHIEVED!** (170/339 components)

## Post-Migration Progress

**After Phase 16**:
- Total components: 170/339 (50.1% complete) 🎯 **50% MILESTONE!**
- Packages: 15 specialized packages + common
- Remaining: 169 components (~49.9%)
- **Major psychological milestone achieved!**

## Timeline Estimate

**Phase 16 Execution**: ~30-35 minutes
- Package structure: 5 minutes
- Component copying: 7 minutes (10 files)
- __init__.py creation: 5 minutes
- Validation script: 5 minutes
- Documentation: 10 minutes
- Git workflow: 5 minutes

**Ready to proceed with user's blanket authorization.**

---

**Status**: PLANNED
**Next Step**: Create phase-16 branch and begin migration
**Approval**: Covered by user's blanket authorization to proceed
**Milestone**: 🎯 **50% COMPLETION UPON SUCCESS!**
