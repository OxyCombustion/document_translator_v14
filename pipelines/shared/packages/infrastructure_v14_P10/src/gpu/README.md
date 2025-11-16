# GPU Compatibility Monitor Agent

**Version:** 1.0.0
**Status:** Active
**Purpose:** Monitor and report AI framework compatibility with Intel Arc GPUs

## Quick Overview

This agent automates GPU compatibility research for AI frameworks and models. It generates targeted web search queries, manages a caching system, and produces comprehensive compatibility reports.

## What It Does

1. **Framework Compatibility Checks** - Verifies if AI frameworks (Docling, PyTorch, etc.) work with your GPU
2. **Model Discovery** - Finds multimodal AI models that fit your VRAM constraints
3. **Installation Guidance** - Provides exact installation commands and configuration options
4. **Performance Estimates** - Reports expected performance (tokens/sec, time/page, etc.)
5. **Caching System** - Stores results for 7 days to avoid redundant searches
6. **Report Generation** - Creates markdown or JSON compatibility reports

## Quick Start

```python
from gpu_compatibility_monitor import GPUCompatibilityMonitor, GPUProfile

# Initialize
monitor = GPUCompatibilityMonitor()

# Define GPU
gpu = GPUProfile(
    model="Intel Arc B580",
    vram_gb=12,
    architecture="Xe2 Battlemage"
)

# Check framework
check = monitor.check_framework_compatibility("Docling", gpu)
# Returns search queries to execute

# Find models
models = monitor.find_compatible_models("VLM", gpu, max_vram_gb=12)
# Returns search queries for compatible VLMs

# Generate report (after collecting data)
report = monitor.generate_compatibility_report(
    gpu_profile=gpu,
    frameworks_data=[...],
    models_data=[...]
)
```

## Files

- **`AGENT_SPECIFICATION.md`** - Complete technical specification
- **`USAGE_GUIDE.md`** - Detailed usage instructions and examples
- **`gpu_compatibility_monitor.py`** - Agent implementation
- **`README.md`** - This file

## Key Features

### Intelligent Search Query Generation
- Framework-specific queries with current year/month
- Model-type queries with VRAM constraints
- Accelerator-specific compatibility queries

### Caching System
- 7-day default cache duration (configurable)
- Cache validation and expiration
- Force refresh option
- Cache management utilities

### Flexible Reporting
- Markdown reports with formatting
- JSON export for programmatic use
- Grouped model listings by type
- Installation commands and configuration

### Data Structures

```python
GPUProfile(
    model: str,              # "Intel Arc B580"
    vram_gb: int,            # 12
    architecture: str,       # "Xe2 Battlemage"
    compute_units: int,      # Optional
    ai_tops: int,           # Optional
    driver_version: str      # Optional
)

FrameworkCompatibility(
    framework_name: str,
    version: str,
    gpu_support: str,        # "native" | "via_adapter" | "unsupported"
    accelerator: str,        # "OpenVINO" | "DirectML" | "oneAPI"
    installation_cmd: str,
    vram_requirements: dict,
    configuration_options: list,
    performance_notes: str,
    source_urls: list
)

ModelCompatibility(
    model_name: str,
    model_type: str,         # "VLM" | "LLM" | "Diffusion"
    parameters: str,         # "7B"
    vram_requirements: dict, # Per quantization
    quantization_options: list,
    framework_support: list,
    gpu_compatible: bool,
    performance_estimate: str
)
```

## Current Findings (2025-10-02)

Based on latest research for Intel Arc B580 (12GB VRAM):

### Docling Compatibility
- ✅ **Supported** via OpenVINO
- Install: `pip install "docling-ocr-onnxtr[openvino]"`
- VRAM: 4-8GB (configurable)
- Performance: 0.49 sec/page

### Multimodal Models (VLM)
- ✅ **Qwen 2.5 VL 7B** - 6GB (4-bit), 12GB (8-bit)
- ✅ **LLaMA 3.2 Vision 11B** - 8GB (4-bit)
- ✅ **Gemma 3 9B** - 6GB (4-bit), 12GB (8-bit)
- ✅ **DeepSeek-VL 7B** - 5GB (4-bit), 10GB (8-bit)
- ✅ **Phi-3-Vision 4B** - 3GB (4-bit), 6GB (8-bit)

