# GPU Compatibility Monitor - Usage Guide

## Overview

The GPU Compatibility Monitor Agent tracks AI framework and model compatibility with Intel Arc GPUs. It provides automated web searches, caching, and comprehensive reporting for GPU compatibility research.

## Quick Start

### Basic Framework Check

```python
from src.agents.gpu_compatibility_monitor.gpu_compatibility_monitor import (
    GPUCompatibilityMonitor,
    GPUProfile
)

# Initialize monitor
monitor = GPUCompatibilityMonitor()

# Define your GPU
gpu = GPUProfile(
    model="Intel Arc B580",
    vram_gb=12,
    architecture="Xe2 Battlemage",
    ai_tops=233
)

# Check framework compatibility
docling_check = monitor.check_framework_compatibility("Docling", gpu)

# This returns search queries you should execute
print(docling_check['queries'])
# Execute web searches, then save results:
# monitor.save_compatibility_result(docling_check['cache_key'], compatibility_data)
```

### Find Compatible Models

```python
# Find Vision-Language Models that fit 12GB VRAM
vlm_check = monitor.find_compatible_models("VLM", gpu, max_vram_gb=12)

print(vlm_check['queries'])
# Execute searches, collect model data, then save
```

### Generate Report

```python
# After collecting framework and model data
frameworks_data = [
    {
        'framework_name': 'Docling',
        'gpu_support': 'via_adapter',
        'accelerator': 'OpenVINO',
        'installation_cmd': 'pip install "docling-ocr-onnxtr[openvino]"',
        'vram_requirements': {'minimum': 4, 'recommended': 8},
        'configuration_options': [
            'Use OpenVINO accelerator for Intel GPU support',
            'Install OpenCL runtime packages',
            'Configure GPU device selection'
        ],
        'performance_notes': '0.49 sec/page with GPU acceleration',
        'source_urls': ['https://github.com/docling-project/docling']
    }
]

models_data = [
    {
        'model_name': 'Qwen 2.5 VL 7B',
        'model_type': 'VLM',
        'parameters': '7B',
        'vram_requirements': {'4-bit': 6, '8-bit': 12, 'FP16': 18},
        'quantization_options': ['4-bit', '8-bit', 'FP16'],
        'framework_support': ['PyTorch', 'ONNX', 'Transformers'],
        'gpu_compatible': True,
        'performance_estimate': '15-20 tokens/sec',
        'source_urls': ['https://huggingface.co/']
    }
]

# Generate markdown report
report = monitor.generate_compatibility_report(
    gpu_profile=gpu,
    frameworks_data=frameworks_data,
    models_data=models_data,
    output_format="markdown"
)

# Save report
with open("gpu_compatibility_report.md", "w", encoding="utf-8") as f:
    f.write(report)
```

## Workflow Integration

### Step 1: Define GPU Profile

```python
# Intel Arc B580
gpu_b580 = GPUProfile(
    model="Intel Arc B580",
    vram_gb=12,
    architecture="Xe2 Battlemage",
    compute_units=20,
    ai_tops=233,
    driver_version="31.0.101.5590"  # Optional
)
```

### Step 2: Request Compatibility Checks

```python
# Check multiple frameworks
frameworks = ["Docling", "PyTorch", "TensorFlow", "ONNX Runtime", "OpenVINO"]
framework_checks = []

for framework in frameworks:
    check = monitor.check_framework_compatibility(framework, gpu_b580)
    framework_checks.append(check)
```

### Step 3: Execute Web Searches

The agent provides search queries - you execute them using Claude's web search tools:

```python
# For each check, use the queries to search the web
for check in framework_checks:
    if check['status'] == 'search_required':
        print(f"\nSearching for: {check['framework']}")
        print(f"Instructions: {check['search_instructions']}")
        print(f"Queries: {check['queries']}")

        # Execute web searches with Claude's tools
        # Then parse results into compatibility data
```

### Step 4: Save Results to Cache

```python
# After collecting data from web searches
compatibility_data = {
    'framework_name': 'Docling',
    'version': '2.0.0',
    'gpu_support': 'via_adapter',
    'accelerator': 'OpenVINO',
    # ... more fields
}

monitor.save_compatibility_result(check['cache_key'], compatibility_data)
```

### Step 5: Generate Reports

```python
# Generate comprehensive report
report = monitor.generate_compatibility_report(
    gpu_profile=gpu_b580,
    frameworks_data=collected_frameworks,
    models_data=collected_models,
    output_format="markdown"
)
```

## Cache Management

### View Cache Status

```python
cache_info = monitor.get_cache_info()
print(f"Cached items: {cache_info['total_cached_items']}")
print(f"Cache duration: {cache_info['cache_duration_days']} days")

for item in cache_info['cached_items']:
    print(f"  {item['file']}: {'Valid' if item['valid'] else 'Expired'}")
```

### Clear Old Cache

```python
# Clear items older than 30 days
result = monitor.clear_cache(older_than_days=30)
print(f"Deleted: {result['deleted_count']}, Remaining: {result['remaining_count']}")

# Clear all cache
result = monitor.clear_cache()
```

### Force Refresh

```python
# Bypass cache and get fresh data
fresh_check = monitor.check_framework_compatibility(
    "Docling",
    gpu_b580,
    force_refresh=True
)
```

## Output Formats

### Markdown Report

