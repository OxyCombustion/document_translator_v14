# Component Migration Mapping: v13 + v12 → v14

**Purpose**: Complete mapping of all components from v13 and recovered v12 components to v14 three-pipeline architecture

**Date**: 2025-11-14
**Source Systems**:
- v13 (329 Python files, 152 configs, 216 docs)
- v12 recovered (10 working components)
**Destination**: v14 three-pipeline architecture

---

## 📊 Migration Overview

### **Component Counts**

| Source | Total Files | Destination | Status |
|--------|-------------|-------------|--------|
| v13 Python | 329 | All pipelines | ⏸️ Mapping in progress |
| v13 Config | 152 | All pipelines | ⏸️ Pending |
| v13 Docs | 216 | All pipelines | ⏸️ Pending |
| v12 Recovered | 10 | P1 & P2 | ✅ Components ready |
| **Total** | **707** | **v14** | **⏸️ Phase 0.8** |

### **v12 Recovered Components Status**

✅ **All 10 working components recovered** from v12 git history:

| # | Component | Size | Category | v14 Destination |
|---|-----------|------|----------|-----------------|
| 1 | bidirectional_equation_extractor.py | 17K | Extraction | extraction_v14_P1/src/agents/extraction/ |
| 2 | parallel_equation_extractor.py | 21K | Performance | extraction_v14_P1/src/agents/extraction/ |
| 3 | parallel_table_extractor.py | 15K | Performance | extraction_v14_P1/src/agents/extraction/ |
| 4 | document_intelligence_scanner.py | 22K | Orchestration | rag_v14_P2/src/orchestration/ |
| 5 | dual_scanning_agent_framework.py | 32K | Orchestration | rag_v14_P2/src/orchestration/ |
| 6 | equation_intelligence_analyzer.py | 12K | Analysis | rag_v14_P2/src/analyzers/ |
| 7 | figure_intelligence_analyzer.py | 17K | Analysis | rag_v14_P2/src/analyzers/ |
| 8 | table_intelligence_analyzer.py | 9.7K | Analysis | rag_v14_P2/src/analyzers/ |
| 9 | text_intelligence_analyzer.py | 25K | Analysis | rag_v14_P2/src/analyzers/ |
| 10 | - | - | - | - |

**Total Recovered**: 171K of working code from v12

---

## 🗺️ Pipeline 1: Extraction (extraction_v14_P1/)

**Purpose**: PDF → Structured JSON
**Responsibilities**: Detection & extraction of equations, tables, figures, text

### **Recovered v12 Components → P1**

| Component | Destination Path | Integration Notes |
|-----------|------------------|-------------------|
| bidirectional_equation_extractor.py | extraction_v14_P1/src/agents/extraction/ | Handles equation numbers before/after content |
| parallel_equation_extractor.py | extraction_v14_P1/src/agents/extraction/ | Multi-core optimization (1.9x speedup) |
| parallel_table_extractor.py | extraction_v14_P1/src/agents/extraction/ | Multi-core table processing |

### **v13 Components → P1** (To be mapped)

**From v13 Component Audit** (329 files total):

Detection agents from v13 `agents/detection/`:
- ⏸️ TBD: Map YOLO, Docling, PyMuPDF detectors
- ⏸️ TBD: Map unified detection module
- ⏸️ TBD: Map bounding box utilities

Extraction agents from v13 `agents/extraction/`:
- ⏸️ TBD: Map equation extraction agents
- ⏸️ TBD: Map table extraction agents
- ⏸️ TBD: Map figure extraction agents
- ⏸️ TBD: Map text extraction agents

**Action Required**: Phase 0.8 complete mapping requires reading V13_COMPONENT_AUDIT.md and mapping each of 329 files

---

## 🗺️ Pipeline 2: RAG Preparation (rag_v14_P2/)

**Purpose**: Structured JSON → RAG-Ready JSONL + Knowledge Graph
**Responsibilities**: Intelligence analysis, orchestration, relationship mapping

### **Recovered v12 Components → P2**

| Component | Destination Path | Integration Notes |
|-----------|------------------|-------------------|
| document_intelligence_scanner.py | rag_v14_P2/src/orchestration/ | Phase 1 orchestrator |
| dual_scanning_agent_framework.py | rag_v14_P2/src/orchestration/ | Multi-agent dual-scanning |
| equation_intelligence_analyzer.py | rag_v14_P2/src/analyzers/ | Equation analysis |
| figure_intelligence_analyzer.py | rag_v14_P2/src/analyzers/ | Figure analysis (100% accuracy) |
| table_intelligence_analyzer.py | rag_v14_P2/src/analyzers/ | Table structure analysis |
| text_intelligence_analyzer.py | rag_v14_P2/src/analyzers/ | Text semantic segmentation |

