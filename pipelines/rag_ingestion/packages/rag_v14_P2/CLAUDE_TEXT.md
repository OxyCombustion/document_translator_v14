# Text Extraction Pipeline - AI Instance Memory

**Pipeline**: `rag_v14_P2` (RAG Preparation Package)
**Component**: Text Extraction & Semantic Chunking
**Last Updated**: 2025-11-16
**AI Scope**: Text extraction and RAG preparation ONLY (no equations, tables, or figures)

---

## 🎯 PURPOSE OF THIS AI INSTANCE

This AI instance is **dedicated exclusively** to text extraction and semantic chunking for RAG. It should:
- ✅ Know everything about semantic chunking strategies
- ✅ Remember embedding optimization techniques
- ✅ Track chunk size distributions and quality metrics
- ❌ NOT track equation/table/figure extraction
- ❌ NOT carry context about detection algorithms

**Context Budget**: Small, focused, deep expertise in text and RAG preparation only.

---

## 📝 TEXT EXTRACTION DOMAIN KNOWLEDGE

### Current Status (2025-11-16)

**Detection**: Docling text detection available
- Docling provides `main_text` attribute with full document text
- Current issue: Docling result object doesn't have `output` attribute in some tests
- Fallback: Use PyMuPDF direct text extraction

**Extraction**: Not yet enabled in full document test
- Text extraction exists but was not run in latest test
- Focus was on equations and tables first

### Semantic Chunking Requirements

