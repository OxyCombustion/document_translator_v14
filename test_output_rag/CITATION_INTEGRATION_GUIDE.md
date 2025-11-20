# Citation Graph Integration Guide

**Purpose**: Guide for integrating citation graph into Pipeline 3 (Data Management)
**Target**: Vector database enrichment with citation relationships
**Status**: Ready for implementation

---

## Overview

The citation graph enables **citation-aware retrieval** in your RAG system by:
1. Enriching chunks with citation metadata
2. Building citation relationships in the vector database
3. Enabling cross-reference queries
4. Validating AI-generated responses

---

## Citation Graph Structure

### File Location
```
/home/thermodynamics/document_translator_v14/test_output_rag/citation_graph.json
```

### Data Structure

```json
{
  "document": "test_data/Ch-04_Heat_Transfer.pdf",
  "total_chunks": 34,
  "citation_stats": { /* aggregate statistics */ },
  "citations_by_chunk": { /* chunk_id -> citations */ },
  "citations_by_object": { /* object_type -> object_id -> [chunk_ids] */ },
  "cross_references": [ /* detailed citation records */ ],
  "validation": { /* validation results */ }
}
```

---

## Integration Methods

### Method 1: Chunk Metadata Enrichment (Recommended)

**Use Case**: Add citation metadata to each chunk before embedding

```python
import json

# Load citation graph
def load_citation_graph(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Enrich chunk with citation metadata
def enrich_chunk_with_citations(chunk, citation_graph):
    """Add citation information to chunk metadata"""
    chunk_id = chunk['chunk_id']

    # Get citations for this chunk
    if chunk_id in citation_graph['citations_by_chunk']:
        citations = citation_graph['citations_by_chunk'][chunk_id]

        # Add to metadata
        chunk['metadata']['citations'] = {
            'figures': citations['figures'],
            'tables': citations['tables'],
            'equations': citations['equations'],
            'chapters': citations['chapters'],
            'references': citations['references']
        }

        # Add citation counts
        chunk['metadata']['citation_count'] = sum(len(v) for v in citations.values())
        chunk['metadata']['has_citations'] = chunk['metadata']['citation_count'] > 0

        # Add citation density flag (high = >6 citations)
        chunk['metadata']['is_citation_dense'] = chunk['metadata']['citation_count'] > 6

        # Add specific flags
        chunk['metadata']['has_figures'] = len(citations['figures']) > 0
        chunk['metadata']['has_tables'] = len(citations['tables']) > 0
        chunk['metadata']['has_equations'] = len(citations['equations']) > 0

    return chunk

# Usage example
citation_graph = load_citation_graph('citation_graph.json')

# Process each chunk
for chunk in chunks:
    enriched_chunk = enrich_chunk_with_citations(chunk, citation_graph)
    # Now embed and store in vector database
```

**Benefits**:
- Enables filtering: "find chunks with figures"
- Enables ranking: prioritize citation-dense chunks
- Enables faceting: filter by object type

---

### Method 2: Citation Edge Storage

**Use Case**: Store citation relationships as edges in graph database or metadata

```python
def create_citation_edges(citation_graph):
    """Create edge list for graph database"""
    edges = []

    for cross_ref in citation_graph['cross_references']:
        edge = {
            'source': cross_ref['from_chunk'],
            'target': cross_ref['to_object'],
            'type': 'cites',
            'object_type': cross_ref['object_type'],
            'object_id': cross_ref['object_id'],
            'weight': cross_ref['mention_count']
        }
        edges.append(edge)

    return edges

# Create edges
edges = create_citation_edges(citation_graph)

# Store in graph database (e.g., Neo4j)
for edge in edges:
    # CREATE (chunk)-[CITES {weight: X}]->(object)
    pass
```

**Benefits**:
- Enables graph traversal: "find all chunks connected to Figure 11"
- Enables path queries: "shortest path from chunk A to chunk B via citations"
- Enables clustering: identify citation communities

