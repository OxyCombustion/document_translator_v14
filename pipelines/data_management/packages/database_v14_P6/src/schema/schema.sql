-- Document Translator V12 - Database Schema
-- Production-Ready Document Registry and Metadata System
--
-- This schema provides:
-- - Document metadata (books, papers, manuals, standards)
-- - Extraction tracking and versioning
-- - Object-level metadata (equations, tables, figures, text)
-- - Cross-references and citations
-- - Full-text search (FTS5)
--
-- Author: Claude Code
-- Date: 2025-01-21
-- Version: 1.0

-- ============================================================================
-- CORE DOCUMENTS
-- ============================================================================

-- Main documents registry
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL CHECK(doc_type IN ('book', 'paper', 'manual', 'standard', 'report', 'thesis')),
    title TEXT NOT NULL,
    authors TEXT,  -- JSON array: ["Author 1", "Author 2"]
    year INTEGER,
    isbn TEXT,
    doi TEXT,
    zotero_key TEXT UNIQUE,
    subject_areas TEXT,  -- JSON array: ["heat_transfer", "thermodynamics"]
    language TEXT DEFAULT 'en',
    abstract TEXT,
    keywords TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_doc_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_zotero_key ON documents(zotero_key);

-- Book-specific metadata
CREATE TABLE IF NOT EXISTS books (
    doc_id TEXT PRIMARY KEY,
    edition TEXT,
    publisher TEXT,
    total_chapters INTEGER,
    volume TEXT,
    series TEXT,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- Paper-specific metadata
CREATE TABLE IF NOT EXISTS papers (
    doc_id TEXT PRIMARY KEY,
    journal TEXT,
    volume TEXT,
    issue TEXT,
    pages TEXT,
    conference TEXT,
    conference_location TEXT,
    conference_date TEXT,
    peer_reviewed BOOLEAN DEFAULT 1,
    open_access BOOLEAN DEFAULT 0,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- Manual-specific metadata
CREATE TABLE IF NOT EXISTS manuals (
    doc_id TEXT PRIMARY KEY,
    manufacturer TEXT,
    model TEXT,
    manual_type TEXT,  -- 'operation', 'maintenance', 'installation', 'service'
    revision TEXT,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- Standard-specific metadata
CREATE TABLE IF NOT EXISTS standards (
    doc_id TEXT PRIMARY KEY,
    standard_body TEXT,  -- 'ASME', 'ISO', 'ASTM', 'IEC'
    standard_number TEXT,
    status TEXT,  -- 'active', 'superseded', 'withdrawn'
    supersedes TEXT,  -- doc_id of previous version
    superseded_by TEXT,  -- doc_id of newer version
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

-- ============================================================================
-- EXTRACTIONS
-- ============================================================================

-- Extraction tracking (one per chapter/document processed)
CREATE TABLE IF NOT EXISTS extractions (
    extraction_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    chapter_number INTEGER,
    chapter_title TEXT,
    section_id TEXT,  -- For papers/manuals without chapters
    pdf_file TEXT NOT NULL,
    pdf_hash TEXT NOT NULL,  -- SHA256 for change detection
    extraction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pipeline_version TEXT,
    output_directory TEXT NOT NULL,
    status TEXT DEFAULT 'complete' CHECK(status IN ('pending', 'processing', 'complete', 'partial', 'failed')),
    error_message TEXT,
    processing_time_seconds REAL,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_extraction_doc ON extractions(doc_id);
CREATE INDEX IF NOT EXISTS idx_extraction_status ON extractions(status);
CREATE INDEX IF NOT EXISTS idx_pdf_hash ON extractions(pdf_hash);

-- Extraction statistics
CREATE TABLE IF NOT EXISTS extraction_stats (
    extraction_id TEXT PRIMARY KEY,
    equations_detected INTEGER DEFAULT 0,
    equations_extracted INTEGER DEFAULT 0,
    tables_detected INTEGER DEFAULT 0,
    tables_extracted INTEGER DEFAULT 0,
    figures_detected INTEGER DEFAULT 0,
    figures_extracted INTEGER DEFAULT 0,
    text_blocks_detected INTEGER DEFAULT 0,
    text_blocks_extracted INTEGER DEFAULT 0,
    references_found INTEGER DEFAULT 0,
    detection_time_seconds REAL,
    extraction_time_seconds REAL,
    FOREIGN KEY (extraction_id) REFERENCES extractions(extraction_id) ON DELETE CASCADE
);

-- ============================================================================
-- EXTRACTED OBJECTS
-- ============================================================================

-- All extracted objects (equations, tables, figures, text blocks)
CREATE TABLE IF NOT EXISTS extracted_objects (
    object_id TEXT PRIMARY KEY,
    extraction_id TEXT NOT NULL,
    object_type TEXT NOT NULL CHECK(object_type IN ('equation', 'table', 'figure', 'text_block')),
    object_number TEXT,  -- e.g., "42", "8a", "Table 4"
    page_number INTEGER NOT NULL,
    bbox TEXT NOT NULL,  -- JSON: [x0, y0, x1, y1]
    file_path TEXT,  -- Relative to output_directory (e.g., "equations/eq_42.png")
    confidence REAL,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_id) REFERENCES extractions(extraction_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_object_extraction ON extracted_objects(extraction_id);
CREATE INDEX IF NOT EXISTS idx_object_type ON extracted_objects(object_type);
CREATE INDEX IF NOT EXISTS idx_object_number ON extracted_objects(object_number);
CREATE INDEX IF NOT EXISTS idx_object_page ON extracted_objects(page_number);

-- Object-specific metadata (flexible JSON storage)
CREATE TABLE IF NOT EXISTS object_metadata (
    object_id TEXT PRIMARY KEY,
    latex_code TEXT,  -- For equations
    caption TEXT,  -- For tables/figures
    table_data TEXT,  -- JSON: table content
    image_format TEXT,  -- For figures: 'png', 'jpg', 'svg'
    text_content TEXT,  -- For text blocks
    notes TEXT,
    metadata_json TEXT,  -- Additional flexible metadata
    FOREIGN KEY (object_id) REFERENCES extracted_objects(object_id) ON DELETE CASCADE
);

-- ============================================================================
-- CROSS-REFERENCES
-- ============================================================================

-- Cross-references within documents
CREATE TABLE IF NOT EXISTS cross_references (
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    extraction_id TEXT NOT NULL,
    source_object_id TEXT,  -- NULL if reference is from unextracted text
    source_type TEXT,  -- 'text', 'equation', 'table', 'figure', 'caption'
    source_page INTEGER,
    target_type TEXT NOT NULL,  -- 'equation', 'table', 'figure'
    target_number TEXT NOT NULL,  -- e.g., "4", "8a"
    reference_text TEXT,  -- The actual text snippet: "as shown in Table 4"
    FOREIGN KEY (extraction_id) REFERENCES extractions(extraction_id) ON DELETE CASCADE,
    FOREIGN KEY (source_object_id) REFERENCES extracted_objects(object_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_xref_extraction ON cross_references(extraction_id);
CREATE INDEX IF NOT EXISTS idx_xref_target ON cross_references(target_type, target_number);

-- Bibliography entries
CREATE TABLE IF NOT EXISTS bibliography_entries (
    entry_id TEXT PRIMARY KEY,
    extraction_id TEXT NOT NULL,
    reference_number TEXT,  -- e.g., "[1]", "[Smith2020]"
    raw_text TEXT NOT NULL,
    parsed_authors TEXT,  -- JSON array
    parsed_title TEXT,
    parsed_journal TEXT,
    parsed_year INTEGER,
    parsed_doi TEXT,
    confidence REAL,
    FOREIGN KEY (extraction_id) REFERENCES extractions(extraction_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_biblio_extraction ON bibliography_entries(extraction_id);

-- ============================================================================
-- FULL-TEXT SEARCH (FTS5)
-- ============================================================================

-- Full-text search virtual table
CREATE VIRTUAL TABLE IF NOT EXISTS extraction_search USING fts5(
    extraction_id UNINDEXED,
    doc_id UNINDEXED,
    chapter_title,
    text_content,
    table_content,
    equation_latex,
    figure_captions,
    bibliography_text,
    tokenize = 'porter unicode61'
);

-- ============================================================================
-- VECTOR EMBEDDINGS (metadata only, actual vectors in ChromaDB)
-- ============================================================================

-- Track which objects have embeddings in ChromaDB
CREATE TABLE IF NOT EXISTS embeddings (
    embedding_id TEXT PRIMARY KEY,
    object_id TEXT NOT NULL,
    embedding_type TEXT NOT NULL,  -- 'text', 'equation', 'table', 'figure_caption'
    model_name TEXT NOT NULL,  -- 'all-MiniLM-L6-v2', 'text-embedding-ada-002'
    vector_dimension INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chromadb_collection TEXT,
    chromadb_id TEXT,
    FOREIGN KEY (object_id) REFERENCES extracted_objects(object_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embedding_object ON embeddings(object_id);
CREATE INDEX IF NOT EXISTS idx_embedding_type ON embeddings(embedding_type);

-- ============================================================================
-- VALIDATION & QUALITY
-- ============================================================================

-- Completeness validation results
CREATE TABLE IF NOT EXISTS validation_reports (
    report_id TEXT PRIMARY KEY,
    extraction_id TEXT NOT NULL,
    object_type TEXT NOT NULL,
    expected_count INTEGER,
    found_count INTEGER,
    missing_objects TEXT,  -- JSON array of missing numbers
    coverage_percent REAL,
    quality_grade TEXT,  -- 'A', 'B', 'C', 'D', 'F'
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (extraction_id) REFERENCES extractions(extraction_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_validation_extraction ON validation_reports(extraction_id);

-- ============================================================================
-- SYSTEM METADATA
-- ============================================================================

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT OR IGNORE INTO schema_version (version, description)
VALUES ('1.0.0', 'Initial schema - full-featured document registry with search capabilities');

-- Pipeline version tracking
CREATE TABLE IF NOT EXISTS pipeline_versions (
    version TEXT PRIMARY KEY,
    release_date TIMESTAMP,
    features TEXT,  -- JSON array of feature descriptions
    deprecated BOOLEAN DEFAULT 0
);

-- ============================================================================
-- TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Update document timestamp on modification
CREATE TRIGGER IF NOT EXISTS update_document_timestamp
AFTER UPDATE ON documents
BEGIN
    UPDATE documents SET updated_at = CURRENT_TIMESTAMP WHERE doc_id = NEW.doc_id;
END;

-- Automatically update extraction stats when objects are added
CREATE TRIGGER IF NOT EXISTS update_extraction_stats_on_insert
AFTER INSERT ON extracted_objects
BEGIN
    INSERT OR REPLACE INTO extraction_stats (extraction_id)
    SELECT NEW.extraction_id FROM extraction_stats WHERE extraction_id = NEW.extraction_id
    UNION
    SELECT NEW.extraction_id WHERE NOT EXISTS (SELECT 1 FROM extraction_stats WHERE extraction_id = NEW.extraction_id);

    UPDATE extraction_stats
    SET equations_extracted = (SELECT COUNT(*) FROM extracted_objects WHERE extraction_id = NEW.extraction_id AND object_type = 'equation'),
        tables_extracted = (SELECT COUNT(*) FROM extracted_objects WHERE extraction_id = NEW.extraction_id AND object_type = 'table'),
        figures_extracted = (SELECT COUNT(*) FROM extracted_objects WHERE extraction_id = NEW.extraction_id AND object_type = 'figure'),
        text_blocks_extracted = (SELECT COUNT(*) FROM extracted_objects WHERE extraction_id = NEW.extraction_id AND object_type = 'text_block')
    WHERE extraction_id = NEW.extraction_id;
END;

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Complete document information with type-specific metadata
CREATE VIEW IF NOT EXISTS v_documents_complete AS
SELECT
    d.*,
    b.edition, b.publisher, b.total_chapters,
    p.journal, p.volume, p.issue, p.pages, p.conference,
    m.manufacturer, m.model, m.manual_type,
    s.standard_body, s.standard_number, s.status
FROM documents d
LEFT JOIN books b ON d.doc_id = b.doc_id
LEFT JOIN papers p ON d.doc_id = p.doc_id
LEFT JOIN manuals m ON d.doc_id = m.doc_id
LEFT JOIN standards s ON d.doc_id = s.doc_id;

-- Extraction summary with document context
CREATE VIEW IF NOT EXISTS v_extraction_summary AS
SELECT
    e.extraction_id,
    e.doc_id,
    d.title AS document_title,
    d.doc_type,
    e.chapter_number,
    e.chapter_title,
    e.pdf_file,
    e.extraction_date,
    e.status,
    es.equations_extracted,
    es.tables_extracted,
    es.figures_extracted,
    es.text_blocks_extracted,
    e.output_directory
FROM extractions e
JOIN documents d ON e.doc_id = d.doc_id
LEFT JOIN extraction_stats es ON e.extraction_id = es.extraction_id;

-- Object counts by document
CREATE VIEW IF NOT EXISTS v_document_object_counts AS
SELECT
    d.doc_id,
    d.title,
    d.doc_type,
    COUNT(DISTINCT e.extraction_id) AS extraction_count,
    SUM(es.equations_extracted) AS total_equations,
    SUM(es.tables_extracted) AS total_tables,
    SUM(es.figures_extracted) AS total_figures,
    SUM(es.text_blocks_extracted) AS total_text_blocks
FROM documents d
LEFT JOIN extractions e ON d.doc_id = e.doc_id
LEFT JOIN extraction_stats es ON e.extraction_id = es.extraction_id
GROUP BY d.doc_id, d.title, d.doc_type;
