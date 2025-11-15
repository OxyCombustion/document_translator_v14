# Phase 17 Migration Plan: RAG Extraction Agents

**Target**: 8 components from 1 agent category
**Package**: rag_extraction_v14_P16
**Priority**: P1 (Critical) - RAG-specific extraction agents for document assembly
**Estimated Size**: ~252KB of code

## Migration Strategy

### Package Decision: Single Package for RAG Extraction

**Recommendation**: Create **single package `rag_extraction_v14_P16`** for RAG extraction agents

**Rationale**:
1. **Cohesion**: All agents perform RAG-specific extraction tasks
2. **Size**: 8 components (~144KB) - substantial, focused package
3. **Functionality**: Unified approach to extraction for RAG pipeline
4. **Integration**: Direct support for rag_v14_P2 RAG preparation pipeline

**Package Structure**:
```
rag_extraction_v14_P16/
├── __init__.py
├── src/
│   ├── __init__.py
│   ├── citations/            # 1 component - Citation extraction
│   ├── assembly/             # 2 components - Document assembly (basic + enhanced)
│   ├── equations/            # 1 component - Equation extraction
│   ├── figures/              # 2 components - Figure extraction (basic + enhanced)
│   ├── tables/               # 1 component - Table extraction
│   └── text/                 # 1 component - Text extraction
```

## Components to Migrate (8 components)

### Category 1: Citation Extraction (1 component, ~18KB)

**Source**: `document_translator_v13/agents/rag_extraction/`
**Destination**: `rag_extraction_v14_P16/src/citations/`

1. **citation_extraction_agent.py** (~18KB)
   - Citation extraction for RAG
   - Reference parsing and linking
   - Bibliographic data extraction

**Priority**: P1 - Critical
**Reason**: Essential for RAG knowledge graph construction
**Dependencies**: Text extraction, metadata

### Category 2: Document Assembly (2 components, ~36KB)

**Source**: `document_translator_v13/agents/rag_extraction/`
**Destination**: `rag_extraction_v14_P16/src/assembly/`

1. **document_assembly_agent.py** (~16KB)
   - Basic document assembly for RAG
   - Object aggregation and linking
   - Document package creation

2. **document_assembly_agent_enhanced.py** (~20KB)
   - Enhanced assembly with ML enrichment
   - Advanced linking and validation
   - Quality assessment

**Priority**: P1 - Critical
**Reason**: Core assembly for RAG pipeline
**Dependencies**: All extraction agents

### Category 3: Equation Extraction (1 component, ~25KB)

**Source**: `document_translator_v13/agents/rag_extraction/`
**Destination**: `rag_extraction_v14_P16/src/equations/`

1. **equation_extraction_agent.py** (~25KB)
   - Equation extraction for RAG
   - LaTeX generation
   - Mathematical context preservation

**Priority**: P1 - Critical
**Reason**: Mathematical content for RAG
**Dependencies**: Detection, LaTeX-OCR

### Category 4: Figure Extraction (2 components, ~29KB)

**Source**: `document_translator_v13/agents/rag_extraction/`
**Destination**: `rag_extraction_v14_P16/src/figures/`

1. **figure_extraction_agent.py** (~16KB)
   - Basic figure extraction for RAG
   - Image extraction and metadata
   - Caption association

2. **figure_extraction_agent_enhanced.py** (~13KB)
   - Enhanced figure extraction
   - Advanced image processing
   - Quality validation

**Priority**: P1 - Critical
**Reason**: Visual content for RAG
**Dependencies**: Detection, image processing

### Category 5: Table Extraction (1 component, ~30KB)

**Source**: `document_translator_v13/agents/rag_extraction/`
**Destination**: `rag_extraction_v14_P16/src/tables/`

1. **table_extraction_agent.py** (~30KB)
   - Table extraction for RAG
   - Structured data extraction
   - Multi-format export

**Priority**: P1 - Critical
**Reason**: Structured data for RAG
**Dependencies**: Detection, Docling