**Goal**: Create RAG-optimized text chunks that:
1. Respect document structure (chapters, sections, paragraphs)
2. Maintain semantic coherence (don't split mid-sentence)
3. Fit within embedding model limits (typically 512 tokens)
4. Preserve context for accurate retrieval

**Target Chunk Sizes**:
- Min: 128 tokens (avoid too-small chunks)
- Target: 384 tokens (optimal for most embedding models)
- Max: 768 tokens (hard limit for most models)
- Overlap: 64 tokens (preserve context across chunks)

### Document Structure in Chapter 4

**Hierarchical Organization**:
- Chapter title: "Chapter 4: Heat Transfer"
- Sections: Introduction, Conduction, Convection, Radiation, etc.
- Subsections: Various topics within each section
- Paragraphs: Basic text units

**Special Text Regions**:
- Headers and titles (separate from body text)
- Captions (for figures/tables - already handled by figure/table extraction)
- Footnotes and references
- Equations embedded in paragraphs (coordination with equation extraction)

---

## 🔧 TECHNICAL IMPLEMENTATION

### Agent Location
```
pipelines/rag_ingestion/packages/rag_v14_P2/
├── src/
│   ├── text/
│   │   └── text_extraction_agent.py
│   └── chunking/
│       ├── semantic_chunker.py
│       └── embedding_optimizer.py
└── tests/
```

### Semantic Chunking Algorithm

**Phase 1: Structure Detection**:
```python
# Detect document hierarchy
- Identify chapter/section headers (larger font, bold)
- Detect paragraph boundaries (line breaks, indentation)
- Identify special regions (lists, quotes, code blocks)
```

**Phase 2: Initial Chunking**:
```python
# Create semantic units
- Start with paragraphs as base units
- Merge small paragraphs if below min size
- Split large paragraphs if above max size (at sentence boundaries)
```

**Phase 3: Context Enrichment**:
```python
# Add metadata to each chunk
chunk_metadata = {
    "chunk_id": unique_id,
    "page_range": [start_page, end_page],
    "section": "4.2 Convection",
    "prev_chunk_id": previous_chunk,
    "next_chunk_id": next_chunk,
    "contains_equations": [5, 6, 7],  # Cross-reference
    "contains_tables": [2],
    "contains_figures": [3, 4]
}
```

**Phase 4: Embedding Optimization**:
```python
# Ensure chunks are embedding-ready
- Remove excessive whitespace
- Normalize special characters
- Ensure proper sentence boundaries
- Calculate token count (using tiktoken)
- Verify chunk doesn't exceed token limit
```

---

## 🎯 RAG-SPECIFIC REQUIREMENTS

### Chunk Metadata Schema

Each text chunk must include:
```json
{
  "chunk_id": "ch4_text_001",
  "content": "Heat transfer by conduction occurs when...",
  "tokens": 245,
  "page_range": [5, 6],
  "section_path": "Chapter 4 > Conduction > Fourier's Law",
  "cross_references": {
    "equations": ["1", "2"],
    "tables": [],
    "figures": ["1"]
  },
  "embedding_ready": true,
  "quality_score": 0.92
}
```

### Quality Metrics

**Chunk Quality Score** (0.0 to 1.0):
- **Coherence** (0.4 weight): Measures semantic unity within chunk
- **Completeness** (0.3 weight): No mid-sentence splits
- **Size appropriateness** (0.2 weight): Within target range
- **Context richness** (0.1 weight): Contains useful metadata

**Target**: Average quality score > 0.85

### Cross-Reference Integration

**Challenge**: Text chunks reference equations/tables/figures
**Solution**: Link text chunks with extracted objects
```python
# When text mentions "Equation (5)"
text_chunk.cross_references.equations.append("5")
# Link to equation object
equation_5.referenced_in_chunks.append(text_chunk.chunk_id)
```

---

## 🚨 CURRENT PRIORITIES

### 1. Enable Text Extraction in Pipeline
**Status**: Currently disabled
**Action**:
- Fix Docling text detection issue (missing `output` attribute)
- OR use PyMuPDF fallback for text extraction
- Enable text extraction in orchestrator

### 2. Implement Semantic Chunking
**Status**: Not yet implemented in v14
**Requirements**:
- Structure-aware chunking (respect sections)
- Token-count limiting (tiktoken)
- Cross-reference linking

### 3. Generate RAG-Ready Outputs
**Target Formats**:
- JSONL (for ChromaDB/Pinecone ingestion)
- Markdown (for human review)
- Graph format (for knowledge graph integration)

---

## 📊 EXPECTED METRICS (Chapter 4)

**Document Statistics**:
- Total pages: 34
- Estimated text: ~50,000 words
- Estimated chunks (384 tokens avg): ~180-200 chunks

**Quality Targets**:
- Chunk quality score: > 0.85 average
- Embedding readiness: 100%
- Cross-reference completeness: > 95%
- Context preservation: No mid-sentence splits

---

## 🔍 KNOWN EDGE CASES

### 1. Multi-Column Layouts
**Challenge**: Text flows in columns, need correct reading order
**Solution**: Docling handles this, PyMuPDF may require column detection

### 2. Embedded Objects
**Example**: Equations and figures embedded in paragraphs
**Handling**:
- Extract text around object
- Maintain reference to object
- Don't split paragraph at object location

### 3. Lists and Enumerations
**Challenge**: Bulleted/numbered lists should stay together
**Solution**: Detect list patterns, keep as single chunk if possible

### 4. Cross-Page Paragraphs
**Challenge**: Paragraph spans page break
**Solution**: Track page ranges, don't split at page boundary

---

## 🧪 TESTING WORKFLOW

### Enable Text Extraction
```python
# In unified_pipeline_orchestrator.py
# Ensure text extraction is enabled
```

### Run Extraction
```bash
./venv/bin/python test_with_unified_orchestrator.py
```

### Validate Chunks
```bash
# Check text chunks output
ls -lh test_output_orchestrator/text/
# Should see chunks.jsonl, chunks.md

# Validate chunk sizes
cat test_output_orchestrator/text/chunks.jsonl | jq '.tokens' | awk '{sum+=$1; count++} END {print "Avg tokens:", sum/count}'
# Should be close to 384 target

# Check quality scores
cat test_output_orchestrator/text/chunks.jsonl | jq '.quality_score' | awk '{sum+=$1; count++} END {print "Avg quality:", sum/count}'
# Should be > 0.85
```

---

## 📁 RELATED FILES

### This Pipeline Only
- `pipelines/rag_ingestion/packages/rag_v14_P2/src/text/text_extraction_agent.py`
- `pipelines/rag_ingestion/packages/rag_v14_P2/src/chunking/semantic_chunker.py`
- `pipelines/extraction/packages/detection_v14_P14/src/docling/docling_text_detector.py`

### Configuration
- `config/semantic_chunking.yaml` - Chunking parameters
- `config/embedding_config.yaml` - Embedding model settings

---

## 🚫 OUT OF SCOPE FOR THIS AI

This AI should **NOT** track or remember:
- Equation extraction (separate AI instance)
- Table extraction (separate AI instance)
- Figure extraction (separate AI instance)
- Detection algorithms (different package)
- Embedding model training (use pre-trained models)
- Vector database administration (separate concern)

**Keep this AI focused on text extraction and RAG preparation only.**

---

## 📝 STATUS TRACKING

**Current Status**: INACTIVE (text extraction not yet enabled)
**Last Task**: None
**Next Action**: Enable text extraction in pipeline, implement semantic chunking

**Status File**: `STATUS_TEXT.json` (for inter-AI communication)

---

*This CLAUDE.md file is specific to the text extraction and RAG preparation AI instance. Other content types have their own dedicated AI instances.*
