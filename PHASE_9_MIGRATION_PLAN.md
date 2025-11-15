# Phase 9 Migration Plan: Docling Agents

**Target**: 5 components across 3 agent categories
**Package**: docling_agents_v14_P8
**Priority**: P1 (Important) - Docling integration agents
**Estimated Size**: ~192KB of code

## Migration Strategy

### Package Decision: Single Package for Docling Agents

**Recommendation**: Create **single package `docling_agents_v14_P8`** for all docling agents

**Rationale**:
1. **Cohesion**: All agents related to Docling library integration
2. **Size**: 5 components (~192KB) - manageable package
3. **Functionality**: Unified Docling-based extraction approach
4. **Integration**: All work with Docling document conversion

**Package Structure**:
```
docling_agents_v14_P8/
├── __init__.py
├── src/
│   ├── __init__.py
│   ├── core/              # 2 components - main docling agent
│   ├── first/             # 2 components - first-pass agent
│   └── roi/               # 1 component - region of interest agent
```

## Components to Migrate (5 components)

### Category 1: Core Docling Agent (2 components, ~24KB)

**Source**: `document_translator_v13/agents/docling_agent/`
**Destination**: `docling_agents_v14_P8/src/core/`

1. **agent.py** (~12KB estimated)
   - Main Docling integration agent
   - Document conversion orchestration
   - Docling library interface

2. **__init__.py** (small)
   - Package initialization
   - Exports for docling_agent

**Priority**: P1 - Important
**Reason**: Core Docling integration
**Dependencies**: Docling library, extraction framework

### Category 2: Docling First Agent (2 components, ~156KB)

**Source**: `document_translator_v13/agents/docling_first_agent/`
**Destination**: `docling_agents_v14_P8/src/first/`

1. **docling_first_agent.py** (~150KB estimated)
   - First-pass document processing
   - Initial Docling-based extraction
   - Comprehensive document analysis

2. **__init__.py** (small)
   - Package initialization
   - Exports for docling_first_agent

**Priority**: P1 - Important
**Reason**: Primary Docling processing agent
**Dependencies**: Docling library, extraction framework
**Note**: Large file suggests comprehensive functionality

### Category 3: Docling ROI Agent (1 component, ~12KB)

**Source**: `document_translator_v13/agents/docling_roi_agent/`
**Destination**: `docling_agents_v14_P8/src/roi/`

1. **agent.py** (~12KB estimated)
   - Region of Interest extraction
   - Targeted Docling processing
   - Focused area extraction

**Priority**: P1 - Important
**Reason**: Specialized ROI extraction
**Dependencies**: Docling library, extraction framework

## Migration Steps

### Step 1: Create Package Structure
1. Create `docling_agents_v14_P8/` directory
2. Create `docling_agents_v14_P8/__init__.py`
3. Create `docling_agents_v14_P8/src/__init__.py`
4. Create category subdirectories with `__init__.py`:
   - `src/core/__init__.py`
   - `src/first/__init__.py`
   - `src/roi/__init__.py`

### Step 2: Copy Components
1. Copy 2 files from docling_agent/ → core/
2. Copy 2 files from docling_first_agent/ → first/
3. Copy 1 file from docling_roi_agent/ → roi/

### Step 3: Create Validation Script
1. Create `tools/validate_phase9.py`
2. Validate all 5 components migrated
3. Report by category (core/first/roi)

### Step 4: Documentation and Commit
1. Create `PHASE_9_COMPLETE_SUMMARY.md`
2. Commit to phase-9 branch
3. Merge to develop
4. Tag v14.0.0-phase9

## Known Challenges

### Import Path Dependencies

**Expected**: Docling agents likely have:
- Imports from extraction_v14_P1 framework
- Docling library dependencies
- Old v13 import paths
- Potential sys.path manipulation

**Strategy**:
- Migrate first, update imports in follow-up
- Document Docling version dependencies

### Documentation Files

**Note**: docling_first_agent has extensive documentation:
- ARCHITECTURE.md
- README.md
- REQUIREMENTS.md
- CHANGELOG.md

**Decision**: Include documentation in migration
- Preserve valuable architectural documentation
- Keep requirements for reference
- Maintain changelog for history

## Integration Points

### With Existing v14 Packages

**extraction_v14_P1**:
- Docling agents provide alternative extraction method
- May integrate with or replace some extraction components
- Complementary to existing extraction pipeline

**All Pipelines**:
- Docling provides document conversion foundation
- May be used by multiple pipeline stages
- Core infrastructure for document processing

## Success Metrics

- ✅ 5/5 components migrated (100% success rate)
- ✅ Proper package structure with __init__.py files
- ✅ Validation script confirms all components present
- ✅ Zero component loss from v13
- ✅ Documentation complete (summary + plan)
- ✅ Git workflow: branch → commit → merge → tag

## Post-Migration Progress

**After Phase 9**:
- Total components: 122/339 (36.0% complete)
- Packages: 8 specialized packages + common
- Remaining: 217 components (~64%)

## Timeline Estimate

**Phase 9 Execution**: ~25-30 minutes
- Package structure: 5 minutes
- Component copying: 5 minutes (5 files + docs)
- __init__.py creation: 5 minutes
- Validation script: 5 minutes
- Documentation: 10 minutes
- Git workflow: 5 minutes

**Ready to proceed with user's blanket permission.**

---

**Status**: PLANNED
**Next Step**: Create phase-9 branch and begin migration
**Approval**: Covered by user's blanket permission to proceed
