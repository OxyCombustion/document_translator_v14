# Hardware Configuration - NVIDIA DGX Spark

**CRITICAL**: This document defines the hardware environment for this project.
**DO NOT ASSUME DIFFERENT HARDWARE** - always read this file first.

## System Specifications

### Primary System: NVIDIA DGX Spark

| Component | Specification | Status |
|-----------|---------------|--------|
| **System Type** | NVIDIA DGX Spark | ✅ Enterprise AI Workstation |
| **GPU** | NVIDIA Blackwell Architecture | ✅ Latest Generation |
| **CUDA Support** | YES - Full NVIDIA CUDA Stack | ✅ Required for Docling |
| **Unified Memory** | 128GB | ✅ 2.7x over Docling requirements |
| **AI Performance** | 1 petaFLOP | ✅ Enterprise-grade |
| **CUDA Version** | 13.0 | ✅ Latest |
| **Driver Version** | 580.95.05 | ✅ Latest |

### NOT Intel Hardware

❌ **This is NOT an Intel B580 GPU system**
❌ **This is NOT Intel XPU**
❌ **Do NOT use Intel Extension for PyTorch**

## Software Implications

### ✅ Can Use (NVIDIA CUDA Required):
- Docling formula enrichment (GPU-accelerated)
- DocLayout-YOLO (GPU-accelerated)
- PyTorch with CUDA support
- NVIDIA-optimized libraries

### ❌ Cannot Use:
- Intel XPU extensions
- Intel-specific optimizations
- CPU-only approaches when GPU is available

## Memory Requirements vs Available

| Feature | Memory Required | Memory Available | Status |
|---------|----------------|------------------|---------|
| **Docling Formula Enrichment** | 18-20GB VRAM | 128GB unified | ✅ 6.4x margin |
| **DocLayout-YOLO** | 4-8GB VRAM | 128GB unified | ✅ 16x margin |
| **Combined Pipeline** | ~25GB VRAM | 128GB unified | ✅ 5x margin |

## Equation Extraction Strategy

### CRITICAL UPDATE (2025-11-16): Root Cause Found

**V13→V14 Regression Identified** 🚨
- **V13 Working Approach**: DocLayout-YOLO + pix2tex (108/108 equations, ~100s, 100% success)
- **V14 Broken Approach**: Docling 2.x formula enrichment (0/108 equations, 12+ hours, 0% success)
- **Root Cause**: DocLayout-YOLO detector NOT migrated from v13 to v14
- **Impact**: Complete equation extraction failure in v14

**Performance Comparison**:
| Method | Time | Success | Status |
|--------|------|---------|--------|
| **V13 DocLayout-YOLO** | ~100s | 108/108 (100%) | ✅ WORKING |
| **V14 Docling 2.x** | 12+ hours | 0/108 (0%) | ❌ BROKEN |

**Why Docling Failed on DGX Spark**:
1. Formula enrichment runs for 12+ hours on CPU (vs expected 2-4 min on GPU)
2. GPU acceleration NOT utilized despite DGX Spark capabilities
3. CPU mode impractical for production (terminated after 12.7 hours)
4. Different paradigm from v13's proven vision-based approach

**Solution**: Port v13 DocLayout-YOLO detector to v14
- **V13 Source**: `/home/thermodynamics/document_translator_v13/legacy/test_doclayout_yolo_equations.py`
- **V14 Target**: `detection_v14_P14/src/doclayout/doclayout_equation_detector.py`
- **doclayout-yolo**: Already installed in v14 venv (0.0.4)
- **Expected Result**: 108/108 equations in ~100 seconds

See: `V13_TO_V14_EQUATION_EXTRACTION_REGRESSION_ANALYSIS.md` for complete analysis

## Performance Expectations

### With DGX Spark GPU:
- Docling formula enrichment: **2-3 minutes** for 34-page document
- Table detection: **< 1 minute** for 34-page document
- Figure detection: **< 1 minute** for 34-page document
- Total pipeline: **< 5 minutes** for 34-page document

### With CPU (Fallback):
- Would be **10-20x slower**
- Not recommended when DGX Spark GPU is available

## Configuration Best Practices

1. **Always enable CUDA**: Check `torch.cuda.is_available()` returns True
2. **Use GPU for Docling**: Enable formula enrichment in pipeline options
3. **Monitor GPU memory**: Should see utilization in nvidia-smi
4. **Expect fast performance**: Enterprise hardware should deliver enterprise speed

## Historical Notes

### Information Loss Prevention

This file was created because:
- Hardware information was lost multiple times across sessions
- Incorrect assumptions about Intel vs NVIDIA hardware
- Wasted time implementing CPU-only solutions
- Missed opportunities to use enterprise GPU capabilities

**Solution**: This file is now the **single source of truth** for hardware configuration.

**When starting a new session**: READ THIS FILE FIRST before making hardware assumptions.

---

**Last Updated**: 2025-11-15
**System Owner**: thermodynamics
**Location**: /home/thermodynamics/document_translator_v14/
