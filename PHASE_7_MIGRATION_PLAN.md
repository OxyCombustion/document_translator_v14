# Phase 7 Migration Plan: Database & Registry

**Target**: 4 components + 1 schema file
**Package**: database_v14_P6
**Priority**: P1 (Important) - Persistent storage and document management
**Estimated Size**: ~57KB of code + database schema

## Migration Strategy

### Package Decision: Single Package

**Recommendation**: Create **single package `database_v14_P6`** for all database components

**Rationale**:
1. **Cohesion**: All components related to persistent storage and document registry
2. **Size**: 4 components (~57KB) - small, focused package
3. **Dependencies**: Components work together for document management
4. **Integration**: Central registry for all extracted documents

**Package Structure**:
```
database_v14_P6/
├── __init__.py
├── src/
│   ├── __init__.py
│   ├── registry/          # 2 components - document registry core
│   ├── organization/      # 1 component - directory organization
│   ├── extraction/        # 1 component - metadata extraction
│   └── schema/            # 1 file - database schema SQL
```

## Components to Migrate (4 Python files + 1 SQL schema)

### Category 1: Document Registry (2 components, ~37KB)

**Source**: `document_translator_v13/database/`
**Destination**: `database_v14_P6/src/registry/`

1. **document_registry.py** (23,658 bytes)
   - Core document registry implementation
   - Document tracking and indexing
   - Metadata storage and retrieval
   - SQLite database operations

2. **migrate_chapter4_to_registry.py** (12,618 bytes)
   - Migration utilities for existing data
   - Batch import functionality
   - Registry population tools
   - Data validation during migration

**Priority**: P0 - CRITICAL
**Reason**: Core document management infrastructure
**Dependencies**: Likely uses schema.sql, metadata_extractor.py

### Category 2: Directory Organization (1 component, ~11KB)

**Source**: `document_translator_v13/database/`
**Destination**: `database_v14_P6/src/organization/`

1. **directory_organizer.py** (11,095 bytes)
   - File system organization utilities
   - Directory structure management
   - Path standardization
   - Output organization

**Priority**: P1 - Important
**Reason**: Maintains clean file system structure
**Dependencies**: May work with document_registry.py

### Category 3: Metadata Extraction (1 component, ~10KB)

**Source**: `document_translator_v13/database/`
**Destination**: `database_v14_P6/src/extraction/`

1. **metadata_extractor.py** (9,529 bytes)
   - Document metadata extraction
   - Bibliographic data extraction
   - Metadata normalization
   - Enrichment from external sources

**Priority**: P1 - Important
**Reason**: Populates registry with rich metadata
**Dependencies**: Feeds into document_registry.py

### Category 4: Database Schema (1 file, ~15KB)

**Source**: `document_translator_v13/database/`
**Destination**: `database_v14_P6/src/schema/`

1. **schema.sql** (14,507 bytes)
   - SQLite database schema definition
   - Table structures
   - Indexes and constraints
   - Database initialization

**Priority**: P0 - CRITICAL
**Reason**: Foundation for all database operations
**Dependencies**: None (defines structure)

## Migration Steps

### Step 1: Create Package Structure
1. Create `database_v14_P6/` directory
2. Create `database_v14_P6/__init__.py` with package metadata
3. Create `database_v14_P6/src/__init__.py` with category exports
4. Create category subdirectories with `__init__.py`:
   - `src/registry/__init__.py`
   - `src/organization/__init__.py`
   - `src/extraction/__init__.py`
   - `src/schema/__init__.py`

### Step 2: Copy Components (Order Matters!)
1. **First**: Copy schema.sql (foundation)
2. **Then**: Copy remaining 4 Python components:
   - 2 registry components → registry/
   - 1 organization component → organization/
   - 1 extraction component → extraction/

### Step 3: Create Validation Script
1. Create `tools/validate_phase7.py`
2. Validate all 4 Python components + 1 SQL file migrated
3. Categorize by registry/organization/extraction/schema
4. Report total size and success rate

### Step 4: Documentation and Commit
1. Create `PHASE_7_COMPLETE_SUMMARY.md`
2. Commit to phase-7 branch with comprehensive message
3. Merge phase-7 → develop
4. Tag v14.0.0-phase7

## Known Challenges

### Import Path Dependencies

**Expected**: Database components likely have:
- Imports from old v13 structure (needs updating)
- Potential sys.path manipulation (needs removal)
- Dependencies on extraction_v14_P1 for extracted objects
- Dependencies on curation_v14_P3 for metadata

**Strategy**:
- Migrate first, update imports in follow-up commit
- Document all import path issues for batch cleanup

### Schema File Handling

**Note**: schema.sql is not a Python file
- No import path issues
- Should be accessible as package resource
- May need special handling in __init__.py

**Decision**: Include in src/schema/ directory as data file

### Migration Script Classification

**Question**: Is migrate_chapter4_to_registry.py production code or one-off script?

**Decision**: Include in migration
- May be useful for future data imports
- Documents migration patterns
- Can be kept in registry/ as utility

## Integration Points

### With Existing v14 Packages

**extraction_v14_P1**:
- Registry stores references to all extracted objects
- Metadata extractor may depend on extraction results
- Directory organizer manages extraction output

**rag_v14_P2**:
- Registry tracks which documents have RAG preparation
- Metadata enriches RAG context
- Organization helps locate RAG outputs

**curation_v14_P3**:
- Registry stores curated document metadata
- Metadata extraction feeds curation pipeline
- Quality metrics stored in registry

**All Pipelines**:
- Central registry for all document processing state
- Metadata tracking across entire pipeline
- Directory organization for all outputs

## Success Metrics

- ✅ 4/4 Python components migrated (100% success rate)
- ✅ 1/1 schema file migrated
- ✅ Proper package structure with __init__.py files
- ✅ Validation script confirms all components present
- ✅ Zero component loss from v13
- ✅ Documentation complete (summary + plan)
- ✅ Git workflow: branch → commit → merge → tag

## Post-Migration Progress

**After Phase 7**:
- Total components: 116/339 (34.2% complete)
- Pipelines:
  - extraction_v14_P1 (34 components)
  - rag_v14_P2 (37 components)
  - curation_v14_P3 (9 components)
  - semantic_processing_v14_P4 (7 components)
  - relationship_detection_v14_P5 (9 components)
  - database_v14_P6 (4 components)
- Common utilities: common/ (16 components)
- Remaining: 223 components (~66%)

## Next Phases (Tentative)

**Phase 8** - CLI & Tools:
- cli/ (1-2 components) - command line interface
- User-facing document management tools

**Phase 9+** - Agent Categories:
- ~40 agent subdirectories with specialized functions
- Likely mixture of P1/P2 priority components
- Largest remaining migration effort

**Import Cleanup Phase**:
- Batch update ~55+ files across Phases 2-7
- Remove all sys.path manipulation
- Update all v13 → v14 import paths
- Comprehensive validation with test runs

## Timeline Estimate

**Phase 7 Execution**: ~30-40 minutes
- Package structure: 5 minutes
- Component copying: 5 minutes (4 Python files + 1 SQL)
- __init__.py creation: 10 minutes (4 files with exports)
- Validation script: 5 minutes
- Documentation: 10 minutes
- Git workflow: 5 minutes

**Ready to proceed with user's blanket permission.**

---

**Status**: PLANNED
**Next Step**: Create phase-7 branch and begin migration
**Approval**: Covered by user's blanket permission to proceed
