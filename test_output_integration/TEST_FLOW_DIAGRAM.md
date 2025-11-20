# Integration Test Flow Diagram

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  END-TO-END INTEGRATION TEST                         │
│                     test_integration_e2e.py                          │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ├─── PHASE 1: Pipeline Execution
                                 ├─── PHASE 2: Data Contract Validation
                                 ├─── PHASE 3: Query Retrieval Testing
                                 ├─── PHASE 4: Performance Analysis
                                 └─── PHASE 5: Report Generation
```

## Detailed Test Flow

```
START
  │
  ├── Prerequisites Check
  │   ├── ✓ PDF exists (Ch-04_Heat_Transfer.pdf)
  │   ├── ✓ YOLO model exists
  │   └── ✓ All test scripts exist
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 1: SEQUENTIAL PIPELINE EXECUTION                         │
└────────────────────────────────────────────────────────────────┘
  │
  ├── PIPELINE 1: Extraction (subprocess)
  │   │
  │   ├── Run: test_with_unified_orchestrator.py
  │   │   ├── YOLO detection (DocLayout-YOLO)
  │   │   ├── Object extraction (equations, tables, figures)
  │   │   ├── OCR & text extraction
  │   │   └── Save to test_output_orchestrator/
  │   │
  │   ├── Collect Metrics
  │   │   ├── Duration: ~555s
  │   │   ├── Total objects: 162
  │   │   ├── Equations: 106
  │   │   └── Tables: 14
  │   │
  │   └── Status: ✅ PASS / ❌ FAIL
  │        (If FAIL → Abort)
  │
  ▼
  ├── PIPELINE 2: RAG Ingestion (subprocess)
  │   │
  │   ├── Run: test_rag_pipeline.py
  │   │   ├── Semantic structure detection
  │   │   ├── Hierarchical processing
  │   │   ├── Semantic chunking
  │   │   ├── Citation extraction
  │   │   └── Save to test_output_rag/
  │   │       ├── rag_bundles.jsonl
  │   │       └── citation_graph.json
  │   │
  │   ├── Collect Metrics
  │   │   ├── Duration: ~1s
  │   │   ├── Chunks: 34
  │   │   ├── Avg chars/chunk: 3,834
  │   │   └── Citations: 386
  │   │
  │   └── Status: ✅ PASS / ❌ FAIL
  │        (If FAIL → Abort)
  │
  ▼
  ├── PIPELINE 3: Database Loading (subprocess)
  │   │
  │   ├── Run: test_database_pipeline.py
  │   │   ├── Load JSONL chunks
  │   │   ├── Load citation graph
  │   │   ├── Create ChromaDB collection
  │   │   ├── Enrich metadata with citations
  │   │   ├── Batch insert with retry
  │   │   └── Save to test_output_database/chromadb/
  │   │
  │   ├── Collect Metrics
  │   │   ├── Duration: ~1s
  │   │   ├── Chunks inserted: 34
  │   │   ├── Database size: ~1.2 MB
  │   │   └── Chunks with citations: 34/34
  │   │
  │   └── Status: ✅ PASS / ❌ FAIL
  │        (If FAIL → Abort)
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 2: DATA CONTRACT VALIDATION                              │
└────────────────────────────────────────────────────────────────┘
  │
  ├── Extraction → RAG Contract
  │   ├── Check: test_output_orchestrator/ exists
  │   │   ├── equations/ directory
  │   │   ├── tables/ directory
  │   │   └── unified_pipeline_summary.json
  │   │
  │   ├── Validate: JSON structure
  │   │   └── Required fields: total_objects
  │   │
  │   └── Status: ✅ VALID / ❌ INVALID
  │
  ├── RAG → Database Contract
  │   ├── Check: test_output_rag/ exists
  │   │   ├── rag_bundles.jsonl
  │   │   └── citation_graph.json
  │   │
  │   ├── Validate: JSONL format (per line)
  │   │   └── Required fields: chunk_id, text, page_number,
  │   │                         char_count, metadata
  │   │
  │   ├── Validate: Citation graph format
  │   │   └── Required fields: citation_stats, citations_by_chunk
  │   │
  │   └── Status: ✅ VALID / ❌ INVALID
  │
  └── Data Integrity
      ├── Check: Chunk count consistency
      │   └── JSONL count == ChromaDB count
      │
      ├── Check: Citation count preservation
      │   └── RAG citations > 0
      │
      └── Status: ✅ VALID / ❌ INVALID
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 3: QUERY RETRIEVAL TESTING                               │
└────────────────────────────────────────────────────────────────┘
  │
  ├── Load ChromaDB Collection
  │   └── Connect to: test_output_database/chromadb/
  │
  ├── Semantic Query Tests (5 queries)
  │   │
  │   ├── Query 1: "What is Newton's law of cooling?"
  │   │   ├── Execute semantic search (n_results=2)
  │   │   ├── Check: Results >= 2
  │   │   ├── Validate source tracing
  │   │   │   ├── chunk_id exists
  │   │   │   ├── page_number in valid range (1-34)
  │   │   │   └── citations preserved
  │   │   └── Status: ✅ PASS / ❌ FAIL
  │   │
  │   ├── Query 2: "convection heat transfer coefficient"
  │   │   └── [Same validation as Query 1]
  │   │
  │   ├── Query 3: "radiation heat transfer"
  │   │   └── [Same validation as Query 1]
  │   │
  │   ├── Query 4: "thermal conductivity equations"
  │   │   └── [Same validation as Query 1]
  │   │
  │   └── Query 5: "heat exchanger design"
  │       └── [Same validation as Query 1]
  │
  ├── Citation Filter Tests (2 filters)
  │   │
  │   ├── Filter 1: Figure 11
  │   │   ├── Filter by: cited_figures contains "11"
  │   │   ├── Check: Results >= 3
  │   │   └── Status: ✅ PASS / ❌ FAIL
  │   │
  │   └── Filter 2: Equation 1
  │       ├── Filter by: cited_equations contains "1"
  │       ├── Check: Results >= 2
  │       └── Status: ✅ PASS / ❌ FAIL
  │
  └── Source Tracing Validation
      ├── For each semantic query result:
      │   ├── Verify: chunk_id → page_number → PDF page
      │   ├── Verify: Citations preserved from RAG
      │   └── Verify: Metadata chains correctly
      │
      └── Status: ✅ ALL VALID / ❌ SOME INVALID
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 4: PERFORMANCE ANALYSIS                                  │
└────────────────────────────────────────────────────────────────┘
  │
  ├── Calculate Total Duration
  │   └── Sum: Extraction + RAG + Database
  │
  ├── Calculate Throughput
  │   └── Pages/minute: (34 pages / total_seconds) * 60
  │
  ├── Pipeline Breakdown
  │   ├── Extraction: XXXs (99.7%)
  │   ├── RAG:        Xs   (0.2%)
  │   └── Database:   Xs   (0.2%)
  │
  └── Data Flow Statistics
      ├── Extraction objects: 162
      ├── RAG chunks: 34
      └── Database chunks: 34
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│ PHASE 5: REPORT GENERATION                                     │
└────────────────────────────────────────────────────────────────┘
  │
  ├── Generate Text Report
  │   ├── Pipeline execution results
  │   ├── Data flow validation
  │   ├── Query retrieval results
  │   ├── Performance summary
  │   └── Overall status
  │
  ├── Save Reports
  │   ├── integration_report.txt (human-readable)
  │   └── integration_summary.json (machine-readable)
  │
  └── Print Summary to Console
  │
  ▼
