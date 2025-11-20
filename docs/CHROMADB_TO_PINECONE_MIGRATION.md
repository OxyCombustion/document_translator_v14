# ChromaDB to Pinecone Migration Guide

**Complete guide for migrating from local ChromaDB to cloud-based Pinecone vector database**

**Date**: 2025-11-20
**Status**: Production-ready migration path
**Estimated Time**: 2-4 hours (depends on data size)

---

## Table of Contents

1. [Overview](#overview)
2. [When to Migrate](#when-to-migrate)
3. [Pre-Migration Checklist](#pre-migration-checklist)
4. [Migration Strategy](#migration-strategy)
5. [Step-by-Step Migration](#step-by-step-migration)
6. [Cost Estimation](#cost-estimation)
7. [Validation and Testing](#validation-and-testing)
8. [Rollback Plan](#rollback-plan)
9. [Post-Migration Optimization](#post-migration-optimization)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What This Guide Covers

This guide walks you through migrating your vector database from ChromaDB (local, SQLite-backed) to Pinecone (cloud-based, serverless).

### Migration Benefits

| Feature | ChromaDB | Pinecone |
|---------|----------|----------|
| **Deployment** | Local only | Cloud (auto-scaling) |
| **Scalability** | Limited by disk | Unlimited |
| **Availability** | Single machine | 99.9% SLA |
| **Hybrid Search** | No | Yes (sparse + dense) |
| **Metadata Filtering** | Basic | Advanced (pre-filter) |
| **Cost** | Free (local compute) | Pay-per-use |
| **Latency** | <10ms (local) | 50-100ms (network) |
| **Setup Complexity** | Low | Medium |

### Migration Risks

- **Cost**: Pinecone has monthly costs (~$22/month for 10k chunks)
- **Network Dependency**: Requires internet connection
- **API Key Management**: Requires secure key storage
- **Latency**: Network latency adds 40-90ms per query

---

## When to Migrate

### Migrate to Pinecone When:

✅ **You need production scalability** (>100k vectors)
✅ **You need high availability** (99.9% uptime SLA)
✅ **You need hybrid search** (semantic + keyword)
✅ **You need multi-user access** (team deployment)
✅ **You need cloud deployment** (serverless, no infra management)

### Stay with ChromaDB When:

✅ **You're in development/testing** (local iteration)
✅ **You have <10k vectors** (ChromaDB performs well)
✅ **You want zero ongoing costs** (local compute only)
✅ **You need <10ms latency** (local is faster)
✅ **You want full data control** (no cloud dependency)

---

## Pre-Migration Checklist

### 1. Verify Current ChromaDB Setup

```bash
# Check ChromaDB location
ls -lh test_output_database/chromadb/

# Check collection stats
python query_chromadb.py --stats

# Expected output:
# Collection: chapter_4_heat_transfer
# Total vectors: 34
# Dimension: 384
# Database size: 3.01 MB
```

### 2. Get Pinecone API Key

1. Sign up at [https://www.pinecone.io](https://www.pinecone.io)
2. Create a new project
3. Generate API key
4. Save key securely:

```bash
# Add to environment
export PINECONE_API_KEY="your-api-key-here"

# Or add to ~/.bashrc for persistence
echo 'export PINECONE_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### 3. Install Pinecone Client

```bash
# Install Pinecone Python client
pip install pinecone-client

# Verify installation
python -c "import pinecone; print('Pinecone installed')"
```

### 4. Backup ChromaDB Data

```bash
# Create backup
mkdir -p backups/chromadb_$(date +%Y%m%d)
cp -r test_output_database/chromadb backups/chromadb_$(date +%Y%m%d)/

# Verify backup
ls -lh backups/chromadb_$(date +%Y%m%d)/
```

### 5. Test Pinecone Connection

```bash
# Test with mock mode first
python test_database_pipeline_pinecone.py --mock

# Test with real API key
python test_database_pipeline_pinecone.py
```

---

## Migration Strategy

### Option 1: Full Migration (Recommended)

**Best for**: First-time migration, small datasets (<10k vectors)

**Process**:
1. Export all vectors from ChromaDB
2. Create Pinecone index
3. Batch upsert to Pinecone
4. Validate data integrity
5. Switch application to Pinecone

**Time**: 2-4 hours
**Risk**: Low (ChromaDB remains intact)

### Option 2: Incremental Migration

**Best for**: Large datasets (>10k vectors), zero-downtime required

**Process**:
1. Create Pinecone index
2. Migrate data in batches (daily/weekly)
3. Run dual-write to both databases
4. Validate Pinecone data
5. Switch reads to Pinecone
6. Stop writes to ChromaDB

**Time**: 1-2 weeks
**Risk**: Medium (requires dual-write logic)

### Option 3: Parallel Deployment

**Best for**: Testing, gradual rollout

**Process**:
1. Deploy Pinecone alongside ChromaDB
2. Route 10% traffic to Pinecone
3. Monitor performance and costs
4. Gradually increase Pinecone traffic
5. Decommission ChromaDB when at 100%

**Time**: 2-4 weeks
**Risk**: Low (easy rollback)

---

## Step-by-Step Migration

### Phase 1: Export ChromaDB Data

**Step 1.1: Export Vectors**

```python
#!/usr/bin/env python3
"""Export ChromaDB vectors to JSON for migration."""

import json
import chromadb
from pathlib import Path

# Connect to ChromaDB
client = chromadb.PersistentClient(path="test_output_database/chromadb")
collection = client.get_collection("chapter_4_heat_transfer")

# Get all vectors
results = collection.get(include=['embeddings', 'documents', 'metadatas'])

# Export to JSON
export_data = {
    'vectors': [],
    'metadata': {
        'collection_name': 'chapter_4_heat_transfer',
        'dimension': 384,
        'count': len(results['ids']),
        'exported_at': '2025-11-20'
    }
}

for i, chunk_id in enumerate(results['ids']):
    export_data['vectors'].append({
        'id': chunk_id,
        'embedding': results['embeddings'][i],
        'document': results['documents'][i],
        'metadata': results['metadatas'][i]
    })

# Save to file
output_file = Path('chromadb_export.json')
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(export_data, f, indent=2)

print(f"✓ Exported {len(export_data['vectors'])} vectors to {output_file}")
print(f"  File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
```

**Step 1.2: Verify Export**

```bash
# Check export file
ls -lh chromadb_export.json

# Validate JSON structure
python -c "import json; data = json.load(open('chromadb_export.json')); print(f'Vectors: {len(data[\"vectors\"])}')"
```

---

### Phase 2: Create Pinecone Index

**Step 2.1: Configure Pinecone**

```yaml
# config/pinecone_config.yaml
pinecone:
  api_key: "${PINECONE_API_KEY}"
  environment: "us-east-1"

index:
  name: "thermodynamics-v14"
  dimension: 384
  metric: "cosine"
  serverless:
    cloud: "aws"
    region: "us-east-1"

namespace:
  strategy: "document"
  default: "chapter_4"

batch_processing:
  batch_size: 100
  max_retries: 3
```

**Step 2.2: Create Index**

```python
#!/usr/bin/env python3
"""Create Pinecone index for migration."""

import os
import yaml
from pathlib import Path
from pinecone import Pinecone, ServerlessSpec

# Load config
with open('config/pinecone_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize Pinecone
api_key = os.getenv('PINECONE_API_KEY')
pc = Pinecone(api_key=api_key)

# Create serverless index
index_name = config['index']['name']
dimension = config['index']['dimension']
metric = config['index']['metric']

if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=dimension,
        metric=metric,
        spec=ServerlessSpec(
            cloud=config['index']['serverless']['cloud'],
            region=config['index']['serverless']['region']
        )
    )
    print(f"✓ Created index: {index_name}")
else:
    print(f"Index {index_name} already exists")

# Wait for index to be ready
import time
print("Waiting for index to be ready...")
time.sleep(10)

# Verify index
index = pc.Index(index_name)
stats = index.describe_index_stats()
print(f"✓ Index ready: {stats}")
```

---

### Phase 3: Migrate Data

**Step 3.1: Batch Upsert to Pinecone**

```python
#!/usr/bin/env python3
"""Migrate ChromaDB data to Pinecone."""

import json
import time
import os
import yaml
from pathlib import Path
from pinecone import Pinecone

# Load export data
print("Loading ChromaDB export...")
with open('chromadb_export.json', 'r') as f:
    export_data = json.load(f)

vectors = export_data['vectors']
print(f"✓ Loaded {len(vectors)} vectors")

# Load config
with open('config/pinecone_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize Pinecone
api_key = os.getenv('PINECONE_API_KEY')
pc = Pinecone(api_key=api_key)
index = pc.Index(config['index']['name'])

# Batch upsert
batch_size = config['batch_processing']['batch_size']
namespace = config['namespace']['default']
successful = 0
failed = 0

print(f"\nMigrating to Pinecone...")
print(f"  Index: {config['index']['name']}")
print(f"  Namespace: {namespace}")
print(f"  Batch size: {batch_size}")

for i in range(0, len(vectors), batch_size):
    batch = vectors[i:i + batch_size]
    batch_num = (i // batch_size) + 1
    total_batches = (len(vectors) + batch_size - 1) // batch_size

    # Format for Pinecone
    pinecone_vectors = []
    for vector in batch:
        pinecone_vectors.append({
            'id': vector['id'],
            'values': vector['embedding'],
            'metadata': {
                **vector['metadata'],
                'text': vector['document'][:40000]  # Pinecone limit
            }
        })

    # Upsert with retry
    retry_count = 0
    max_retries = config['batch_processing']['max_retries']

    while retry_count < max_retries:
        try:
            index.upsert(vectors=pinecone_vectors, namespace=namespace)
            successful += len(batch)
            print(f"✓ Batch {batch_num}/{total_batches} migrated ({len(batch)} vectors)")
            break
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                print(f"⚠ Batch {batch_num} failed (attempt {retry_count}), retrying...")
                time.sleep(2 ** retry_count)
            else:
                print(f"✗ Batch {batch_num} failed after {max_retries} attempts: {e}")
                failed += len(batch)

print(f"\n{'='*80}")
print(f"MIGRATION SUMMARY")
print(f"{'='*80}")
print(f"✓ Successful: {successful}")
if failed > 0:
    print(f"✗ Failed: {failed}")
print(f"Total: {len(vectors)}")
```

---

### Phase 4: Validation

**Step 4.1: Compare Counts**

```python
#!/usr/bin/env python3
"""Validate migration by comparing counts."""

import chromadb
from pinecone import Pinecone
import os
import yaml

# ChromaDB count
chroma_client = chromadb.PersistentClient(path="test_output_database/chromadb")
chroma_collection = chroma_client.get_collection("chapter_4_heat_transfer")
chroma_count = chroma_collection.count()

# Pinecone count
with open('config/pinecone_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
index = pc.Index(config['index']['name'])
pinecone_stats = index.describe_index_stats()
pinecone_count = pinecone_stats['total_vector_count']

# Compare
print(f"ChromaDB count: {chroma_count}")
print(f"Pinecone count: {pinecone_count}")

if chroma_count == pinecone_count:
    print("✓ Counts match - migration successful")
else:
    print(f"✗ Count mismatch - {abs(chroma_count - pinecone_count)} vectors missing")
```

**Step 4.2: Sample Query Comparison**

```python
#!/usr/bin/env python3
"""Compare query results between ChromaDB and Pinecone."""

import chromadb
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import os
import yaml

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Test query
query_text = "heat transfer convection"
query_embedding = model.encode(query_text).tolist()

# ChromaDB query
chroma_client = chromadb.PersistentClient(path="test_output_database/chromadb")
chroma_collection = chroma_client.get_collection("chapter_4_heat_transfer")
chroma_results = chroma_collection.query(
    query_embeddings=[query_embedding],
    n_results=5
)

# Pinecone query
with open('config/pinecone_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
index = pc.Index(config['index']['name'])
pinecone_results = index.query(
    vector=query_embedding,
    top_k=5,
    namespace=config['namespace']['default'],
    include_metadata=True
)

# Compare top results
print(f"Query: '{query_text}'")
print(f"\nChromaDB top result: {chroma_results['ids'][0][0]}")
print(f"Pinecone top result: {pinecone_results['matches'][0]['id']}")

# Check if top 5 overlap
chroma_ids = set(chroma_results['ids'][0])
pinecone_ids = set(m['id'] for m in pinecone_results['matches'])
overlap = len(chroma_ids & pinecone_ids)

print(f"\nTop-5 overlap: {overlap}/5 ({overlap/5*100:.0f}%)")

if overlap >= 4:
    print("✓ Query results are consistent")
else:
    print("⚠ Query results differ - may need investigation")
```

---

### Phase 5: Switch Application

**Step 5.1: Update Configuration**

```python
# config/vector_db_config.yaml

# OLD (ChromaDB)
# vector_db:
#   backend: "chromadb"
#   chromadb:
#     persist_directory: "test_output_database/chromadb"

# NEW (Pinecone)
vector_db:
  backend: "pinecone"
  pinecone:
    api_key: "${PINECONE_API_KEY}"
    index_name: "thermodynamics-v14"
    namespace: "chapter_4"
```

**Step 5.2: Update Application Code**

```python
# OLD CODE (ChromaDB-specific)
# import chromadb
# client = chromadb.PersistentClient(path="test_output_database/chromadb")
# collection = client.get_collection("chapter_4_heat_transfer")

# NEW CODE (Unified interface)
from database_v14_P6.src.vector_db import ChromaDBAdapter, PineconeAdapter
import yaml

# Load config
with open('config/vector_db_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Choose backend dynamically
if config['vector_db']['backend'] == 'chromadb':
    db = ChromaDBAdapter(config['vector_db']['chromadb'])
elif config['vector_db']['backend'] == 'pinecone':
    db = PineconeAdapter(config['vector_db']['pinecone'])

# Use unified interface
db.connect()
collection = db.get_collection('thermodynamics-v14')

# All query operations remain the same
results = db.query(collection, query_embedding, top_k=5)
```

---

## Cost Estimation

### Pinecone Pricing Calculator

**Current Pricing (as of 2025-11-20)**:
- Storage: $0.002 per GB-hour
- Read units: $0.25 per million reads
- Write units: $2.00 per million writes

### Example: 10,000 Chunks (384-dimensional)

**Storage Cost**:
```
Data size = 10,000 vectors × 384 dimensions × 4 bytes/float
          = 15.36 MB
          = 0.015 GB

Monthly storage = 0.015 GB × 720 hours × $0.002/GB-hour
                = $21.60/month
```

**Read Cost** (10,000 queries/day):
```
Monthly reads = 10,000 queries/day × 30 days
              = 300,000 queries
              = 0.3 million read units

Monthly read cost = 0.3M × $0.25/M
                  = $0.075/month
```

**Write Cost** (1,000 upserts/day):
```
Monthly writes = 1,000 upserts/day × 30 days
               = 30,000 writes
               = 0.03 million write units

Monthly write cost = 0.03M × $2.00/M
                   = $0.06/month
```

**Total Monthly Cost**:
```
Storage: $21.60
Reads:   $0.08
Writes:  $0.06
────────────────
Total:   $21.74/month
```

### Cost Optimization Tips

1. **Use namespaces** to logically separate data (no cost increase)
2. **Batch writes** to reduce write unit consumption
3. **Cache frequent queries** to reduce read units
4. **Archive old indexes** when not actively used
5. **Use serverless** (auto-scales, pay only for usage)

---

## Validation and Testing

### Validation Checklist

- [ ] **Vector counts match** (ChromaDB count = Pinecone count)
- [ ] **Sample queries match** (top-5 overlap ≥80%)
- [ ] **Metadata preserved** (all fields present)
- [ ] **Query latency acceptable** (<200ms p95)
- [ ] **Cost within budget** (<$50/month)
- [ ] **Error rate low** (<1% query failures)
- [ ] **Backup created** (ChromaDB data backed up)

### Testing Procedure

1. **Run full test suite**:
   ```bash
   python test_database_pipeline_pinecone.py
   ```

2. **Run validation queries**:
   ```bash
   python -c "
   from pinecone import Pinecone
   import os
   pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
   index = pc.Index('thermodynamics-v14')
   print(index.describe_index_stats())
   "
   ```

3. **Monitor for 24 hours**:
   - Query latency (should be <200ms p95)
   - Error rate (should be <1%)
   - Cost (monitor usage in Pinecone console)

---

## Rollback Plan

### When to Rollback

- Query latency >500ms consistently
- Error rate >5%
- Cost exceeds budget by 2x
- Data integrity issues detected

### Rollback Procedure

1. **Stop writes to Pinecone**:
   ```python
   # Revert config
   # vector_db:
   #   backend: "chromadb"
   ```

2. **Verify ChromaDB data intact**:
   ```bash
   python query_chromadb.py --stats
   ```

3. **Switch application back to ChromaDB**:
   ```bash
   # Restart application with ChromaDB config
   systemctl restart document-translator
   ```

4. **Delete Pinecone index** (optional, to stop costs):
   ```python
   from pinecone import Pinecone
   import os
   pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
   pc.delete_index('thermodynamics-v14')
   ```

---

## Post-Migration Optimization

### 1. Enable Hybrid Search

```python
# Add sparse vectors for keyword search
from pinecone_text.sparse import BM25Encoder

# Fit BM25 on corpus
bm25 = BM25Encoder.default()
corpus = [chunk['text'] for chunk in chunks]
bm25.fit(corpus)

# Generate sparse embeddings
sparse_embeddings = bm25.encode_documents(corpus)

# Upsert with both dense and sparse
for i, chunk in enumerate(chunks):
    index.upsert(vectors=[{
        'id': chunk['id'],
        'values': dense_embeddings[i],
        'sparse_values': sparse_embeddings[i],
        'metadata': chunk['metadata']
    }])
```

### 2. Optimize Metadata Filtering

```python
# Use pre-filter for better performance
results = index.query(
    vector=query_embedding,
    top_k=10,
    filter={'page_number': {'$gte': 10}},  # Pre-filter
    namespace='chapter_4'
)
```

### 3. Set Up Monitoring

```python
# Monitor query performance
import time

def monitored_query(query_embedding, top_k=10):
    start = time.time()
    results = index.query(vector=query_embedding, top_k=top_k)
    latency = time.time() - start

    # Log metrics
    print(f"Query latency: {latency*1000:.1f}ms")

    if latency > 0.2:
        print("⚠ High latency detected")

    return results
```

---

## Troubleshooting

### Issue 1: Vector Count Mismatch

**Symptoms**: Pinecone has fewer vectors than ChromaDB

**Solution**:
```bash
# Re-run migration for missing batches
python migrate_chromadb_to_pinecone.py --resume
```

### Issue 2: High Query Latency

**Symptoms**: Queries taking >500ms

**Solution**:
- Check network connectivity
- Use pre-filtering instead of post-filtering
- Reduce top_k value
- Enable query caching

### Issue 3: Unexpected Costs

**Symptoms**: Monthly costs exceed estimate

**Solution**:
```bash
# Check usage in Pinecone console
# Identify high-cost operations
# Optimize write batching
# Enable query caching
```

### Issue 4: API Rate Limiting

**Symptoms**: 429 errors from Pinecone

**Solution**:
- Implement exponential backoff
- Reduce batch size
- Add delays between batches

---

## Summary Checklist

- [ ] Backup ChromaDB data
- [ ] Get Pinecone API key
- [ ] Install Pinecone client
- [ ] Test connection with mock mode
- [ ] Export ChromaDB vectors
- [ ] Create Pinecone index
- [ ] Migrate data in batches
- [ ] Validate vector counts
- [ ] Compare sample queries
- [ ] Update application config
- [ ] Monitor for 24 hours
- [ ] Document costs
- [ ] Update team documentation

---

**Migration Complete!** Your vector database is now running on Pinecone with production-grade scalability and availability.

For questions or issues, refer to:
- Pinecone documentation: https://docs.pinecone.io
- Project CLAUDE_DATABASE.md: `pipelines/data_management/CLAUDE_DATABASE.md`
- Support: Create issue in project repository
