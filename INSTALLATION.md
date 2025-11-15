# Installation Guide: Document Translator V14

**Version**: 14.0.0
**Python Required**: 3.11+
**Last Updated**: 2025-11-15

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Prerequisites](#prerequisites)
3. [Installation Methods](#installation-methods)
4. [GPU Support](#gpu-support)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)
7. [Development Setup](#development-setup)

---

## Quick Start

### For End Users (Production)

```bash
# Clone repository
git clone <repository-url>
cd document_translator_v14

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python tools/test_v14_integration.py
```

### For Developers

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e .

# Set up pre-commit hooks
pre-commit install
```

---

## Prerequisites

### System Requirements

**Minimum**:
- CPU: 4 cores
- RAM: 8GB
- Storage: 10GB free space
- Python: 3.11+

**Recommended**:
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 50GB free space
- GPU: 8GB+ VRAM (optional, for acceleration)
- Python: 3.11 or 3.12

### Software Dependencies

**Required**:
- Python 3.11 or higher
- pip (latest version)
- git

**Optional**:
- CUDA Toolkit 11.8+ (for NVIDIA GPU)
- Intel oneAPI (for Intel GPU)
- ROCm 5.6+ (for AMD GPU)

---

## Installation Methods

### Method 1: Standard Installation (Recommended)

```bash
# 1. Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 2. Upgrade pip
pip install --upgrade pip setuptools wheel

# 3. Install production dependencies
pip install -r requirements.txt

# 4. Verify installation
python -c "import torch, numpy, pandas; print('✅ Installation successful')"
```

### Method 2: Development Installation

```bash
# 1. Create virtual environment
python3.11 -m venv venv-dev
source venv-dev/bin/activate

# 2. Install all development tools
pip install --upgrade pip
pip install -r requirements-dev.txt

# 3. Install pre-commit hooks
pre-commit install

# 4. Run tests to verify
pytest tests/ -v
```

### Method 3: Testing/CI Installation

```bash
# For CI/CD pipelines
pip install -r requirements-test.txt

# Run test suite
pytest --cov=. --cov-report=html
```

### Method 4: Conda Installation (Alternative)

```bash
# Create conda environment
conda create -n doc-translator python=3.11
conda activate doc-translator

# Install conda-available packages
conda install numpy pandas openpyxl networkx pyyaml

# Install remaining via pip
pip install -r requirements.txt
```

---

## GPU Support

### NVIDIA CUDA GPUs

```bash
# 1. Install CUDA Toolkit (if not already installed)
# Download from: https://developer.nvidia.com/cuda-downloads

# 2. Remove CPU-only PyTorch
pip uninstall torch torchvision torchaudio

# 3. Edit requirements-gpu.txt
# Uncomment CUDA 12.1 section (lines for cu121)

# 4. Install GPU version
pip install -r requirements-gpu.txt

# 5. Verify CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
```

**Expected Output**:
```
CUDA available: True
CUDA version: 12.1
```

### Intel GPUs (Arc, Iris Xe)

```bash
# 1. Install Intel oneAPI Base Toolkit
# Download from: https://www.intel.com/content/www/us/en/developer/tools/oneapi/base-toolkit.html

# 2. Install CPU PyTorch first
pip install torch>=2.0.0

# 3. Install Intel extension
pip install intel-extension-for-pytorch>=2.0.0

# 4. Verify Intel GPU
python -c "import intel_extension_for_pytorch as ipex; print(f'XPU available: {ipex.xpu.is_available()}')"
```

**Expected Output**:
```
XPU available: True
```

### AMD ROCm GPUs

```bash
# 1. Install ROCm (if not already installed)
# See: https://rocm.docs.amd.com/en/latest/deploy/linux/quick_start.html

# 2. Remove CPU PyTorch
pip uninstall torch torchvision torchaudio

# 3. Edit requirements-gpu.txt
# Uncomment ROCm section

# 4. Install ROCm version
pip install -r requirements-gpu.txt

# 5. Verify ROCm
python -c "import torch; print(f'ROCm available: {torch.cuda.is_available()}')"
```

---

## Verification

### Basic Verification

```bash
# Test Python version
python --version  # Should be 3.11 or higher

# Test imports
python -c "import torch, numpy, pandas, cv2, fitz; print('✅ All core libraries imported')"

# Test GPU (if installed)
python -c "import torch; print(f'GPU available: {torch.cuda.is_available()}')"
```

### Integration Tests

```bash
# Run full integration test suite
python tools/test_v14_integration.py

# Expected output:
# ✅ ALL TESTS PASSED - V14 integration validated successfully!
```

### Package Verification

```bash
# Verify all 21 packages are importable
python -c "
import common
import extraction_v14_P1
import rag_v14_P2
import curation_v14_P3
# ... etc
print('✅ All v14 packages importable')
"
```

---

## Troubleshooting

### Issue 1: ImportError: No module named 'fitz'

**Solution**:
```bash
pip install PyMuPDF>=1.23.0
```

### Issue 2: CUDA not available despite GPU installation

**Solutions**:
1. Check CUDA toolkit installation:
   ```bash
   nvidia-smi  # Should show CUDA version
   ```

2. Verify PyTorch CUDA version matches system CUDA:
   ```bash
   python -c "import torch; print(torch.version.cuda)"
   ```

3. Reinstall correct CUDA version of PyTorch

### Issue 3: Memory errors during installation

**Solutions**:
1. Install packages one at a time:
   ```bash
   pip install torch  # Large package, install first
   pip install transformers  # Install second
   pip install -r requirements.txt  # Rest
   ```

2. Use --no-cache-dir:
   ```bash
   pip install --no-cache-dir -r requirements.txt
   ```

### Issue 4: Package conflicts

**Solution**:
```bash
# Start fresh
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
```

### Issue 5: Integration tests fail

**Check**:
1. All dependencies installed:
   ```bash
   pip list | grep -E "(torch|numpy|pandas|PyMuPDF|docling)"
   ```

2. No import errors:
   ```bash
   python -c "from common.src.base.base_agent import BaseAgent"
   ```

3. Python path is set (if not using pip install -e .):
   ```bash
   export PYTHONPATH="${PYTHONPATH}:/path/to/document_translator_v14"
   ```

---

## Development Setup

### Full Development Environment

```bash
# 1. Clone and enter repository
git clone <repository-url>
cd document_translator_v14

# 2. Create development virtual environment
python3.11 -m venv venv-dev
source venv-dev/bin/activate

# 3. Install development dependencies
pip install --upgrade pip
pip install -r requirements-dev.txt

# 4. Install project in editable mode
pip install -e .

# 5. Set up pre-commit hooks
pre-commit install

# 6. Configure git hooks
git config core.hooksPath .githooks

# 7. Verify setup
pytest tests/ -v
black --check .
flake8 .
mypy .
```

### IDE Configuration

#### VS Code

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true
}
```

#### PyCharm

1. File → Settings → Project → Python Interpreter
2. Add interpreter → Existing environment → `venv/bin/python`
3. Tools → Python Integrated Tools → Default test runner → pytest

---

## Dependency Overview

### Production Dependencies (requirements.txt)

| Category | Packages | Purpose |
|----------|----------|---------|
| PDF Processing | PyMuPDF, docling, doclayout-yolo | Extract content from PDFs |
| Computer Vision | opencv-python, easyocr, Pillow | Image processing and OCR |
| Machine Learning | torch, transformers | ML models and inference |
| Data Processing | numpy, pandas, openpyxl, networkx | Data manipulation |
| Vector Database | chromadb | RAG and embeddings |
| Utilities | PyYAML, tqdm, psutil | Configuration and utilities |

### Development Dependencies (requirements-dev.txt)

| Category | Packages | Purpose |
|----------|----------|---------|
| Code Quality | black, flake8, isort, mypy, pylint | Linting and formatting |
| Testing | pytest, pytest-cov, pytest-xdist | Test framework |
| Documentation | sphinx, sphinx-rtd-theme | Doc generation |
| Development | ipython, jupyter, pre-commit | Dev tools |
| Profiling | memory-profiler, line-profiler, py-spy | Performance analysis |

### GPU Dependencies (requirements-gpu.txt)

| Hardware | Packages | Purpose |
|----------|----------|---------|
| NVIDIA CUDA | torch+cu121 | GPU acceleration |
| AMD ROCm | torch+rocm5.6 | AMD GPU support |
| Intel Arc/Xe | intel-extension-for-pytorch | Intel GPU support |

---

## Installation Checklist

### Before Installation
- [ ] Python 3.11+ installed
- [ ] pip updated to latest version
- [ ] Virtual environment created
- [ ] (Optional) GPU drivers installed

### During Installation
- [ ] requirements.txt installed successfully
- [ ] No error messages during installation
- [ ] All dependencies resolved

### After Installation
- [ ] Python version verified (3.11+)
- [ ] Core imports work (torch, numpy, pandas)
- [ ] Integration tests pass
- [ ] (Optional) GPU detected and working

---

## Support

### Getting Help

1. **Documentation**: Read all .md files in repository
2. **Integration Tests**: Run `python tools/test_v14_integration.py`
3. **Issue Tracker**: Check existing issues
4. **Community**: Search for similar problems

### Reporting Issues

When reporting installation issues, include:
1. Python version (`python --version`)
2. OS and version
3. Full error traceback
4. Output of `pip list`
5. GPU info (if using GPU)

---

## Next Steps

After successful installation:

1. **Run Tests**: `python tools/test_v14_integration.py`
2. **Read Documentation**: `V14_MIGRATION_PROJECT_COMPLETE.md`
3. **Explore Packages**: Review 21 v14 packages
4. **Try Extraction**: Run sample document extraction
5. **Configure**: Set up configuration files in `config/`

---

*Installation guide for Document Translator V14*
*Last updated: 2025-11-15*
*Version: 14.0.0*