┌────────────────────────────────────────────────────────────────┐
│ OVERALL STATUS DETERMINATION                                   │
└────────────────────────────────────────────────────────────────┘
  │
  ├── Check ALL conditions:
  │   ├── ✅ Pipeline 1 success
  │   ├── ✅ Pipeline 2 success
  │   ├── ✅ Pipeline 3 success
  │   ├── ✅ Extraction → RAG contract valid
  │   ├── ✅ RAG → Database contract valid
  │   ├── ✅ Data integrity valid
  │   └── ✅ All query tests passed
  │
  ├── ALL TRUE → Exit 0 (✅ INTEGRATION TEST PASSED)
  │
  └── ANY FALSE → Exit 1 (❌ INTEGRATION TEST FAILED)
  │
  ▼
END
```

## Data Flow Through Pipelines

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT                                    │
│              Ch-04_Heat_Transfer.pdf                             │
│                     (34 pages)                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │         PIPELINE 1: EXTRACTION                       │
    │                                                      │
    │  DocLayout-YOLO → Object Detection → Extraction     │
    ├──────────────────────────────────────────────────────┤
    │  OUTPUT:                                             │
    │  • equations/    (106 files)                        │
    │  • tables/       (14 files)                         │
    │  • figures/      (XX files)                         │
    │  • text/         (XX files)                         │
    │  • bibliography.json                                 │
    │  • unified_pipeline_summary.json                     │
    └──────────────────────────────────────────────────────┘
                          │
                          ▼ [Validate: Extraction → RAG Contract]
                          │
    ┌─────────────────────────────────────────────────────┐
    │         PIPELINE 2: RAG INGESTION                    │
    │                                                      │
    │  Semantic Detection → Chunking → Citation Graph     │
    ├──────────────────────────────────────────────────────┤
    │  OUTPUT:                                             │
    │  • rag_bundles.jsonl        (34 chunks)             │
    │  • citation_graph.json       (386 citations)        │
    └──────────────────────────────────────────────────────┘
                          │
                          ▼ [Validate: RAG → Database Contract]
                          │
    ┌─────────────────────────────────────────────────────┐
    │         PIPELINE 3: DATABASE LOADING                 │
    │                                                      │
    │  Load JSONL → Enrich Metadata → Insert ChromaDB     │
    ├──────────────────────────────────────────────────────┤
    │  OUTPUT:                                             │
    │  • chromadb/                 (34 chunks)            │
    │    ├── Collection: chapter_4_heat_transfer          │
    │    ├── Embeddings: all-MiniLM-L6-v2                 │
    │    └── Enriched with citation metadata              │
    └──────────────────────────────────────────────────────┘
                          │
                          ▼ [Validate: Data Integrity]
                          │
    ┌─────────────────────────────────────────────────────┐
    │         QUERY RETRIEVAL VALIDATION                   │
    │                                                      │
    │  5 Semantic Queries + 2 Citation Filters            │
    ├──────────────────────────────────────────────────────┤
    │  VALIDATION:                                         │
    │  • Results returned                                  │
    │  • Source tracing works                             │
    │  • Citations preserved                              │
    │  • Page numbers valid                               │
    └──────────────────────────────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │              FINAL OUTPUT                            │
    │                                                      │
    │  • integration_report.txt                           │
    │  • integration_summary.json                         │
    │  • Exit code: 0 (pass) or 1 (fail)                 │
    └──────────────────────────────────────────────────────┘
```

