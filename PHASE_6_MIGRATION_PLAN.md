# Phase 6 Migration Plan: Relationship Detection & Analysis

**Target**: 9 components across 4 categories
**Package**: relationship_detection_v14_P5
**Priority**: P1 (Important) - Advanced relationship extraction and analysis
**Estimated Size**: ~184KB of code

## Migration Strategy

### Package Decision: Single Package

**Recommendation**: Create **single package `relationship_detection_v14_P5`** for all 9 components

**Rationale**:
1. **Cohesion**: All components related to detecting and analyzing relationships between document elements
2. **Size**: 9 components (~184KB) - manageable for single package
3. **Dependencies**: Components are interdependent (citation/cross-reference detection, variable analysis)
4. **Integration**: All feed into relationship extraction pipeline (rag_v14_P2)

**Package Structure**:
```
relationship_detection_v14_P5/
├── __init__.py
├── src/
│   ├── __init__.py
│   ├── citations/        # 2 components - citation & cross-reference detection
│   ├── variables/        # 3 components - variable extraction, definition, matching
│   ├── dependencies/     # 2 components - data dependency & table analysis
│   └── generators/       # 1 component - lookup method generation
│   └── data_structures/  # 1 component - shared data structures
```

## Components to Migrate (9 total, ~184KB)

### Category 1: Citations & Cross-References (2 components, ~45KB)

**Source**: `document_translator_v13/detectors/`
**Destination**: `relationship_detection_v14_P5/src/citations/`

1. **citation_detector.py** (22KB)
   - Citation detection and extraction
   - Reference parsing
   - Citation graph construction

2. **cross_reference_detector.py** (23KB)
   - Cross-reference detection (equations, figures, tables)
   - Internal document linking
   - Reference validation

**Priority**: P1 - CRITICAL
**Reason**: Core relationship extraction for RAG pipeline
**Dependencies**: May depend on data_structures.py

### Category 2: Variable Analysis (3 components, ~86KB)

**Source**: `document_translator_v13/detectors/`
**Destination**: `relationship_detection_v14_P5/src/variables/`

1. **equation_variable_extractor.py** (18KB)
   - Extract variables from equations
   - Variable symbol parsing
   - Mathematical notation analysis

2. **variable_definition_detector.py** (53KB)
   - Detect variable definitions in text
   - Symbol-to-meaning mapping
   - Definition extraction from prose

3. **variable_matching_engine.py** (15KB)
   - Match variables across document
   - Symbol disambiguation
   - Cross-reference resolution

**Priority**: P1 - Important
**Reason**: Enables mathematical relationship understanding
**Dependencies**: Likely interdependent, may use data_structures.py

### Category 3: Dependency Analysis (2 components, ~34KB)

**Source**: `document_translator_v13/detectors/`
**Destination**: `relationship_detection_v14_P5/src/dependencies/`

1. **data_dependency_detector.py** (18KB)
   - Detect data flow dependencies
   - Input-output relationship analysis
   - Dependency graph construction

2. **table_column_analyzer.py** (16KB)
   - Analyze table column relationships
   - Column type detection
   - Inter-column dependencies

**Priority**: P1 - Important
**Reason**: Advanced data relationship detection
**Dependencies**: May depend on extraction_v14_P1 table components

### Category 4: Code Generation (1 component, ~12KB)

**Source**: `document_translator_v13/detectors/`
**Destination**: `relationship_detection_v14_P5/src/generators/`

1. **lookup_method_generator.py** (12KB)
   - Generate lookup methods for data access
   - Code generation utilities
   - API generation for extracted data

**Priority**: P2 - Optional (but included for completeness)
**Reason**: Utility for generating access methods
**Dependencies**: May depend on data_structures.py

### Category 5: Shared Utilities (1 component, ~9KB)

**Source**: `document_translator_v13/detectors/`
**Destination**: `relationship_detection_v14_P5/src/data_structures/`

1. **data_structures.py** (9.4KB)
   - Shared data models for detectors
   - Relationship representations
   - Common types and enums

**Priority**: P0 - CRITICAL (dependency for other components)
**Reason**: Shared foundation for all detector components
**Dependencies**: None (foundation component)

## Migration Steps

### Step 1: Create Package Structure
1. Create `relationship_detection_v14_P5/` directory
2. Create `relationship_detection_v14_P5/__init__.py` with package metadata
3. Create `relationship_detection_v14_P5/src/__init__.py` with category exports
4. Create category subdirectories with `__init__.py`:
   - `src/citations/__init__.py`
   - `src/variables/__init__.py`
   - `src/dependencies/__init__.py`
   - `src/generators/__init__.py`
   - `src/data_structures/__init__.py`