---

### Method 3: Reverse Index for Object Lookup

**Use Case**: Query "which chunks discuss Figure 11?"

```python
def build_object_index(citation_graph):
    """Build reverse index: object -> chunks"""
    index = {}

    for obj_type, objects in citation_graph['citations_by_object'].items():
        for obj_id, chunk_ids in objects.items():
            key = f"{obj_type}_{obj_id}"
            index[key] = {
                'type': obj_type,
                'id': obj_id,
                'chunks': chunk_ids,
                'count': len(chunk_ids)
            }

    return index

# Usage
object_index = build_object_index(citation_graph)

# Query: which chunks cite Figure 11?
fig11_info = object_index['figure_11']
print(f"Figure 11 cited in {fig11_info['count']} chunks: {fig11_info['chunks']}")
```

**Benefits**:
- Fast object → chunks lookup
- Enables "related chunks" queries
- Supports co-citation analysis

---

### Method 4: Co-Citation Analysis

**Use Case**: Find chunks that cite similar objects

```python
def find_related_chunks_by_cocitation(chunk_id, citation_graph, threshold=2):
    """Find chunks that cite similar objects"""
    # Get citations for target chunk
    target_citations = citation_graph['citations_by_chunk'][chunk_id]
    target_objects = set()
    for obj_type, refs in target_citations.items():
        for ref in refs:
            target_objects.add(f"{obj_type}_{ref}")

    # Find chunks with overlapping citations
    related_chunks = {}

    for other_chunk_id, other_citations in citation_graph['citations_by_chunk'].items():
        if other_chunk_id == chunk_id:
            continue

        # Get objects cited in other chunk
        other_objects = set()
        for obj_type, refs in other_citations.items():
            for ref in refs:
                other_objects.add(f"{obj_type}_{ref}")

        # Calculate overlap
        overlap = target_objects & other_objects
        if len(overlap) >= threshold:
            related_chunks[other_chunk_id] = {
                'overlap_count': len(overlap),
                'shared_objects': list(overlap)
            }

    # Sort by overlap
    sorted_related = sorted(related_chunks.items(), key=lambda x: x[1]['overlap_count'], reverse=True)

    return sorted_related

# Usage
related = find_related_chunks_by_cocitation('unit_001_page_009', citation_graph)
for chunk_id, info in related[:5]:
    print(f"{chunk_id}: {info['overlap_count']} shared citations")
```

**Benefits**:
- Discover semantically related chunks
- Improve retrieval with citation similarity
- Build recommendation system: "users who read this also read..."

---

## ChromaDB Integration Example

### Enriched Metadata Schema

```python
import chromadb

# Initialize ChromaDB
client = chromadb.Client()
collection = client.create_collection("heat_transfer_chapter4")

# Load citation graph
citation_graph = load_citation_graph('citation_graph.json')

# Add chunks with citation metadata
for chunk in chunks:
    # Enrich with citations
    enriched_chunk = enrich_chunk_with_citations(chunk, citation_graph)

    # Add to ChromaDB
    collection.add(
        ids=[chunk['chunk_id']],
        documents=[chunk['text']],
        metadatas=[{
            'chunk_id': chunk['chunk_id'],
            'page_number': chunk['page_number'],
            'unit_id': chunk['unit_id'],

            # Citation metadata
            'citation_count': enriched_chunk['metadata']['citation_count'],
            'has_figures': enriched_chunk['metadata']['has_figures'],
            'has_tables': enriched_chunk['metadata']['has_tables'],
            'has_equations': enriched_chunk['metadata']['has_equations'],
            'is_citation_dense': enriched_chunk['metadata']['is_citation_dense'],

            # Lists (stored as JSON strings in ChromaDB)
            'cited_figures': json.dumps(enriched_chunk['metadata']['citations']['figures']),
            'cited_tables': json.dumps(enriched_chunk['metadata']['citations']['tables']),
            'cited_equations': json.dumps(enriched_chunk['metadata']['citations']['equations']),
        }]
    )
```