## Validation Points

```
EXTRACTION → RAG
├── Directory existence
│   ├── test_output_orchestrator/equations/
│   ├── test_output_orchestrator/tables/
│   └── test_output_orchestrator/bibliography.json
├── File format
│   └── unified_pipeline_summary.json (valid JSON)
└── Required fields
    └── total_objects present

RAG → DATABASE
├── File existence
│   ├── test_output_rag/rag_bundles.jsonl
│   └── test_output_rag/citation_graph.json
├── JSONL format (per line)
│   ├── Valid JSON
│   ├── chunk_id present
│   ├── text present
│   ├── page_number present
│   ├── char_count present
│   └── metadata present
└── Citation graph format
    ├── citation_stats present
    └── citations_by_chunk present

DATA INTEGRITY
├── Chunk count consistency
│   └── JSONL line count == ChromaDB count
├── Citation preservation
│   └── Total citations > 0
└── Metadata enrichment
    └── All chunks have citation metadata

SOURCE TRACING
├── For each query result:
│   ├── chunk_id → ChromaDB lookup
│   ├── page_number → valid range (1-34)
│   ├── page_number → PDF page mapping
│   └── citations → citation_graph lookup
```

## Error Handling Flow

```
Pipeline Execution
├── Timeout (900s extraction, 300s RAG/DB)
│   └── Return: FAIL + timeout message
├── Non-zero exit code
│   └── Return: FAIL + stderr output
└── Exception
    └── Return: FAIL + exception traceback

Contract Validation
├── Missing file
│   └── Issue: "Missing extraction output: <path>"
├── Invalid JSON
│   └── Issue: "Invalid JSON: <error>"
└── Missing field
    └── Issue: "Missing field: <field_name>"

Query Testing
├── Query returns 0 results
│   └── FAIL + expected minimum not met
├── Source tracing fails
│   └── FAIL + missing/invalid fields
└── ChromaDB error
    └── FAIL + connection/query error
```

## Success Criteria Matrix

| Component | Criterion | Pass Condition |
|-----------|-----------|----------------|
| Pipeline 1 | Execution | Exit code 0 |
| Pipeline 1 | Output | ≥160 objects extracted |
| Pipeline 2 | Execution | Exit code 0 |
| Pipeline 2 | Output | ≥30 chunks created |
| Pipeline 3 | Execution | Exit code 0 |
| Pipeline 3 | Output | All chunks inserted |
| Contract 1 | Validation | All required files exist |
| Contract 2 | Validation | Valid JSONL + graph |
| Data | Integrity | Counts consistent |
| Query 1-5 | Results | ≥min_results per query |
| Query 1-5 | Tracing | All fields valid |
| Filter 1-2 | Results | ≥min_results per filter |
| **OVERALL** | **ALL** | **ALL criteria TRUE** |

---

**Visual Key:**
- `┌─┐` - Process boundaries
- `│` - Sequential flow
- `├──` - Branch/option
- `▼` - Flow continuation
- `✅` - Success condition
- `❌` - Failure condition

**Last Updated**: 2025-11-19