### Step 2: Copy Components (Order Matters!)
1. **First**: Copy data_structures.py (foundation)
2. **Then**: Copy remaining 8 components:
   - 2 citation components → citations/
   - 3 variable components → variables/
   - 2 dependency components → dependencies/
   - 1 generator component → generators/

### Step 3: Create Validation Script
1. Create `tools/validate_phase6.py`
2. Validate all 9 components migrated
3. Categorize by citations/variables/dependencies/generators/data_structures
4. Report total size and success rate

### Step 4: Documentation and Commit
1. Create `PHASE_6_COMPLETE_SUMMARY.md`
2. Commit to phase-6 branch with comprehensive message
3. Merge phase-6 → develop
4. Tag v14.0.0-phase6

## Known Challenges

### Import Path Dependencies

**Expected**: Detector components likely have:
- Imports from old v13 structure (needs updating)
- Potential sys.path manipulation (needs removal)
- Cross-dependencies within detectors/ (now in same package)
- Dependencies on extraction_v14_P1 components

**Strategy**:
- Migrate first, update imports in follow-up commit
- Stub unmigrated dependencies with TODO comments
- Document all import path issues for batch cleanup

### Test Files

**Note**: detectors/ has 8 test files (~156KB):
- test_citation_detector.py
- test_cross_reference_detector.py
- test_data_structures.py
- test_equation_variable_extractor.py
- test_lookup_method_generator.py
- test_table_column_analyzer.py
- test_variable_definition_detector.py
- manual_test_cross_reference.py

**Decision**: Skip test files in Phase 6
- Focus on production code migration
- Tests can be migrated in separate testing infrastructure phase
- Or integrated into tests/ directory later

### Interdependencies

**Potential Issues**:
- Variable extractor/detector/matcher are tightly coupled
- Citation and cross-reference detectors may share utilities
- All components likely depend on data_structures.py

**Mitigation**:
- Migrate data_structures.py first (foundation)
- Check imports during migration
- Document dependency chains

## Integration Points

### With Existing v14 Packages

**rag_v14_P2**:
- Relationship extraction feeds knowledge graph builder
- Citation detection enhances RAG context
- Variable matching improves semantic understanding

**extraction_v14_P1**:
- Depends on extracted equations, tables, figures
- Analyzes relationships between extracted objects
- Enhances extraction metadata

**semantic_processing_v14_P4**:
- Classification may use relationship patterns
- Coordination may orchestrate relationship detection
- Document structure influences relationship detection

## Success Metrics

- ✅ 9/9 components migrated (100% success rate)
- ✅ Proper package structure with __init__.py files
- ✅ Validation script confirms all components present
- ✅ Zero component loss from v13
- ✅ Documentation complete (summary + plan)
- ✅ Git workflow: branch → commit → merge → tag

## Post-Migration Progress

**After Phase 6**:
- Total components: 112/339 (33.0% complete)
- Pipelines:
  - extraction_v14_P1 (34 components)
  - rag_v14_P2 (37 components)
  - curation_v14_P3 (9 components)
  - semantic_processing_v14_P4 (7 components)
  - relationship_detection_v14_P5 (9 components)
- Common utilities: common/ (16 components)
- Remaining: 227 components (~67%)

## Next Phases (Tentative)

**Phase 7** - Database & Registry:
- database/ (3-4 components) - document registry, metadata extraction
- Persistent storage and document management

**Phase 8** - CLI & Tools:
- cli/ (1 component) - command line interface
- User-facing tools

**Phase 9+** - Agent Categories:
- ~40 agent subdirectories with specialized functions
- Likely mixture of P1/P2 priority components

**Import Cleanup Phase**:
- Batch update ~50+ files across Phases 2-6
- Remove all sys.path manipulation
- Update all v13 → v14 import paths
- Comprehensive validation with test runs

## Timeline Estimate

**Phase 6 Execution**: ~35-50 minutes
- Package structure: 5 minutes
- Component copying: 10 minutes (9 files)
- __init__.py creation: 10 minutes (5 files with exports)
- Validation script: 5 minutes
- Documentation: 10 minutes
- Git workflow: 5 minutes

**Ready to proceed with user's blanket permission.**

---

**Status**: PLANNED
**Next Step**: Create phase-6 branch and begin migration
**Approval**: Covered by user's blanket permission to proceed