### Query Examples

```python
# Query 1: Find chunks that cite Figure 11
results = collection.query(
    query_texts=["heat transfer"],
    where={"cited_figures": {"$contains": "11"}},
    n_results=10
)

# Query 2: Find citation-dense chunks (>6 citations)
results = collection.query(
    query_texts=["thermodynamics"],
    where={"is_citation_dense": True},
    n_results=10
)

# Query 3: Find chunks with equations
results = collection.query(
    query_texts=["calculation"],
    where={"has_equations": True},
    n_results=10
)

# Query 4: Combine semantic + citation filtering
results = collection.query(
    query_texts=["boundary layer flow"],
    where={
        "$and": [
            {"has_figures": True},
            {"citation_count": {"$gte": 3}}
        ]
    },
    n_results=10
)
```

---

## RAG Query Enhancement

### Enhanced Retrieval Pipeline

```python
def citation_aware_retrieval(query, citation_graph, collection, prefer_cited=True):
    """Retrieve chunks with citation-aware ranking"""

    # Step 1: Semantic search
    results = collection.query(
        query_texts=[query],
        n_results=20  # Get more candidates
    )

    # Step 2: Re-rank with citation information
    ranked_results = []

    for i, chunk_id in enumerate(results['ids'][0]):
        chunk = results['documents'][0][i]
        metadata = results['metadatas'][0][i]

        # Calculate citation score
        citation_score = 0
        if prefer_cited:
            # Prefer chunks with citations
            citation_score += metadata.get('citation_count', 0) * 0.1

            # Extra boost for specific types
            if metadata.get('has_equations', False):
                citation_score += 0.5  # Math content is important
            if metadata.get('has_figures', False):
                citation_score += 0.3  # Visual explanations
            if metadata.get('has_tables', False):
                citation_score += 0.2  # Tabular data

        # Combine semantic distance + citation score
        semantic_score = 1.0 - results['distances'][0][i]  # Convert distance to similarity
        final_score = semantic_score + citation_score

        ranked_results.append({
            'chunk_id': chunk_id,
            'text': chunk,
            'metadata': metadata,
            'semantic_score': semantic_score,
            'citation_score': citation_score,
            'final_score': final_score
        })

    # Sort by final score
    ranked_results.sort(key=lambda x: x['final_score'], reverse=True)

    return ranked_results[:10]  # Return top 10
```

---

## Validation & Hallucination Detection

### Validate AI Responses

```python
def validate_citations_in_response(response_text, citation_graph):
    """Check if AI response contains valid citations"""
    issues = []

    # Extract citations from response (reuse regex patterns)
    from build_citation_graph import CitationExtractor
    extractor = CitationExtractor()
    mentioned_citations = extractor.extract_citations(response_text)

    # Check each citation type
    for obj_type, refs in mentioned_citations.items():
        if obj_type in citation_graph['citations_by_object']:
            valid_refs = set(citation_graph['citations_by_object'][obj_type].keys())

            for ref in refs:
                if ref not in valid_refs:
                    issues.append({
                        'type': 'invalid_citation',
                        'object_type': obj_type,
                        'object_id': ref,
                        'message': f"{obj_type.capitalize()} {ref} does not exist in document"
                    })

    return issues

# Usage
response = "According to Figure 11 and Table 99, heat transfer..."
issues = validate_citations_in_response(response, citation_graph)

if issues:
    print("⚠️ Potential hallucinations detected:")
    for issue in issues:
        print(f"  - {issue['message']}")
```

---

## Performance Considerations

### Indexing Strategy

1. **Chunk metadata**: Store with vectors (fast filtering)
2. **Object index**: Cache in memory (fast lookup)
3. **Co-citation matrix**: Pre-compute for top objects (fast similarity)

### Memory Requirements

