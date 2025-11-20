# GPU Acceleration - Quick Start Guide

**Target**: 10x speedup (9.3 min → ~1 min for 34-page documents)

---

## Installation (5 minutes)

### Step 1: Install GPU Support

```bash
cd /home/thermodynamics/document_translator_v14
./install_gpu_support.sh --backup
```

Wait for installation to complete (~3-5 minutes).

### Step 2: Verify GPU Detection

```bash
python -m pipelines.shared.packages.common.src.gpu_utils
```

**Expected output**:
```
================================================================================
GPU STATUS
================================================================================
Status: ENABLED
Device: NVIDIA GB10
CUDA Version: 13.0
Total Memory: 32.00 GB
```

✅ If you see this, GPU acceleration is ready!

---

## Quick Test (2 minutes)

### Run Benchmark

```bash
python benchmark_gpu.py --pages 5
```

**Expected results**:
- CPU: ~40-50 seconds
- GPU: ~4-5 seconds
- Speedup: ~9-10x

---

## Use in Production

### Automatic (Recommended)

No code changes needed! Just run your normal pipeline:

```bash
python test_with_unified_orchestrator.py
```

GPU will be used automatically if available.

### Manual Control

```python
from pipelines.extraction.packages.detection_v14_P14.src.unified.unified_detection_module import UnifiedDetectionModule

# GPU enabled (default)
detector = UnifiedDetectionModule(
    model_path="path/to/model.pt",
    use_gpu=True,  # This is the default
    enable_mixed_precision=True  # This is the default
)

# Force CPU-only
detector = UnifiedDetectionModule(
    model_path="path/to/model.pt",
    use_gpu=False
)
```

---

## Troubleshooting

### GPU Not Detected

```bash
# Check NVIDIA drivers
nvidia-smi

# Reinstall GPU support
./install_gpu_support.sh
```

### Out of Memory

Edit `/pipelines/extraction/config/gpu_config.yaml`:

```yaml
batch_processing:
  page_batch_size: 2  # Reduce from 4
```

### Slow Performance

```python
# Check if GPU is actually being used
from pipelines.shared.packages.common.src.gpu_utils import GPUManager
gpu = GPUManager()
gpu.print_status()
```

---

## Performance Expectations

| Document Size | CPU Time | GPU Time | Speedup |
|--------------|----------|----------|---------|
| 5 pages      | ~45s     | ~5s      | ~9x     |
| 10 pages     | ~1.5min  | ~10s     | ~9x     |
| 34 pages     | ~9.3min  | ~1min    | ~9x     |

---

## Key Files

- **GPU Utils**: `/pipelines/shared/packages/common/src/gpu_utils.py`
- **Config**: `/pipelines/extraction/config/gpu_config.yaml`
- **Install Script**: `/install_gpu_support.sh`
- **Benchmark**: `/benchmark_gpu.py`
- **Full Docs**: `/GPU_ACCELERATION_IMPLEMENTATION_SUMMARY.md`

---

## One-Liner Commands

```bash
# Install GPU support
./install_gpu_support.sh --backup

# Check GPU status
python -m pipelines.shared.packages.common.src.gpu_utils

# Benchmark performance
python benchmark_gpu.py --pages 5

# Run extraction (GPU auto-enabled)
python test_with_unified_orchestrator.py
```

---

**Questions?** See full documentation: `GPU_ACCELERATION_IMPLEMENTATION_SUMMARY.md`
