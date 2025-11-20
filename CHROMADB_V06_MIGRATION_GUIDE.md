# ChromaDB v0.6.0 Migration Guide

Quick reference for updating code from ChromaDB v0.5.x to v0.6.0+

---

## Breaking Changes

### 1. list_collections() Returns Collection Names (Not Objects)

#### v0.5.x (OLD)
```python
client = chromadb.PersistentClient(path="./chromadb")
collections = client.list_collections()

# collections[0] is a Collection object
collection = collections[0]
print(collection.name)  # Access .name attribute
print(collection.count())  # Use directly
```

#### v0.6.0+ (NEW)
```python
client = chromadb.PersistentClient(path="./chromadb")
collection_names = client.list_collections()

# collection_names[0] is a string
collection_name = collection_names[0]
collection = client.get_collection(collection_name)  # Must get collection first
print(collection.name)  # Now you can access .name
print(collection.count())  # Use count()
```

---

## Migration Patterns

### Pattern 1: List and Iterate Collections

#### Before (v0.5.x)
```python
collections = client.list_collections()
for collection in collections:
    print(f"Collection: {collection.name}")
    print(f"Count: {collection.count()}")
```

#### After (v0.6.0+)
```python
collection_names = client.list_collections()
for name in collection_names:
    collection = client.get_collection(name)
    print(f"Collection: {name}")
    print(f"Count: {collection.count()}")
```

---

### Pattern 2: Get First Collection

#### Before (v0.5.x)
```python
collections = client.list_collections()
if collections:
    collection = collections[0]
    # Use collection...
```

#### After (v0.6.0+)
```python
collection_names = client.list_collections()
if collection_names:
    collection = client.get_collection(collection_names[0])
    # Use collection...
```

---

### Pattern 3: Backward Compatible Code

If you need to support both versions:

```python
collection_names = client.list_collections()
if collection_names:
    # Handle both strings (v0.6.0+) and objects (v0.5.x)
    if isinstance(collection_names[0], str):
        # v0.6.0+ - collection_names are strings
        collection_name = collection_names[0]
        collection = client.get_collection(collection_name)
    else:
        # v0.5.x - collections are objects
        collection = collection_names[0]
```

---

## Common Errors and Fixes

### Error 1: AttributeError: 'str' object has no attribute 'name'

**Error Message:**
```
AttributeError: 'str' object has no attribute 'name'
```

**Cause:**
```python
collections = client.list_collections()
collection = collections[0]
print(collection.name)  # ❌ collections[0] is now a string
```

**Fix:**
```python
collection_names = client.list_collections()
collection_name = collection_names[0]
collection = client.get_collection(collection_name)
print(collection.name)  # ✓ Now collection is an object
```

---

### Error 2: 'str' object has no attribute 'count'

**Error Message:**
```
AttributeError: 'str' object has no attribute 'count'
```

**Cause:**
```python
collections = client.list_collections()
count = collections[0].count()  # ❌ collections[0] is a string
```

**Fix:**
```python
collection_names = client.list_collections()
collection = client.get_collection(collection_names[0])
count = collection.count()  # ✓ Use collection object
```

---

### Error 3: list_collections only returns collection names

**Error Message:**
```
ValueError: list_collections only returns collection names
```

**Cause:**
Trying to access collection properties directly from list_collections() result

**Fix:**
Always use `get_collection()` after `list_collections()`

---

## API Reference

### ChromaDB Client Methods

| Method | v0.5.x Return Type | v0.6.0+ Return Type | Notes |
|--------|-------------------|---------------------|-------|
| `list_collections()` | `List[Collection]` | `List[str]` | Breaking change |
| `get_collection(name)` | `Collection` | `Collection` | No change |
| `create_collection(name)` | `Collection` | `Collection` | No change |
| `delete_collection(name)` | `None` | `None` | No change |

### Collection Methods

| Method | v0.5.x | v0.6.0+ | Notes |
|--------|--------|---------|-------|
| `count()` | `count()` | `count()` | No change |
| `add()` | `add(...)` | `add(...)` | No change |
| `get()` | `get(...)` | `get(...)` | No change |
| `query()` | `query(...)` | `query(...)` | No change |
| `delete()` | `delete(...)` | `delete(...)` | No change |

---

## Migration Checklist

- [ ] Find all uses of `list_collections()` in codebase
- [ ] Replace direct collection access with `get_collection()`
- [ ] Update variable names (`collections` → `collection_names`)
- [ ] Test backward compatibility if supporting multiple versions
- [ ] Update error handling for new API patterns
- [ ] Update documentation and comments
- [ ] Run integration tests

### Search Commands

```bash
# Find all list_collections() usage
grep -rn "list_collections" --include="*.py" .

# Find potential direct collection access
grep -rn "collections\[" --include="*.py" .

# Find .count() calls (verify they're on collection objects)
grep -rn "\.count()" --include="*.py" .
```

---

## Testing Migration

### Test Script

```python
import chromadb

# Test v0.6.0 API
client = chromadb.PersistentClient(path="./test_chromadb")

# Create test collection
collection = client.create_collection("test_collection")
collection.add(
    ids=["1", "2", "3"],
    documents=["doc1", "doc2", "doc3"]
)

# Test list_collections returns strings
collection_names = client.list_collections()
assert isinstance(collection_names[0], str), "list_collections should return strings"

# Test get_collection works
retrieved_collection = client.get_collection(collection_names[0])
assert retrieved_collection.count() == 3, "Collection should have 3 documents"

# Cleanup
client.delete_collection("test_collection")

print("✓ All v0.6.0 API tests passed")
```

---

## References

- **ChromaDB Documentation:** https://docs.trychroma.com/
- **Breaking Changes:** Check CHANGELOG in ChromaDB repository
- **Migration Guide:** https://docs.trychroma.com/migration

---

## Project-Specific Fixes

**Files Updated in Document Translator v14:**
- `test_integration_e2e.py` - Lines 387-398, 549-567, 733-752

**Pattern Used:**
```python
collection_names = client.list_collections()
if collection_names:
    collection_name = collection_names[0] if isinstance(collection_names[0], str) else collection_names[0].name
    collection = client.get_collection(collection_name)
    # Use collection...
```

---

**Last Updated:** 2025-11-19
**ChromaDB Version:** v0.6.0+
