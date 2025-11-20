# End-to-End Integration Test Guide

## Overview

The `test_integration_e2e.py` script provides comprehensive validation of the complete Document Translator v14 workflow, from PDF input to queryable vector database.

## What It Tests

### 1. Pipeline Execution (Sequential)
- **Pipeline 1: Extraction** - Extracts equations, tables, figures, text from PDF
- **Pipeline 2: RAG Ingestion** - Creates semantic chunks and citation graph
- **Pipeline 3: Database Loading** - Loads chunks into ChromaDB with metadata enrichment

### 2. Data Contract Validation
- **Extraction → RAG**: Validates JSON structure and required fields
- **RAG → Database**: Validates JSONL format and citation graph structure
- **Data Integrity**: Ensures chunk counts and citations are preserved across pipelines

### 3. Query Retrieval Testing
- **5 Semantic Queries**: Tests natural language search
- **2 Citation Filters**: Tests filtering by figure/equation references
- **Source Tracing**: Validates each result can be traced back to PDF page

### 4. Performance Metrics
- Total processing time
- Per-pipeline breakdown
- Throughput (pages/minute)
- Database size and statistics

## Quick Start

### Prerequisites

1. All three pipeline test scripts must exist:
   - `test_with_unified_orchestrator.py`
   - `test_rag_pipeline.py`
   - `test_database_pipeline.py`

2. Test data:
   - PDF: `test_data/Ch-04_Heat_Transfer.pdf`
   - YOLO model: `/home/thermodynamics/document_translator_v12/models/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt`

3. Required libraries:
   - ChromaDB
   - All pipeline dependencies

### Run the Test

```bash
# Simple execution
python3 test_integration_e2e.py

# With output redirection
python3 test_integration_e2e.py 2>&1 | tee test_log.txt

# Check exit code
python3 test_integration_e2e.py && echo "SUCCESS" || echo "FAILED"
```

### Expected Output

```
################################################################################
# END-TO-END INTEGRATION TEST
################################################################################
Document Translator v14
Test Date: 2025-11-19 XX:XX:XX

================================================================================
Prerequisites Check
================================================================================
✅ PDF found: test_data/Ch-04_Heat_Transfer.pdf
✅ Model found: /home/.../doclayout_yolo_docstructbench_imgsz1280_2501.pt
✅ Test script found: test_with_unified_orchestrator.py
✅ Test script found: test_rag_pipeline.py
✅ Test script found: test_database_pipeline.py

================================================================================
PIPELINE 1: EXTRACTION (PDF → JSON)
================================================================================
🔄 Running Extraction Pipeline...
✅ Extraction Pipeline completed in XXXs

Extraction Metrics:
  Duration: XXXs
  Total objects: 162
  Equations: 106
  Tables: 14

[... similar output for Pipeline 2 and 3 ...]

================================================================================
DATA CONTRACT VALIDATION: Extraction → RAG
================================================================================
✅ Extraction → RAG contract validated

[... similar output for other validations ...]

================================================================================
QUERY RETRIEVAL TESTING
================================================================================
Testing collection: chapter_4_heat_transfer
Total chunks: 34

Semantic Query Tests
--------------------------------------------------------------------------------
[Test 1/5] Should find equations and heat transfer theory
Query: 'What is Newton's law of cooling?'
✅ Found 3 results (expected ≥2)
✅ Source tracing validated

[... similar output for other tests ...]

================================================================================
END-TO-END INTEGRATION TEST - Document Translator v14
================================================================================
Test Date: 2025-11-19 XX:XX:XX
Test Document: Ch-04_Heat_Transfer.pdf (34 pages)

PIPELINE EXECUTION RESULTS
--------------------------------------------------------------------------------
PIPELINE 1: EXTRACTION
  Status: ✅ PASS
  Duration: 555.4s (9.3m)
  Objects extracted: 162
  Equations: 106
  Tables: 14

PIPELINE 2: RAG INGESTION
  Status: ✅ PASS
  Duration: 0.9s
  Chunks created: 34
  Total characters: 130,350
  Citations extracted: 386

PIPELINE 3: DATABASE LOADING
  Status: ✅ PASS
  Duration: 0.9s
  Chunks inserted: 34
  Database size: 1.23 MB

DATA FLOW VALIDATION
--------------------------------------------------------------------------------
  Extraction → RAG: ✅ PASS
  RAG → Database: ✅ PASS
  Data Integrity: ✅ PASS

QUERY RETRIEVAL TESTING
--------------------------------------------------------------------------------
  Semantic queries: 5/5 passed
    ✅ Should find equations and heat transfer theory
    ✅ Should find technical content about convection
    ✅ Should find relevant sections on radiation
    ✅ Should find equations related to conductivity
    ✅ Should find application sections
  Citation filters: 2/2 passed
  Source tracing: ✅ PASS

PERFORMANCE SUMMARY
--------------------------------------------------------------------------------
  Total duration: 9.3m (557.2s)
  Throughput: 3.66 pages/minute

  Time breakdown:
    Extraction: 555.4s (99.7%)
    Rag: 0.9s (0.2%)
    Database: 0.9s (0.2%)

================================================================================
OVERALL STATUS: ✅ INTEGRATION TEST PASSED
================================================================================

✅ All integration tests passed!
```

## Output Files

All outputs are saved to `test_output_integration/`:

- `integration_report.txt` - Human-readable summary (copy of console output)
- `integration_summary.json` - Machine-readable results for automation

## Test Queries

### Semantic Queries

1. **"What is Newton's law of cooling?"**
   - Target: Equations and heat transfer theory
   - Expected: 2+ results with equation references

