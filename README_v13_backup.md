# Document Translator v14 - Three-Pipeline Architecture

**Version**: 14.0.0
**Architecture**: Three Independent Vertical Pipelines
**Migration Date**: 2025-11-14
**Source**: v13 monolithic system

## 🎯 Strategic Vision

**Primary Goal**: Long-term stability and maintainability with accuracy as the primary goal, not speed.

**User's Direction** (2025-11-14):
> "I am interested in long-term stability and maintainance with accuracy as my primary goal, not speed. I also think we should move this to v14 since it is such a departure that if we screw things up can come back to this point."

## 🏗️ Three-Pipeline Architecture

### **Pipeline 1: Extraction** (`extraction_v14_P1/`)
**Purpose**: PDF → Structured JSON
**Input**: Raw PDF documents
**Output**: `extraction_results_v1.json` (equations, tables, figures, text with bboxes)

**Key Components**:
- Detection agents (YOLO, Docling, PyMuPDF)
- Extraction agents (equation, table, figure, text)
- Parallel processing (multi-core optimization)
- Bidirectional extractors

**Recovered v12 Components**:
- `bidirectional_equation_extractor.py` - Equation extraction
- `parallel_equation_extractor.py` - Multi-core equation processing
- `parallel_table_extractor.py` - Multi-core table processing

### **Pipeline 2: RAG Preparation** (`rag_v14_P2/`)
**Purpose**: Structured JSON → RAG-Ready JSONL + Knowledge Graph
**Input**: `extraction_results_v1.json`
**Output**: `rag_bundles_v1.json` (semantic chunks, embeddings, relationships)

**Key Components**:
- Intelligence analyzers (equation, figure, table, text)
- Document orchestrators (scanning, dual-scanning)
- Relationship mappers
- Semantic chunkers

**Recovered v12 Components**:
- `document_intelligence_scanner.py` - Phase 1 orchestrator
- `dual_scanning_agent_framework.py` - Multi-agent scanning
- `equation_intelligence_analyzer.py` - Equation analysis
- `figure_intelligence_analyzer.py` - Figure analysis
- `table_intelligence_analyzer.py` - Table analysis
- `text_intelligence_analyzer.py` - Text analysis

### **Pipeline 3: Curation** (`curation_v14_P3/`)
**Purpose**: RAG-Ready Data → Curated Knowledge Database
**Input**: `rag_bundles_v1.json`
**Output**: `knowledge_graph_v1.json` (validated, calibrated, curated)

**Key Components**:
- LLM Confidence Calibrator (4 bias pattern mitigation)
- Domain Specificity Validator (heat transfer specialty)
- Novelty Metadata Database (training date versioning)
- Quality assurance validators

**v13 Calibration Work** (migrated to v14):
- `llm_confidence_calibrator.py` - Bias pattern mitigation
- `novelty_metadata_database.py` - Training date tracking
- `domain_specificity_validator.py` - Specialty validation

### **Common** (`common/`)
**Purpose**: Shared utilities, base classes, interfaces
**Components**:
- Base extraction agent
- Common interfaces
- Utility functions
- Shared configuration

### **Schemas** (`schemas/`)
**Purpose**: JSON Schema definitions for inter-pipeline contracts
**Files**:
- `extraction/extraction_results_v1.json` - Pipeline 1 output schema
- `rag/rag_bundles_v1.json` - Pipeline 2 output schema
- `curation/knowledge_graph_v1.json` - Pipeline 3 output schema

## 📊 Migration from v13

### **Component Recovery Status** (Phase 0.4 Complete)

**✅ All 8 MUST RECOVER components** (agentic architecture):
- Document orchestrators (2): intelligence scanner, dual-scanning framework
- Intelligence analyzers (4): equation, figure, table, text
- Extraction agents (2): bidirectional equation, parallel extractors

**✅ 2/4 SHOULD RECOVER components** (performance):
- Parallel equation/table extractors

**⚠️ 2 components not in v12 git** (low priority utilities):
- docling_cpu_baseline_test.py (alternative method)
- enhance_existing_extraction.py (utility)

### **v13 Component Migration**

**Source**: 329 Python files + 152 config files + 216 docs
**Destination**: Three independent pipelines with clear separation

**Migration Mapping**: See `docs/COMPONENT_MIGRATION_MAPPING.md` (Phase 0.8)

## 🔧 Naming Convention

**Format**: `{function}_v14_P{number}`

**Examples**:
- `extraction_v14_P1/` - Pipeline 1 (Extraction)
- `rag_v14_P2/` - Pipeline 2 (RAG Preparation)
- `curation_v14_P3/` - Pipeline 3 (Curation)
- `config/extraction_v14_P1_config.yaml`
- `tests/test_rag_v14_P2_integration.py`

**Rationale**: Clear version and pipeline association, supports future expansion (v15_P1, v14_P4, etc.)

## 📁 Directory Structure

