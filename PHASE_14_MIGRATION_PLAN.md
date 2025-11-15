# Phase 14 Migration Plan: Metadata & Bibliographic Integration

**Target**: 9 components from 1 agent category
**Package**: metadata_v14_P13
**Priority**: P1 (Important) - Bibliographic data and citation management
**Estimated Size**: ~284KB of code

## Migration Strategy

### Package Decision: Single Package for Metadata

**Recommendation**: Create **single package `metadata_v14_P13`** for metadata and bibliographic integration

**Rationale**:
1. **Cohesion**: All agents handle bibliographic data, citations, and external integrations
2. **Size**: 9 components (~284KB) - moderate, focused package
3. **Functionality**: Unified approach to document metadata management
4. **Integration**: Support RAG and curation pipelines with rich metadata

**Package Structure**:
```
metadata_v14_P13/
├── __init__.py
├── src/
│   ├── __init__.py
│   ├── bibliography/          # 2 components - bibliography and citation
│   ├── metadata/              # 2 components - document metadata
│   ├── assessment/            # 1 component - impact assessment
│   ├── trl/                   # 1 component - TRL library
│   └── zotero/                # 3 components - Zotero integration
```

## Components to Migrate (9 components)

### Category 1: Bibliography & Citation (2 components, ~49KB)

**Source**: `document_translator_v13/agents/metadata/`
**Destination**: `metadata_v14_P13/src/bibliography/`

1. **bibliography_extraction_agent.py** (~21KB)
   - Bibliography section extraction
   - Reference parsing and structuring
   - BibTeX generation

2. **citation_graph_analyzer.py** (~28KB)
   - Citation network analysis
   - Reference relationship mapping
   - Citation impact metrics

**Priority**: P1 - Critical
**Reason**: Essential for academic document processing
**Dependencies**: Text extraction, graph analysis

### Category 2: Document Metadata (2 components, ~40KB)

**Source**: `document_translator_v13/agents/metadata/`
**Destination**: `metadata_v14_P13/src/metadata/`

1. **document_metadata_agent.py** (~19KB)
   - Basic document metadata extraction
   - Title, authors, abstract extraction
   - Metadata normalization

2. **enhanced_document_metadata_agent.py** (~21KB)
   - Enhanced metadata with ML enrichment
   - Cross-source metadata validation
   - Quality assessment

**Priority**: P1 - Critical
**Reason**: Core metadata for all documents
**Dependencies**: PDF parsing, text extraction

### Category 3: Impact Assessment (1 component, ~29KB)

**Source**: `document_translator_v13/agents/metadata/`
**Destination**: `metadata_v14_P13/src/assessment/`

1. **impact_assessment_agent.py** (~29KB)
   - Research impact metrics
   - Citation count analysis
   - H-index and impact factor tracking

**Priority**: P2 - Important
**Reason**: Valuable for research assessment
**Dependencies**: Citation data, external APIs

### Category 4: TRL Library (1 component, ~16KB)

**Source**: `document_translator_v13/agents/metadata/`
**Destination**: `metadata_v14_P13/src/trl/`

1. **trl_library_manager.py** (~16KB)
   - Technology Readiness Level tracking
   - Multi-source TRL reconciliation
   - Uncertainty quantification

**Priority**: P1 - Important
**Reason**: Critical for technology assessment
**Dependencies**: Standards data, consensus algorithms

### Category 5: Zotero Integration (3 components, ~66KB)

**Source**: `document_translator_v13/agents/metadata/`
**Destination**: `metadata_v14_P13/src/zotero/`

1. **zotero_integration_agent.py** (~25KB)
   - Zotero library API integration
   - Bibliographic data retrieval
   - Collection management

2. **zotero_working_copy_manager.py** (~20KB)
   - Session-based PDF isolation
   - Working copy management
   - Safe file operations

3. **__init__.py.original** (~392 bytes)
   - Original v13 package init
   - Preserved for reference

**Priority**: P1 - Critical
**Reason**: Primary source for document metadata
**Dependencies**: Zotero library, SQLite database

## Migration Steps

### Step 1: Create Package Structure
1. Create `metadata_v14_P13/` directory
2. Create `metadata_v14_P13/__init__.py`
3. Create `metadata_v14_P13/src/__init__.py`
4. Create category subdirectories with `__init__.py`:
   - `src/bibliography/__init__.py`
   - `src/metadata/__init__.py`
   - `src/assessment/__init__.py`
   - `src/trl/__init__.py`
   - `src/zotero/__init__.py`

### Step 2: Copy Components
1. Copy 2 files to bibliography/
2. Copy 2 files to metadata/
3. Copy 1 file to assessment/
4. Copy 1 file to trl/
5. Copy 3 files (including __init__.py.original) to zotero/

### Step 3: Create Validation Script
1. Create `tools/validate_phase14.py`
2. Validate all 9 components migrated
3. Report by category (bibliography/metadata/assessment/trl/zotero)

### Step 4: Documentation and Commit
1. Create `PHASE_14_COMPLETE_SUMMARY.md`
2. Commit to phase-14 branch
3. Merge to develop
4. Tag v14.0.0-phase14

## Known Challenges

### Import Path Dependencies

**Expected**: Metadata agents likely have:
- Imports from database_v14_P6 (document registry)
- Imports from extraction_v14_P1 (text extraction)
- Imports from rag_v14_P2 (graph analysis)
- External API dependencies (Zotero, CrossRef, OpenAlex)
- Old v13 import paths
- Potential sys.path manipulation

**Strategy**:
- Migrate first, update imports in follow-up
- Document external API requirements
- Note Zotero database access requirements

### External Dependencies

**Zotero**:
- Requires Zotero library installation
- SQLite database access (read-only via .bak file)
- Zotero API for web access

**CrossRef/OpenAlex**:
- DOI resolution services
- Metadata enrichment APIs
- Rate limiting considerations

**TRL Standards**:
- IEA/IEAGHG reports
- DOE NETL data
- Academic consensus data

## Integration Points

### With Existing v14 Packages

**database_v14_P6**:
- Store metadata in document registry
- Link documents to bibliographic data
- Persistent metadata storage

**extraction_v14_P1**:
- Extract text for title/abstract detection
- Parse PDF metadata
- Bibliography section identification

**rag_v14_P2**:
- Citation graphs for knowledge graphs
- Reference relationships for retrieval
- Metadata enrichment for embeddings

**curation_v14_P3**:
- Metadata quality validation
- Deduplication based on DOI/title
- Database population

## Success Metrics

- ✅ 9/9 components migrated (100% success rate)
- ✅ Proper package structure with __init__.py files
- ✅ Validation script confirms all components present
- ✅ Zero component loss from v13
- ✅ Documentation complete (summary + plan)
- ✅ Git workflow: branch → commit → merge → tag

## Post-Migration Progress

**After Phase 14**:
- Total components: 155/339 (45.7% complete)
- Packages: 13 specialized packages + common
- Remaining: 184 components (~54.3%)
- **45% milestone achieved!**

## Timeline Estimate

**Phase 14 Execution**: ~25-30 minutes
- Package structure: 5 minutes
- Component copying: 5 minutes (9 files)
- __init__.py creation: 5 minutes
- Validation script: 5 minutes
- Documentation: 10 minutes
- Git workflow: 5 minutes

**Ready to proceed with user's blanket permission.**

---

**Status**: PLANNED
**Next Step**: Create phase-14 branch and begin migration
**Approval**: Covered by user's blanket permission to proceed