### Category 6: Text Extraction (1 component, ~6KB)

**Source**: `document_translator_v13/agents/rag_extraction/`
**Destination**: `rag_extraction_v14_P16/src/text/`

1. **text_extraction_agent.py** (~6KB)
   - Text extraction for RAG
   - Semantic chunking
   - Context preservation

**Priority**: P1 - Critical
**Reason**: Text content for RAG embeddings
**Dependencies**: Text parsing, chunking

## Migration Steps

### Step 1: Create Package Structure
1. Create `rag_extraction_v14_P16/` directory
2. Create `rag_extraction_v14_P16/__init__.py`
3. Create `rag_extraction_v14_P16/src/__init__.py`
4. Create category subdirectories with `__init__.py`:
   - `src/citations/__init__.py`
   - `src/assembly/__init__.py`
   - `src/equations/__init__.py`
   - `src/figures/__init__.py`
   - `src/tables/__init__.py`
   - `src/text/__init__.py`

### Step 2: Copy Components
1. Copy 1 file to citations/
2. Copy 2 files to assembly/
3. Copy 1 file to equations/
4. Copy 2 files to figures/
5. Copy 1 file to tables/
6. Copy 1 file to text/

### Step 3: Create Validation Script
1. Create `tools/validate_phase17.py`
2. Validate all 8 components migrated
3. Report by category (citations/assembly/equations/figures/tables/text)

### Step 4: Documentation and Commit
1. Create `PHASE_17_COMPLETE_SUMMARY.md`
2. Commit to phase-17 branch
3. Merge to develop
4. Tag v14.0.0-phase17

## Known Challenges

### Import Path Dependencies

**Expected**: RAG extraction agents likely have:
- Imports from rag_v14_P2 (RAG preparation pipeline)
- Imports from extraction_v14_P1 (extraction utilities)
- Imports from detection_v14_P14 (detection zones)
- Old v13 import paths
- Potential sys.path manipulation

**Strategy**:
- Migrate first, update imports in follow-up
- Document RAG pipeline integration requirements
- Note chunking and embedding dependencies

### Integration Complexity

**RAG Pipeline**:
- These agents specifically designed for RAG workflow
- Integration with rag_v14_P2 is critical
- Embedding generation dependencies
- Vector database requirements

## Integration Points

### With Existing v14 Packages

**rag_v14_P2**:
- Primary integration point - RAG preparation pipeline
- JSONL generation for embeddings
- Knowledge graph construction
- Vector database population

**extraction_v14_P1**:
- Extraction utilities and base classes
- Zone data structures
- Coordinate systems

**detection_v14_P14**:
- Detection zones for extraction
- Bounding box coordinates
- Multi-method detection results

**metadata_v14_P13**:
- Citation data for knowledge graph
- Bibliographic enrichment
- Document metadata

## Success Metrics

- ✅ 8/8 components migrated (100% success rate)
- ✅ Proper package structure with __init__.py files
- ✅ Validation script confirms all components present
- ✅ Zero component loss from v13
- ✅ Documentation complete (summary + plan)
- ✅ Git workflow: branch → commit → merge → tag

## Post-Migration Progress

**After Phase 17**:
- Total components: 178/339 (52.5% complete)
- Packages: 16 specialized packages + common
- Remaining: 161 components (~47.5%)
- **Continuing strong momentum in second half!**

## Timeline Estimate

**Phase 17 Execution**: ~30-35 minutes
- Package structure: 5 minutes
- Component copying: 7 minutes (8 files)
- __init__.py creation: 7 minutes (6 categories)
- Validation script: 5 minutes
- Documentation: 10 minutes
- Git workflow: 5 minutes

**Ready to proceed with user's blanket authorization.**

---

**Status**: PLANNED
**Next Step**: Create phase-17 branch and begin migration
**Approval**: Covered by user's blanket authorization to proceed
**Context**: Second half of migration - building on 50% milestone success