Generated reports include:
- GPU specifications
- Framework compatibility status with installation commands
- Compatible models grouped by type
- VRAM requirements and performance estimates
- Configuration options
- Source URLs for verification

### JSON Export

```python
json_report = monitor.generate_compatibility_report(
    gpu_profile=gpu_b580,
    frameworks_data=frameworks_data,
    models_data=models_data,
    output_format="json"
)

# Parse as JSON
import json
data = json.loads(json_report)
```

## Search Query Strategy

The agent generates targeted queries for different purposes:

### Framework Queries
- `"{framework} Intel Arc B580 compatibility 2025"`
- `"{framework} OpenVINO DirectML oneAPI support 2025"`
- `"{framework} VRAM requirements configuration"`
- `"{framework} Intel GPU acceleration setup guide"`

### Model Queries
- `"vision language models 12GB VRAM Intel Arc 2025"`
- `"quantized VLM Intel Arc GPU 2025"`
- `"VLM 4-bit 8-bit quantization VRAM requirements"`

### Accelerator Queries
- `"Intel Arc B580 OpenVINO support 2025"`
- `"Intel GPU drivers AI framework October 2025"`
- `"oneAPI DirectML version compatibility"`

## Convenience Function

For quick checks without setting up the full workflow:

```python
from src.agents.gpu_compatibility_monitor.gpu_compatibility_monitor import quick_gpu_check

# Check specific framework
result = quick_gpu_check(
    gpu_model="Intel Arc B580",
    vram_gb=12,
    framework="Docling"
)

# Check model type
result = quick_gpu_check(
    gpu_model="Intel Arc B580",
    vram_gb=12,
    model_type="VLM"
)
```

## Example Use Cases

### Use Case 1: Evaluate New Framework

```python
# User wants to know if new framework works with their GPU
monitor = GPUCompatibilityMonitor()
gpu = GPUProfile(model="Intel Arc B580", vram_gb=12, architecture="Xe2")

check = monitor.check_framework_compatibility("NewFramework", gpu)
# Execute searches based on check['queries']
# Save results and generate report
```

### Use Case 2: Find Best Models for GPU

```python
# Find all VLMs that fit 12GB VRAM
vlm_check = monitor.find_compatible_models("VLM", gpu, max_vram_gb=12)

# Find LLMs with headroom (use only 10GB)
llm_check = monitor.find_compatible_models("LLM", gpu, max_vram_gb=10)
```

### Use Case 3: Regular Compatibility Updates

```python
# Weekly update check
monitor = GPUCompatibilityMonitor(cache_days=7)

# Force refresh to get latest data
frameworks = ["Docling", "PyTorch", "OpenVINO"]
for fw in frameworks:
    check = monitor.check_framework_compatibility(fw, gpu, force_refresh=True)
    # Execute searches and update cache
```

### Use Case 4: Multi-GPU Comparison

```python
# Compare compatibility across different GPUs
gpus = [
    GPUProfile(model="Intel Arc B580", vram_gb=12, architecture="Xe2"),
    GPUProfile(model="Intel Arc A770", vram_gb=16, architecture="Xe"),
]

for gpu in gpus:
    check = monitor.check_framework_compatibility("Docling", gpu)
    # Collect and compare results
```

## Configuration

### Custom Cache Settings

```python
# Shorter cache duration for rapidly changing data
monitor = GPUCompatibilityMonitor(
    cache_dir=Path("./custom_cache"),
    cache_days=3
)
```

### Custom GPU Profile

```python
# Define custom GPU with all details
gpu_custom = GPUProfile(
    model="Intel Arc A770",
    vram_gb=16,
    architecture="Xe-HPG Alchemist",
    compute_units=32,
    ai_tops=170,
    driver_version="31.0.101.5333"
)
```

## Best Practices

1. **Use Descriptive GPU Profiles**: Include all available GPU details for better search results

2. **Cache Wisely**: Use 7-day cache for stable frameworks, shorter for rapidly evolving tools

3. **Force Refresh for Critical Decisions**: Use `force_refresh=True` before important compatibility decisions

4. **Verify Sources**: Check the `source_urls` in reports to verify information

5. **Update Regularly**: Run weekly checks to catch driver updates and new compatibility improvements

6. **Group Searches**: Batch multiple framework checks together for efficiency

## Troubleshooting

### Issue: No cache results
- Check cache directory exists and is writable
- Verify cache files are valid JSON
- Use `force_refresh=True` to regenerate

### Issue: Outdated information
- Clear cache: `monitor.clear_cache()`
- Reduce cache duration: `GPUCompatibilityMonitor(cache_days=1)`
- Force refresh specific checks

### Issue: Missing framework data
- Verify framework name spelling
- Check that web searches return relevant results
- Update search queries if needed

## Integration with Session Workflow

For integration with the document translator project:

```python
# In session startup
from src.agents.gpu_compatibility_monitor.gpu_compatibility_monitor import (
    GPUCompatibilityMonitor, GPUProfile
)

# Initialize once per session
gpu_monitor = GPUCompatibilityMonitor(
    cache_dir=Path("./cache/gpu_compatibility"),
    cache_days=7
)

# Check Docling compatibility
gpu_b580 = GPUProfile(model="Intel Arc B580", vram_gb=12, architecture="Xe2")
docling_status = gpu_monitor.check_framework_compatibility("Docling", gpu_b580)

# Use results to configure Docling appropriately
```

---

*For questions or issues, refer to AGENT_SPECIFICATION.md*