2. **"convection heat transfer coefficient"**
   - Target: Technical content about convection
   - Expected: 2+ results from convection sections

3. **"radiation heat transfer"**
   - Target: Radiation theory sections
   - Expected: 2+ results

4. **"thermal conductivity equations"**
   - Target: Conductivity equations
   - Expected: 2+ results

5. **"heat exchanger design"**
   - Target: Application sections
   - Expected: 1+ results

### Citation Filter Queries

1. **Filter by Figure 11**
   - Expected: 3+ chunks that reference Figure 11

2. **Filter by Equation 1**
   - Expected: 2+ chunks that reference Equation 1

## Exit Codes

- `0` - **SUCCESS**: All tests passed
- `1` - **FAILURE**: One or more tests failed

## Success Criteria

The test passes only if ALL of the following are true:

- ✅ Pipeline 1 (Extraction) completes successfully
- ✅ Pipeline 2 (RAG) completes successfully
- ✅ Pipeline 3 (Database) completes successfully
- ✅ Extraction → RAG data contract is valid
- ✅ RAG → Database data contract is valid
- ✅ Data integrity is maintained (chunk counts match)
- ✅ All 5 semantic queries return expected results
- ✅ All 2 citation filter queries return expected results
- ✅ Source tracing is valid for all results

## Troubleshooting

### "Pipeline X failed, aborting integration test"

**Solution**: Run the individual pipeline test script to see detailed error:

```bash
# For extraction failures
python3 test_with_unified_orchestrator.py

# For RAG failures
python3 test_rag_pipeline.py

# For database failures
python3 test_database_pipeline.py
```

### "Data contract validation failed"

**Cause**: Output format from one pipeline doesn't match expected input for next pipeline.

**Solution**:
1. Check the error message for specific missing fields
2. Verify pipeline output directories exist
3. Check JSON/JSONL file formats

### "Query test failed - found 0 results"

**Cause**: ChromaDB collection is empty or not properly created.

**Solution**:
1. Verify Pipeline 3 completed successfully
2. Check `test_output_database/chromadb` exists
3. Run database test script individually

### "Source tracing validation failed"

**Cause**: Metadata is missing or invalid in query results.

**Solution**:
1. Check that citation graph was created (Pipeline 2)
2. Verify metadata enrichment in Pipeline 3
3. Ensure page numbers are valid (1-34 for test document)

## Performance Expectations

Based on typical runs with Ch-04_Heat_Transfer.pdf (34 pages):

| Pipeline | Expected Duration | % of Total |
|----------|------------------|------------|
| Extraction | ~555s (9.3m) | ~99.7% |
| RAG | ~1s | ~0.2% |
| Database | ~1s | ~0.2% |
| **Total** | **~557s (9.3m)** | **100%** |

**Throughput**: ~3.6 pages/minute

Note: Extraction dominates processing time due to YOLO detection and OCR.

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Integration Test
on: [push, pull_request]

jobs:
  integration-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run integration test
        run: |
          python3 test_integration_e2e.py
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: integration-test-results
          path: test_output_integration/
```

### Jenkins Example

```groovy
stage('Integration Test') {
    steps {
        sh 'python3 test_integration_e2e.py'
    }
    post {
        always {
            archiveArtifacts artifacts: 'test_output_integration/*'
            junit 'test_output_integration/integration_summary.json'
        }
    }
}
```

## Advanced Usage

### Custom Test Document

Edit the script configuration:

```python
# In test_integration_e2e.py
PDF_PATH = Path("path/to/your/document.pdf")
EXPECTED_PAGES = 42  # Update based on your document
```

### Custom Queries

Add to the `TEST_QUERIES` list:

```python
TEST_QUERIES = [
    # ... existing queries ...
    {
        "query": "your custom query",
        "description": "What this should find",
        "expected_min_results": 2
    }
]
```

### Adjust Timeouts

Modify subprocess timeouts for large documents:

```python
# In run_extraction_pipeline()
timeout=1800  # 30 minutes for large PDFs
```

## Best Practices

1. **Run After Code Changes**: Always run integration test before committing
2. **Check Exit Code**: Use in pre-commit hooks or CI/CD
3. **Review Reports**: Don't just check pass/fail - review metrics
4. **Monitor Performance**: Track throughput over time
5. **Keep Test Data Consistent**: Use same PDF for reproducibility

## Maintenance

### When to Update Test

- Pipeline code changes
- Data contract changes
- New query types added
- Performance regression detected

### Updating Expected Values

```python
# In test_integration_e2e.py
EXPECTED_OBJECTS_MIN = 160  # Adjust based on extraction improvements
EXPECTED_CHUNKS_MIN = 30    # Adjust based on chunking strategy
```

## FAQ

**Q: How long should the test take?**
A: ~9-10 minutes for the 34-page test document (mostly extraction time).

**Q: Can I run pipelines individually?**
A: Yes, the test is designed for that. If Pipeline 1 fails, you can fix it and re-run without starting over.

**Q: Does the test modify existing data?**
A: No, it uses separate output directories (`test_output_integration/`).

**Q: Can I run this on a different document?**
A: Yes, edit the configuration section at the top of the script.

**Q: What if ChromaDB is already running?**
A: The test uses a new collection each time (deletes existing if present).

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run individual pipeline tests to isolate the issue
3. Review the detailed error messages in console output
4. Check `test_output_integration/integration_report.txt`

## Version History

- **v1.0** (2025-11-19) - Initial release
  - Sequential pipeline execution
  - Data contract validation
  - Query retrieval testing
  - Performance metrics
  - Source tracing validation

---

**Last Updated**: 2025-11-19
