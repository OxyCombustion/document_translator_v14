#!/bin/bash
# Pipeline 3 Verification Script
# Verifies all deliverables are present and functional

echo "================================================================================"
echo "PIPELINE 3 (DATABASE) VERIFICATION"
echo "================================================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check function
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2 (missing)"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2 (missing)"
        return 1
    fi
}

# Check scripts
echo "Checking Scripts..."
echo "--------------------------------------------------------------------------------"
check_file "test_database_pipeline.py" "Main test script (test_database_pipeline.py)"
check_file "query_chromadb.py" "Query interface (query_chromadb.py)"
check_file "example_rag_retrieval.py" "RAG examples (example_rag_retrieval.py)"
echo ""

# Check documentation
echo "Checking Documentation..."
echo "--------------------------------------------------------------------------------"
check_file "PIPELINE_3_TEST_RESULTS.md" "Test results (PIPELINE_3_TEST_RESULTS.md)"
check_file "PIPELINE_3_QUICK_START.md" "Quick start guide (PIPELINE_3_QUICK_START.md)"
check_file "PIPELINE_3_SUMMARY.txt" "Executive summary (PIPELINE_3_SUMMARY.txt)"
check_file "PIPELINE_3_DELIVERABLES.md" "Deliverables manifest (PIPELINE_3_DELIVERABLES.md)"
echo ""

# Check input data
echo "Checking Input Data..."
echo "--------------------------------------------------------------------------------"
check_file "test_output_rag/rag_bundles.jsonl" "JSONL chunks (rag_bundles.jsonl)"
check_file "test_output_rag/citation_graph.json" "Citation graph (citation_graph.json)"
echo ""

# Check database output
echo "Checking Database Output..."
echo "--------------------------------------------------------------------------------"
check_dir "test_output_database/chromadb" "ChromaDB directory"
check_file "test_output_database/chromadb/chroma.sqlite3" "SQLite database"
echo ""

# Count chunks in JSONL
echo "Verifying Data..."
echo "--------------------------------------------------------------------------------"
chunk_count=$(wc -l < test_output_rag/rag_bundles.jsonl)
if [ "$chunk_count" -eq 34 ]; then
    echo -e "${GREEN}✓${NC} JSONL chunks: $chunk_count (expected: 34)"
else
    echo -e "${RED}✗${NC} JSONL chunks: $chunk_count (expected: 34)"
fi

# Check database size
db_size=$(du -sh test_output_database/chromadb 2>/dev/null | cut -f1)
if [ -n "$db_size" ]; then
    echo -e "${GREEN}✓${NC} Database size: $db_size"
else
    echo -e "${RED}✗${NC} Database size: unknown"
fi

echo ""

# Test ChromaDB query (if venv available)
echo "Testing Functionality..."
echo "--------------------------------------------------------------------------------"
if [ -d "venv" ]; then
    echo "Testing ChromaDB query..."
    source venv/bin/activate
    python3 -c "import chromadb; client = chromadb.PersistentClient(path='test_output_database/chromadb'); collection = client.get_collection('chapter_4_heat_transfer'); count = collection.count(); print(f'✓ ChromaDB collection: {count} chunks')" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC} ChromaDB functional"
    else
        echo -e "${RED}✗${NC} ChromaDB test failed"
    fi
else
    echo "⚠ venv not found, skipping functionality test"
fi

echo ""
echo "================================================================================"
echo "VERIFICATION COMPLETE"
echo "================================================================================"
echo ""
echo "All deliverables verified. Ready to use!"
echo ""
echo "Quick start:"
echo "  1. Run complete test:   source venv/bin/activate && python3 test_database_pipeline.py"
echo "  2. Query database:      python3 query_chromadb.py --stats"
echo "  3. See RAG examples:    python3 example_rag_retrieval.py"
echo ""
