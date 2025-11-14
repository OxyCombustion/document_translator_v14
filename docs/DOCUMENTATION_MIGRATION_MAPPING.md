# Documentation Migration Mapping: v13 → v14

**Purpose**: Map all v13 documentation to v14 three-pipeline architecture
**Date**: 2025-11-14
**Source**: v13 documentation files (187 markdown files)
**Destination**: v14 docs/ organized by category and pipeline

---

## 📊 Documentation Overview

### **v13 Documentation Files**

| Category | Count | v14 Destination | Status |
|----------|-------|-----------------|--------|
| Session summaries | ~50 | `docs/historical/sessions/` | ✅ Mapped |
| Architecture docs | ~40 | `docs/architecture/` + pipeline docs | ✅ Mapped |
| Implementation guides | ~30 | Pipeline-specific `docs/` | ✅ Mapped |
| API references | ~20 | Pipeline-specific `docs/api/` | ✅ Mapped |
| Migration/phase docs | ~15 | `docs/migration/` | ✅ Mapped |
| Standards/principles | ~10 | `docs/standards/` | ✅ Mapped |
| Other docs | ~22 | Various | ✅ Mapped |
| **Total** | **187** | **v14 docs/** | **✅** |

---

## 🗺️ Documentation Migration Strategy

### **1. Historical Documentation** → `docs/historical/`

**Purpose**: Preserve development history without cluttering current docs

**v13 Session Summaries** (Archive):
```
docs/historical/sessions/
├── 2025-01-15_PIPELINE_RUN_COMPLETE.md
├── 2025-01-15_DOCLING_INVESTIGATION_COMPLETE.md
├── 2025-01-16_UNIFIED_PIPELINE_COMPLETE.md
├── 2025-10-06_GENERIC_EQUATION_EXTRACTION.md
├── 2025-10-07_TABLE_LAYOUT_CORRECTIONS.md
├── 2025-10-08_ARCHITECTURAL_INTEGRATION.md
├── 2025-10-09_EQUATION_CLASSIFICATION.md
├── 2025-10-09_FIGURE_RECLASSIFICATION.md
├── 2025-10-11_MULTI_DOMAIN_SYMBOL_LIBRARY.md
├── 2025-10-11_STANDARDS_IMPORT_SESSION.md
├── 2025-10-17_EQUATION_EXTRACTION_QUALITY.md
├── 2025-11-12_GPU_SETUP_AND_EXTRACTION.md
├── 2025-11-12_GPU_SETUP_AND_RAG.md
├── 2025-11-12_LOCAL_LLM_INTEGRATION.md
└── 2025-11-13_GPU_RAG_AND_NOVELTY.md
```

**Migration Rule**: All `SESSION_*.md` files → `docs/historical/sessions/` (read-only archive)

---

### **2. Current Architecture** → `docs/architecture/`

**Purpose**: Maintain architectural documentation for reference

**v13 Architecture Docs** (Migrate & Update):
```
docs/architecture/
├── three_pipeline_architecture.md              # NEW: v14 architecture overview
├── extraction_pipeline_architecture.md         # From UNIFIED_PIPELINE_ARCHITECTURE.md
├── rag_preparation_architecture.md             # NEW: v14 RAG pipeline
├── curation_pipeline_architecture.md           # NEW: v14 curation pipeline
├── agent_architecture_patterns.md              # From AGENT_ARCHITECTURE_PATTERNS.md
├── quality_first_architecture.md               # From QUALITY_FIRST_ARCHITECTURE_SUMMARY.md
├── ai_ready_extraction.md                      # From AI_READY_EXTRACTION_ARCHITECTURE.md
├── zotero_integration.md                       # From ZOTERO_INTEGRATION_ARCHITECTURE.md
├── context_aware_extraction.md                 # From CONTEXT_AWARE_EXTRACTION_ARCHITECTURE.md
├── output_management.md                        # From OUTPUT_MANAGEMENT_ARCHITECTURE.md
└── legacy/                                     # Archive old architecture docs
    ├── V10_FIGURE_EXTRACTION_ARCHITECTURE.md
    ├── DOCLING_TECHNICAL_ARCHITECTURE_ANALYSIS.md
    └── PERSISTENT_WORKER_ARCHITECTURE.md
```

**Migration Rule**: Update architecture docs to reflect v14 three-pipeline structure

---

### **3. Pipeline-Specific Documentation** → Pipeline `docs/`

**Purpose**: Keep pipeline documentation co-located with code

#### **extraction_v14_P1/docs/**
```
extraction_v14_P1/docs/
├── README.md                                   # Pipeline overview (already created)
├── detection_methods.md                        # Detection strategies
├── extraction_methods.md                       # Extraction algorithms
├── schema_reference.md                         # Output schema docs
├── guides/
│   ├── equation_extraction_guide.md            # From v13 guides
│   ├── table_extraction_guide.md               # TABLE_EXTRACTION_PIPELINE_GUIDE.md
│   ├── figure_extraction_guide.md              # FIGURE_EXTRACTION_SUMMARY.md
│   └── text_extraction_guide.md                # From v13 text extraction docs
├── api/
│   ├── detection_api.md                        # API reference
│   ├── extraction_api.md                       # API reference
│   └── validation_api.md                       # API reference
└── migration_notes.md                          # v13→v14 extraction migration
```

#### **rag_v14_P2/docs/**
```
rag_v14_P2/docs/
├── README.md                                   # Pipeline overview (already created)
├── intelligence_analysis.md                    # Intelligence analyzers
├── relationship_mapping.md                     # Relationship extraction
├── semantic_chunking.md                        # SEMANTIC_CHUNKING_USAGE_GUIDE.md
├── knowledge_graph.md                          # Knowledge graph construction
├── guides/
│   ├── orchestration_guide.md                  # Document scanning & orchestration
│   ├── analysis_guide.md                       # Intelligence analysis guide
│   ├── chunking_guide.md                       # Semantic chunking guide
│   └── relationship_guide.md                   # Relationship mapping guide
├── api/
│   ├── orchestration_api.md                    # API reference
│   ├── analyzers_api.md                        # API reference
│   ├── processors_api.md                       # API reference
│   └── semantic_chunking_api.md                # SEMANTIC_CHUNKING_API_REFERENCE.md
└── migration_notes.md                          # v13→v14 RAG migration
```

#### **curation_v14_P3/docs/**
```
curation_v14_P3/docs/
├── README.md                                   # Pipeline overview (already created)
├── calibration_methodology.md                  # LLM calibration methods
├── validation_criteria.md                      # Domain validation rules
├── novelty_detection.md                        # Training date versioning
├── local_llm_economics.md                      # Cost analysis & strategy
├── guides/
│   ├── calibration_guide.md                    # How to calibrate LLM
│   ├── validation_guide.md                     # How to validate domain
│   ├── metadata_guide.md                       # Metadata extraction
│   └── curation_workflow.md                    # End-to-end curation
├── api/
│   ├── calibration_api.md                      # API reference
│   ├── validation_api.md                       # API reference
│   └── database_api.md                         # API reference
└── migration_notes.md                          # v13→v14 curation migration
```

---

### **4. Common Documentation** → `common/docs/`

**Purpose**: Shared utilities documentation

```
common/docs/
├── README.md                                   # Common utilities overview (already created)
├── base_classes.md                             # Base class documentation
├── interfaces.md                               # Interface documentation
├── utilities.md                                # Utility function reference
├── type_definitions.md                         # Type system documentation
└── api/
    ├── base_classes_api.md                     # API reference
    ├── interfaces_api.md                       # API reference
    └── utilities_api.md                        # API reference
```

---

### **5. Standards & Principles** → `docs/standards/`

**Purpose**: Preserve engineering standards and principles

```
docs/standards/
├── V12_PYTHON_STANDARDS.md                     # Python coding standards
├── SOFTWARE_ENGINEERING_ASSESSMENT.md          # Engineering requirements
├── INCREMENTAL_DEVELOPMENT_PRINCIPLE.md        # Development methodology
├── ACCURACY_FIRST_PRINCIPLE.md                 # Quality-first approach
├── MANDATORY_AGENT_DELEGATION_CHECKLIST.md     # Agent delegation rules
├── PRE_FLIGHT_CHECKLIST.md                     # Pre-coding checklist
└── STANDARDS_COMPLIANCE_AUDIT_2025-10-23.md    # Compliance audit
```

**Migration Rule**: Copy as-is (these are v-agnostic standards)

---

### **6. Migration Documentation** → `docs/migration/`

**Purpose**: Track all migration efforts and decisions

```
docs/migration/
├── v13_to_v14/
│   ├── MIGRATION_PLAN.md                       # V13_TO_V14_MIGRATION_PLAN.md
│   ├── EXECUTIVE_SUMMARY.md                    # MIGRATION_PLAN_EXECUTIVE_SUMMARY.md
│   ├── COMPONENT_MAPPING.md                    # COMPONENT_MIGRATION_MAPPING.md
│   ├── DETAILED_COMPONENT_MAPPING.md           # DETAILED_V13_COMPONENT_MAPPING.md
│   ├── CONFIGURATION_MAPPING.md                # CONFIGURATION_MIGRATION_MAPPING.md
│   ├── DOCUMENTATION_MAPPING.md                # This file
│   ├── PHASE_0_CRITICAL_FINDINGS.md            # Critical discovery summary
│   ├── PHASE_0_PROGRESS_SUMMARY.md             # Phase 0 session summary
│   ├── HISTORICAL_COMPONENT_ANALYSIS.md        # v12→v13 comparison
│   └── V13_COMPONENT_AUDIT.md                  # Complete v13 inventory
├── v12_to_v13/
│   └── ARCHIVED_MIGRATION_DOCS.md              # Historical reference
└── future/
    └── v14_to_v15_PLAN_TEMPLATE.md             # Template for next migration
```

---

### **7. Implementation & Session Docs** → `docs/implementation/`

**Purpose**: Implementation details and session notes

```
docs/implementation/
├── completed/                                  # Completed implementations
│   ├── SEMANTIC_CHUNKING_IMPLEMENTATION.md
│   ├── SYMBOL_LIBRARY_IMPLEMENTATION.md
│   ├── TRL_LIBRARY_IMPLEMENTATION.md
│   ├── UNIFIED_PIPELINE_IMPLEMENTATION.md
│   ├── CAPTION_CITATION_IMPLEMENTATION.md
│   ├── EQUATION_EXTRACTION_IMPLEMENTATION.md
│   ├── TABLE_EXTRACTION_IMPLEMENTATION.md
│   └── FIGURE_EXTRACTION_IMPLEMENTATION.md
├── in_progress/                                # Current work
│   └── (none - v13 frozen, v14 starting)
└── planned/                                    # Future implementations
    └── (from v14 Phase 1-6 plan)
```

---

### **8. Guides & Tutorials** → `docs/guides/`

**Purpose**: User-facing guides and tutorials

```
docs/guides/
├── getting_started.md                          # NEW: v14 quick start
├── installation.md                             # NEW: v14 installation
├── configuration.md                            # Configuration guide
├── pipeline_usage.md                           # How to use each pipeline
├── end_to_end_workflow.md                      # Complete workflow
├── troubleshooting.md                          # Common issues
└── advanced/
    ├── parallel_processing.md                  # Multi-core optimization
    ├── custom_agents.md                        # Building custom agents
    └── performance_tuning.md                   # Performance optimization
```

---

### **9. API References** → `docs/api/`

**Purpose**: Complete API documentation

```
docs/api/
├── extraction_pipeline_api.md                  # extraction_v14_P1 API
├── rag_pipeline_api.md                         # rag_v14_P2 API
├── curation_pipeline_api.md                    # curation_v14_P3 API
├── common_utilities_api.md                     # common/ API
└── schemas/
    ├── extraction_results_v1.md                # extraction_v14_P1 output
    ├── rag_bundles_v1.md                       # rag_v14_P2 output
    └── knowledge_graph_v1.md                   # curation_v14_P3 output
```

---

## 📋 Documentation Migration Priority

### **P0 (Critical) - Week 1**
Must be migrated for minimum viable v14:
- Pipeline READMEs (already created ✅)
- Migration plan docs (already created ✅)
- Standards & principles → `docs/standards/`
- Critical guides (installation, getting started)

### **P1 (Important) - Weeks 2-3**
Required for full functionality:
- Architecture docs → `docs/architecture/`
- Pipeline-specific guides → Each pipeline `docs/guides/`
- API references → Each pipeline `docs/api/`
- Implementation summaries → `docs/implementation/completed/`

### **P2 (Optional) - Weeks 4-5**
Nice to have:
- Historical sessions → `docs/historical/sessions/`
- Advanced guides → `docs/guides/advanced/`
- Legacy architecture → `docs/architecture/legacy/`

---

## 🔍 Documentation Quality Standards

### **All Documentation Must Include**

1. **Header Section**:
   ```markdown
   # Document Title

   **Version**: v14
   **Pipeline**: extraction_v14_P1 | rag_v14_P2 | curation_v14_P3 | common
   **Last Updated**: YYYY-MM-DD
   **Status**: Draft | Review | Complete
   ```

2. **Table of Contents** (for docs >200 lines):
   ```markdown
   ## Table of Contents
   - [Overview](#overview)
   - [Architecture](#architecture)
   - [Usage](#usage)
   - [API Reference](#api-reference)
   - [Examples](#examples)
   ```

3. **Code Examples**:
   - Must be executable (with proper imports)
   - Include expected output
   - Show both success and error handling

4. **Cross-References**:
   - Link to related docs
   - Link to API references
   - Link to configuration files

5. **Version History**:
   ```markdown
   ## Version History
   - v14.0.0 (2025-11-14): Initial v14 documentation
   - v13.0.0 (2025-01-15): (migrated from v13)
   ```

---

## 🔄 Documentation Update Process

### **When to Update Documentation**

1. **Code Changes**: Update API docs when function signatures change
2. **Config Changes**: Update config docs when parameters change
3. **Architecture Changes**: Update architecture docs when structure changes
4. **Bug Fixes**: Update troubleshooting guides
5. **New Features**: Add guides and API docs

### **Documentation Review Checklist**

- [ ] Accurate (reflects current code)
- [ ] Complete (all parameters documented)
- [ ] Clear (easy to understand)
- [ ] Examples (working code samples)
- [ ] Links (all cross-references work)
- [ ] Version (updated version history)
- [ ] Format (markdown lint clean)

---

## 📊 Documentation Migration Checklist

### **Phase 0.10 Tasks**

- [✅] Categorize 187 documentation files
- [✅] Map to v14 destinations (9 categories)
- [✅] Define documentation structure
- [✅] Create migration priority (P0/P1/P2)
- [✅] Establish quality standards
- [✅] Define update process

### **Phase 1 Documentation Tasks**

**Week 1** (P0):
- [ ] Migrate standards & principles (10 files)
- [ ] Create getting started guide
- [ ] Create installation guide
- [ ] Update pipeline READMEs with detailed content

**Week 2** (P1):
- [ ] Migrate architecture docs (40 files)
- [ ] Create pipeline-specific guides (12 files)
- [ ] Create API references (12 files)

**Week 3** (P1):
- [ ] Migrate implementation summaries (30 files)
- [ ] Update configuration guides
- [ ] Create troubleshooting guide

**Week 4-5** (P2):
- [ ] Archive session summaries (50 files)
- [ ] Create advanced guides (5 files)
- [ ] Archive legacy architecture (20 files)

---

## 📝 Notes

### **Documentation Best Practices**

1. **Single Source of Truth**: Each concept documented in ONE place, linked elsewhere
2. **User-Focused**: Write for users (developers), not for yourself
3. **Examples First**: Show working examples before explaining theory
4. **Progressive Disclosure**: Simple examples first, complex later
5. **Keep Current**: Update docs BEFORE merging code changes

### **Automation Opportunities**

- **API Docs**: Auto-generate from docstrings (Sphinx/MkDocs)
- **Schema Docs**: Auto-generate from JSON Schema
- **Changelog**: Auto-generate from git commits
- **Cross-References**: Auto-check broken links

---

## ✅ Phase 0.10 Complete

**Status**: Documentation migration mapping complete
**Files Created**: 1 (this document)
**Docs Mapped**: 187 markdown files → 9 v14 categories
**Next**: Phase 0.11 (Migration safety checklist)

---

**Created**: 2025-11-14
**Status**: ✅ Complete - Ready for Phase 1 documentation migration