- Citation graph JSON: 45 KB
- Object index (in memory): ~10 KB
- Co-citation matrix (if pre-computed): ~50 KB

**Total**: ~105 KB (negligible overhead)

### Query Performance

- Metadata filtering: O(n) with ChromaDB indexing → ~ms
- Object lookup: O(1) with hash index → <1ms
- Co-citation: O(k) where k = chunks per object → ~ms

---

## Testing Checklist

### Integration Tests

- [ ] Load citation graph from JSON
- [ ] Enrich all chunks with citation metadata
- [ ] Verify metadata fields are populated
- [ ] Test object index lookup (e.g., Figure 11 → chunks)
- [ ] Test co-citation analysis
- [ ] Test citation filtering in vector DB queries
- [ ] Test citation-aware re-ranking
- [ ] Test validation with known good/bad citations

### Example Test Cases

```python
def test_citation_enrichment():
    # Test chunk with known citations
    chunk = {'chunk_id': 'unit_001_page_009', 'text': '...'}
    enriched = enrich_chunk_with_citations(chunk, citation_graph)

    # Verify
    assert enriched['metadata']['has_citations'] == True
    assert 'figure' in enriched['metadata']['citations']
    assert '11' in enriched['metadata']['citations']['figures']

def test_object_lookup():
    index = build_object_index(citation_graph)

    # Figure 11 should be in 5 chunks
    fig11 = index['figure_11']
    assert fig11['count'] == 5
    assert 'unit_001_page_009' in fig11['chunks']

def test_validation():
    # Valid citation
    issues = validate_citations_in_response("See Figure 11", citation_graph)
    assert len(issues) == 0

    # Invalid citation
    issues = validate_citations_in_response("See Figure 999", citation_graph)
    assert len(issues) == 1
    assert issues[0]['type'] == 'invalid_citation'
```

---

## Migration Path

### Phase 1: Basic Integration (Week 1)
1. Load citation graph
2. Add citation counts to chunk metadata
3. Test retrieval with citation filtering

### Phase 2: Enhanced Retrieval (Week 2)
4. Implement citation-aware re-ranking
5. Add co-citation analysis
6. Test with real queries

### Phase 3: Validation (Week 3)
7. Add response validation
8. Implement hallucination detection
9. A/B test citation-aware vs. baseline retrieval

---

## Success Metrics

### Retrieval Quality
- **Precision**: % of retrieved chunks with relevant citations
- **Recall**: % of citation-dense chunks retrieved for technical queries
- **MRR**: Mean reciprocal rank of chunks with target objects

### Response Quality
- **Citation accuracy**: % of AI responses with valid citations
- **Hallucination rate**: % of responses with invalid citations
- **User satisfaction**: A/B test citation-aware vs. baseline

---

## Troubleshooting

### Common Issues

**Issue**: Citation metadata not appearing in ChromaDB
- **Cause**: ChromaDB doesn't support list fields directly
- **Solution**: Store as JSON strings, parse on retrieval

**Issue**: Slow citation filtering
- **Cause**: String matching on JSON fields
- **Solution**: Use boolean flags (has_figures, has_tables) for filtering

**Issue**: Co-citation analysis too slow
- **Cause**: Recomputing for every query
- **Solution**: Pre-compute co-citation matrix for top 100 chunks

---

## Example: Full Integration Script

See `/home/thermodynamics/document_translator_v14/test_output_rag/citation_integration_example.py` (to be created) for complete working example.

---

## References

- Citation Graph: `/home/thermodynamics/document_translator_v14/test_output_rag/citation_graph.json`
- Analysis: `/home/thermodynamics/document_translator_v14/test_output_rag/citation_graph_analysis.md`
- Statistics: `/home/thermodynamics/document_translator_v14/test_output_rag/citation_statistics.md`

---

**Last Updated**: 2025-11-19
**Status**: Ready for Pipeline 3 integration
**Next Step**: Implement Phase 1 (basic integration) in data management pipeline