### Performance
- **7B LLMs:** 15-20 tokens/sec (INT4 quantization)
- **Stable Diffusion:** 4-6 sec per 512×512 image
- **Document AI:** 0.49 sec/page with GPU acceleration

See `intel_arc_b580_compatibility_report_2025-10-02.md` for full report.

## Usage Examples

### Check Docling Compatibility
```python
monitor = GPUCompatibilityMonitor()
gpu = GPUProfile(model="Intel Arc B580", vram_gb=12, architecture="Xe2")

docling_check = monitor.check_framework_compatibility("Docling", gpu)
print(docling_check['queries'])
# Execute web searches with these queries
# Save results: monitor.save_compatibility_result(docling_check['cache_key'], data)
```

### Find VLMs for 12GB
```python
vlm_check = monitor.find_compatible_models("VLM", gpu, max_vram_gb=12)
print(vlm_check['search_instructions'])
# Execute searches, collect model data
```

### Generate Report
```python
report = monitor.generate_compatibility_report(
    gpu_profile=gpu,
    frameworks_data=frameworks,
    models_data=models,
    output_format="markdown"
)

with open("compatibility_report.md", "w") as f:
    f.write(report)
```

### Manage Cache
```python
# View cache
info = monitor.get_cache_info()
print(f"Cached items: {info['total_cached_items']}")

# Clear old cache
monitor.clear_cache(older_than_days=30)

# Force refresh
check = monitor.check_framework_compatibility("Docling", gpu, force_refresh=True)
```

## Integration with Document Translator

```python
# In session startup
from src.agents.gpu_compatibility_monitor.gpu_compatibility_monitor import (
    GPUCompatibilityMonitor, GPUProfile
)

# Initialize
gpu_monitor = GPUCompatibilityMonitor(
    cache_dir=Path("./cache/gpu_compatibility"),
    cache_days=7
)

# Check Docling
gpu_b580 = GPUProfile(model="Intel Arc B580", vram_gb=12, architecture="Xe2")
docling_status = gpu_monitor.check_framework_compatibility("Docling", gpu_b580)

# Use results to configure Docling with optimal settings
```

## Workflow

1. **Define GPU Profile** → Specify GPU model, VRAM, architecture
2. **Request Compatibility Check** → Get search queries for framework/models
3. **Execute Web Searches** → Use Claude's web search tools
4. **Parse Results** → Extract compatibility data from search results
5. **Save to Cache** → Store results for future use
6. **Generate Report** → Create formatted compatibility report

## Configuration

Default settings:
- Cache duration: 7 days
- Cache directory: `./cache/gpu_compatibility`
- Output formats: Markdown, JSON

Customize:
```python
monitor = GPUCompatibilityMonitor(
    cache_dir=Path("./custom_cache"),
    cache_days=3  # Shorter cache for rapidly changing data
)
```

## Best Practices

1. **Use descriptive GPU profiles** - Include all available specs
2. **Cache wisely** - 7 days for stable frameworks, shorter for evolving tools
3. **Force refresh before critical decisions** - Ensure latest data
4. **Verify sources** - Check `source_urls` in reports
5. **Update regularly** - Weekly checks for driver/framework updates

## Maintenance

- **Update Schedule:** Weekly compatibility checks recommended
- **Driver Updates:** Monitor Intel Graphics Driver releases monthly
- **Framework Tracking:** Watch for OpenVINO, IPEX-LLM, Docling updates
- **Cache Cleanup:** Clear cache older than 30 days periodically

## Documentation

- **Full Specification:** See `AGENT_SPECIFICATION.md`
- **Usage Guide:** See `USAGE_GUIDE.md`
- **Latest Report:** See `intel_arc_b580_compatibility_report_2025-10-02.md`

## Dependencies

- Python 3.13+
- Standard library only (json, pathlib, datetime, hashlib, dataclasses, typing)
- No external dependencies for core functionality
- Web search requires Claude's WebSearch/WebFetch tools

## Future Enhancements

- [ ] Automated driver version detection
- [ ] Performance benchmarking integration
- [ ] Multi-GPU comparison reports
- [ ] Framework version compatibility matrix
- [ ] Installation script generation
- [ ] Real-time compatibility monitoring

---

**Created:** 2025-10-02
**Last Updated:** 2025-10-02
**Agent Type:** Research & Monitoring
**Layer:** L3 (Specialized Agent)