### **v13 Components → P2** (To be mapped)

**From v13 Component Audit** (329 files total):

RAG extraction from v13 `agents/rag/`:
- ⏸️ TBD: Map RAG extraction agents
- ⏸️ TBD: Map relationship mappers
- ⏸️ TBD: Map semantic chunkers

Document processing from v13 `agents/document_processing/`:
- ⏸️ TBD: Map document orchestrators
- ⏸️ TBD: Map structure analyzers

**Action Required**: Phase 0.8 complete mapping requires reading V13_COMPONENT_AUDIT.md and mapping each of 329 files

---

## 🗺️ Pipeline 3: Curation (curation_v14_P3/)

**Purpose**: RAG-Ready Data → Curated Knowledge Database
**Responsibilities**: Calibration, validation, novelty detection

### **v13 Calibration Components → P3**

**P0/P1 Priority Components** (from v13 Phase 1 work):

| Component | v13 Location | v14 Destination | Status |
|-----------|--------------|-----------------|--------|
| llm_confidence_calibrator.py | src/rag/ | curation_v14_P3/src/core/ | ⏸️ To migrate |
| novelty_metadata_database.py | src/rag/ | curation_v14_P3/src/database/ | ⏸️ To migrate |
| domain_specificity_validator.py | src/rag/ | curation_v14_P3/src/validators/ | ⏸️ To migrate |

**Integration Architecture** (from migration plan):
```python
# curation_v14_P3/src/orchestrator.py
class Pipeline3Orchestrator:
    def __init__(self, config_path: Path):
        self.calibrator = LLMConfidenceCalibrator(
            model_training_date=self.config['model']['training_cutoff_date'],
            calibration_config=self.config['calibration']
        )
        self.domain_validator = DomainSpecificityValidator(
            domain=self.config['domain_validation']['domain']
        )
        self.db = NoveltyMetadataDatabase(
            db_path=self.config['database']['path']
        )
```

### **v13 Components → P3** (To be mapped)

**From v13 Component Audit** (329 files total):

Metadata agents from v13 `agents/metadata/`:
- ⏸️ TBD: Map Zotero integration
- ⏸️ TBD: Map TRL library system
- ⏸️ TBD: Map symbol library manager

**Action Required**: Phase 0.8 complete mapping requires reading V13_COMPONENT_AUDIT.md and mapping each of 329 files

---

## 🗺️ Common Utilities (common/)

**Purpose**: Shared utilities, base classes, interfaces
**Shared Across**: All three pipelines

### **v13 Components → Common** (To be mapped)

**From v13 Component Audit** (329 files total):

Core/base from v13 `src/agents/base.py`:
- ⏸️ TBD: Map BaseExtractionAgent → common/src/base/base_agent.py
- ⏸️ TBD: Map common interfaces → common/src/interfaces/

Utilities from v13 `src/utils/`:
- ⏸️ TBD: Map file I/O utilities
- ⏸️ TBD: Map configuration management
- ⏸️ TBD: Map logging utilities

**Action Required**: Phase 0.8 complete mapping requires reading V13_COMPONENT_AUDIT.md and mapping each of 329 files

---

## 📋 Configuration Migration Mapping

**Source**: v13 (152 configuration files)
**Destination**: v14 three-pipeline configs

### **Configuration Categories**

| v13 Config Type | Count | v14 Destination | Status |
|----------------|-------|-----------------|--------|
| Pipeline configs | ~10 | extraction/rag/curation_v14_P*_config.yaml | ⏸️ Phase 0.9 |
| Agent configs | ~50 | Each pipeline's config/ | ⏸️ Phase 0.9 |
| ML model configs | ~20 | Pipeline-specific configs | ⏸️ Phase 0.9 |
| System configs | ~30 | Root config/ | ⏸️ Phase 0.9 |
| Other configs | ~42 | TBD | ⏸️ Phase 0.9 |

**Action Required**: Phase 0.9 will create detailed configuration migration mapping

---

## 📚 Documentation Migration Mapping

**Source**: v13 (216 documentation files)
**Destination**: v14 pipeline-specific docs

### **Documentation Categories**