```
document_translator_v14/
├── extraction_v14_P1/          # Pipeline 1: PDF → JSON
│   ├── src/
│   │   ├── agents/            # Detection & extraction agents
│   │   ├── core/              # Core extraction logic
│   │   └── utils/             # Extraction utilities
│   ├── config/                # Pipeline 1 configuration
│   ├── tests/                 # Pipeline 1 tests
│   └── docs/                  # Pipeline 1 documentation
│
├── rag_v14_P2/                # Pipeline 2: JSON → JSONL+Graph
│   ├── src/
│   │   ├── orchestration/     # Document orchestrators
│   │   ├── analyzers/         # Intelligence analyzers
│   │   ├── processors/        # Semantic processors
│   │   ├── core/              # Core RAG logic
│   │   └── utils/             # RAG utilities
│   ├── config/                # Pipeline 2 configuration
│   ├── tests/                 # Pipeline 2 tests
│   └── docs/                  # Pipeline 2 documentation
│
├── curation_v14_P3/           # Pipeline 3: JSONL → Database
│   ├── src/
│   │   ├── core/              # Calibration & validation
│   │   ├── validators/        # Domain validators
│   │   ├── database/          # Novelty database
│   │   └── utils/             # Curation utilities
│   ├── config/                # Pipeline 3 configuration
│   ├── tests/                 # Pipeline 3 tests
│   └── docs/                  # Pipeline 3 documentation
│
├── common/                    # Shared utilities
│   ├── src/
│   │   ├── base/              # Base classes
│   │   ├── interfaces/        # Common interfaces
│   │   └── utilities/         # Shared utilities
│   ├── tests/                 # Common tests
│   └── docs/                  # Common documentation
│
├── schemas/                   # JSON Schemas
│   ├── extraction/            # Pipeline 1 schemas
│   ├── rag/                   # Pipeline 2 schemas
│   └── curation/              # Pipeline 3 schemas
│
├── config/                    # Root configuration
├── docs/                      # Root documentation
├── tests/                     # Integration tests
└── tools/                     # Migration & utility tools
```

## 🚀 Getting Started

### **Prerequisites**
- Python 3.11+
- Git
- Dependencies: See `requirements.txt` in each pipeline

### **Installation** (After Phase 1 Complete)
```bash
cd /home/thermodynamics/document_translator_v14

# Install Pipeline 1
cd extraction_v14_P1
pip install -e .

# Install Pipeline 2
cd ../rag_v14_P2
pip install -e .

# Install Pipeline 3
cd ../curation_v14_P3
pip install -e .

# Install Common
cd ../common
pip install -e .
```

### **Usage** (After Phase 1 Complete)
```bash
# Pipeline 1: Extract from PDF
python extraction_v14_P1/src/main.py --input document.pdf --output extraction_results.json

# Pipeline 2: Prepare for RAG
python rag_v14_P2/src/main.py --input extraction_results.json --output rag_bundles.json

# Pipeline 3: Curate and validate
python curation_v14_P3/src/main.py --input rag_bundles.json --output knowledge_graph.json
```

## 📋 Phase 0 Progress (Pre-Migration Safety)

**Timeline**: 3-4 days
**Purpose**: Prevent component loss (v12→v13 left 24% behind)

- [✅] **Phase 0.1**: Complete v13 audit (329 Python files cataloged)
- [✅] **Phase 0.2**: Analyze component purposes (docstrings extracted)
- [✅] **Phase 0.3**: Create v13 component audit report
- [✅] **Phase 0.4**: Historical v12 analysis (12 components identified, 10 recovered)
- [✅] **Phase 0.5**: Create v14 root directory structure
- [🔄] **Phase 0.6**: Initialize v14 foundation (IN PROGRESS)
- [⏸️] **Phase 0.7**: Initialize git repository
- [⏸️] **Phase 0.8**: Create component migration mapping
- [⏸️] **Phase 0.9**: Create configuration migration mapping
- [⏸️] **Phase 0.10**: Create documentation migration mapping
- [⏸️] **Phase 0.11**: Create migration safety checklist
- [⏸️] **Phase 0.12**: Set up git branch strategy
- [⏸️] **Phase 0.13**: Create Phase 0 validation script

## 📚 Documentation

- **Migration Plan**: `docs/V13_TO_V14_MIGRATION_PLAN.md` (complete 6-week plan)
- **Component Audit**: `docs/V13_COMPONENT_AUDIT.md` (329 files analyzed)
- **Historical Analysis**: `docs/HISTORICAL_COMPONENT_ANALYSIS.md` (v12→v13 comparison)
- **Critical Findings**: `docs/PHASE_0_CRITICAL_FINDINGS.md` (12 left-behind components)
- **Architecture Review**: `docs/THREE_PIPELINE_ARCHITECTURE_MIGRATION_PLAN.md` (Web Claude's proposal)

## 🔗 Related Repositories

- **v13 Monolithic** (preserved): `/home/thermodynamics/document_translator_v13/`
- **v12 Historical**: `/home/thermodynamics/document_translator_v12/`

## 🎯 Project Goals

1. **Accuracy First**: Prioritize correctness over speed
2. **Long-term Stability**: Maintainable architecture for years
3. **Component Preservation**: Never leave working components behind
4. **Agentic Approach**: Modular, reusable agent components
5. **Safe Migration**: Complete rollback capability to v13

## 📝 License

[To be determined]

## 👥 Contributors

- User (Project Direction)
- Claude Code (Implementation)
- Web Claude (Architecture Review)

---

**Status**: Phase 0 in progress (Pre-Migration Safety)
**Next**: Phase 1 - Foundation & Interfaces (Week 1)
**ETA**: 6 weeks to complete migration