| v13 Doc Type | Count | v14 Destination | Status |
|--------------|-------|-----------------|--------|
| Session summaries | ~50 | docs/historical/ | ⏸️ Phase 0.10 |
| Architecture docs | ~30 | docs/architecture/ | ⏸️ Phase 0.10 |
| Implementation guides | ~40 | Pipeline-specific docs/ | ⏸️ Phase 0.10 |
| API references | ~20 | Pipeline-specific docs/ | ⏸️ Phase 0.10 |
| Other docs | ~76 | TBD | ⏸️ Phase 0.10 |

**Action Required**: Phase 0.10 will create detailed documentation migration mapping

---

## 🔍 Migration Decision Rules

### **Rule 1: Agentic Components → P2**
**IF** component is an orchestrator or intelligence analyzer
**THEN** migrate to `rag_v14_P2/src/orchestration/` or `rag_v14_P2/src/analyzers/`
**REASON**: User emphasized "agentic approach" and "reuse useful components"

### **Rule 2: Detection/Extraction → P1**
**IF** component does detection or extraction
**THEN** migrate to `extraction_v14_P1/src/agents/`
**REASON**: Pipeline 1 responsibility

### **Rule 3: Calibration/Validation → P3**
**IF** component does LLM calibration, domain validation, or novelty detection
**THEN** migrate to `curation_v14_P3/src/`
**REASON**: Pipeline 3 responsibility

### **Rule 4: Shared Utilities → Common**
**IF** component is used by multiple pipelines
**THEN** migrate to `common/src/`
**REASON**: Avoid duplication

### **Rule 5: Base Classes → Common**
**IF** component is a base class or interface
**THEN** migrate to `common/src/base/` or `common/src/interfaces/`
**REASON**: Foundation for all pipelines

---

## ⚠️ Components NOT to Migrate

### **Excluded v12 Components**

| Component | Reason | Action |
|-----------|--------|--------|
| docling_formula_enrichment (docling_cpu_formula_fixed.py) | Known broken (hangs on CPU) | ❌ Exclude, document reason |

### **v13 Components to Exclude** (To be identified)

⏸️ **Action Required**: During Phase 0.8 mapping, identify:
- Broken/deprecated code
- Duplicate implementations
- Test files to archive
- Obsolete utilities

---

## 📊 Migration Progress Tracking

### **Phase 0 Status**

| Phase | Task | Status | Notes |
|-------|------|--------|-------|
| 0.4 | Recover v12 components | ✅ Complete | 10/12 recovered (2 not in git) |
| 0.5 | Create v14 directory | ✅ Complete | Three-pipeline structure |
| 0.6 | Initialize foundation | ✅ Complete | READMEs + configs |
| 0.7 | Initialize git | ✅ Complete | First commit: 64c4c5d |
| 0.8 | Component mapping | 🔄 IN PROGRESS | This document |
| 0.9 | Config mapping | ⏸️ Pending | Depends on 0.8 |
| 0.10 | Doc mapping | ⏸️ Pending | Depends on 0.8 |
| 0.11 | Safety checklist | ⏸️ Pending | Validation rules |
| 0.12 | Git branch strategy | ⏸️ Pending | main/develop/phase |
| 0.13 | Validation script | ⏸️ Pending | Automated checks |

### **Next Actions**

1. **Complete Component Mapping** (Phase 0.8):
   - Read V13_COMPONENT_AUDIT.md (329 files)
   - Apply decision rules to each component
   - Create detailed mapping table
   - Identify components to exclude

2. **Configuration Mapping** (Phase 0.9):
   - Analyze 152 v13 config files
   - Map to three pipeline configs
   - Preserve critical settings

3. **Documentation Mapping** (Phase 0.10):
   - Analyze 216 v13 docs
   - Separate historical vs current
   - Distribute to appropriate pipelines

---

## 📝 Notes

- **Agentic Preservation**: All 6 agentic components (orchestrators + analyzers) from v12 mapped to P2
- **Performance Optimization**: All 2 parallel extractors from v12 mapped to P1
- **Calibration Preservation**: All 3 v13 P0/P1 components will migrate to P3
- **No Component Loss**: Tracking ALL 339 components (329 v13 + 10 v12) to prevent v12→v13 mistakes

---

**Status**: Phase 0.8 in progress - Framework complete, detailed mapping pending
**Next**: Complete detailed 329-file v13 component mapping using V13_COMPONENT_AUDIT.md
