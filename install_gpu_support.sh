#!/bin/bash
# -*- coding: utf-8 -*-
#
# GPU Support Installation Script
#
# This script installs CUDA-enabled PyTorch for GPU acceleration in the
# document extraction pipeline.
#
# Usage:
#   ./install_gpu_support.sh [--cuda-version VERSION]
#
# Options:
#   --cuda-version VERSION    Specify CUDA version (default: 130 for CUDA 13.0)
#                            Supported: 118 (11.8), 121 (12.1), 130 (13.0)
#   --cpu-only               Install CPU-only version of PyTorch
#   --backup                 Create backup of current environment
#   --no-verify              Skip verification after installation
#
# Author: Claude Code
# Date: 2025-11-20
# Version: 1.0.0

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
CUDA_VERSION="130"
CPU_ONLY=false
CREATE_BACKUP=false
SKIP_VERIFY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --cuda-version)
            CUDA_VERSION="$2"
            shift 2
            ;;
        --cpu-only)
            CPU_ONLY=true
            shift
            ;;
        --backup)
            CREATE_BACKUP=true
            shift
            ;;
        --no-verify)
            SKIP_VERIFY=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --cuda-version VERSION   CUDA version (118, 121, 130)"
            echo "  --cpu-only              Install CPU-only PyTorch"
            echo "  --backup                Backup current environment"
            echo "  --no-verify             Skip verification"
            echo "  -h, --help              Show this help"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Unknown option $1${NC}"
            exit 1
            ;;
    esac
done

echo "================================================================================"
echo "GPU SUPPORT INSTALLATION"
echo "================================================================================"
echo ""

# Check if we're in the correct directory
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: requirements.txt not found!${NC}"
    echo "Please run this script from the project root directory."
    exit 1
fi

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: No virtual environment detected!${NC}"
    echo "It's recommended to use a virtual environment."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Backup current environment if requested
if [ "$CREATE_BACKUP" = true ]; then
    echo -e "${BLUE}Creating backup of current environment...${NC}"
    BACKUP_DIR="venv_backup_$(date +%Y%m%d_%H%M%S)"

    if [ -n "$VIRTUAL_ENV" ]; then
        pip freeze > "${BACKUP_DIR}_requirements.txt"
        echo -e "${GREEN}✓ Backup created: ${BACKUP_DIR}_requirements.txt${NC}"
    else
        echo -e "${YELLOW}⚠ No virtual environment active, skipping backup${NC}"
    fi
    echo ""
fi

# Determine PyTorch version to install
if [ "$CPU_ONLY" = true ]; then
    echo -e "${BLUE}Installing CPU-only PyTorch...${NC}"
    TORCH_PACKAGE="torch>=2.0.0,<3.0.0"
    TORCHVISION_PACKAGE="torchvision>=0.15.0,<1.0.0"
    TORCHAUDIO_PACKAGE="torchaudio>=2.0.0,<3.0.0"
    EXTRA_INDEX=""
else
    echo -e "${BLUE}Installing CUDA-enabled PyTorch (CUDA ${CUDA_VERSION})...${NC}"

    case $CUDA_VERSION in
        118)
            TORCH_VERSION="2.5.1+cu118"
            TORCHVISION_VERSION="0.20.1+cu118"
            TORCHAUDIO_VERSION="2.5.1+cu118"
            echo "Target: CUDA 11.8"
            ;;
        121)
            TORCH_VERSION="2.5.1+cu121"
            TORCHVISION_VERSION="0.20.1+cu121"
            TORCHAUDIO_VERSION="2.5.1+cu121"
            echo "Target: CUDA 12.1"
            ;;
        130)
            TORCH_VERSION="2.5.1+cu130"
            TORCHVISION_VERSION="0.20.1+cu130"
            TORCHAUDIO_VERSION="2.5.1+cu130"
            echo "Target: CUDA 13.0"
            ;;
        *)
            echo -e "${RED}Error: Unsupported CUDA version: ${CUDA_VERSION}${NC}"
            echo "Supported versions: 118 (11.8), 121 (12.1), 130 (13.0)"
            exit 1
            ;;
    esac

    TORCH_PACKAGE="torch==${TORCH_VERSION}"
    TORCHVISION_PACKAGE="torchvision==${TORCHVISION_VERSION}"
    TORCHAUDIO_PACKAGE="torchaudio==${TORCHAUDIO_VERSION}"
    EXTRA_INDEX="--extra-index-url https://download.pytorch.org/whl/cu${CUDA_VERSION}"
fi

echo ""

# Check current PyTorch installation
echo -e "${BLUE}Checking current PyTorch installation...${NC}"
if python -c "import torch; print(f'Current: {torch.__version__}')" 2>/dev/null; then
    python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')" 2>/dev/null || true
else
    echo "PyTorch not currently installed"
fi
echo ""

# Uninstall existing PyTorch
echo -e "${BLUE}Removing existing PyTorch installation...${NC}"
pip uninstall -y torch torchvision torchaudio 2>/dev/null || true
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""

# Install new PyTorch
echo -e "${BLUE}Installing PyTorch packages...${NC}"
if [ "$CPU_ONLY" = true ]; then
    pip install "$TORCH_PACKAGE" "$TORCHVISION_PACKAGE" "$TORCHAUDIO_PACKAGE"
else
    pip install $EXTRA_INDEX "$TORCH_PACKAGE" "$TORCHVISION_PACKAGE" "$TORCHAUDIO_PACKAGE"
fi
echo -e "${GREEN}✓ PyTorch installation complete${NC}"
echo ""

# Verify installation
if [ "$SKIP_VERIFY" = false ]; then
    echo "================================================================================"
    echo "VERIFICATION"
    echo "================================================================================"
    echo ""

    echo -e "${BLUE}Running verification tests...${NC}"
    python - <<'VERIFICATION_SCRIPT'
import sys
import torch

print(f"PyTorch version: {torch.__version__}")
print(f"Python version: {sys.version.split()[0]}")
print(f"CUDA available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU device: {torch.cuda.get_device_name(0)}")
    print(f"GPU count: {torch.cuda.device_count()}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    print("\n✅ GPU acceleration is ENABLED and ready!")
else:
    if "cpu" in torch.__version__:
        print("\nℹ️  CPU-only build installed (as expected)")
    else:
        print("\n⚠️  CUDA-enabled build installed but GPU not detected")
        print("    Check NVIDIA drivers and CUDA installation")
        sys.exit(1)
VERIFICATION_SCRIPT

    VERIFY_RESULT=$?
    echo ""

    if [ $VERIFY_RESULT -eq 0 ]; then
        echo -e "${GREEN}✓ Verification passed${NC}"
    else
        echo -e "${RED}✗ Verification failed${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ Skipping verification${NC}"
fi

echo ""
echo "================================================================================"
echo "INSTALLATION COMPLETE"
echo "================================================================================"
echo ""

if [ "$CPU_ONLY" = false ]; then
    echo -e "${GREEN}GPU acceleration is now enabled!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run: python -m pipelines.shared.packages.common.src.gpu_utils"
    echo "     To verify GPU detection"
    echo ""
    echo "  2. Run: python benchmark_gpu.py"
    echo "     To benchmark CPU vs GPU performance"
    echo ""
    echo "  3. Run your extraction pipeline normally"
    echo "     GPU will be used automatically"
else
    echo -e "${GREEN}CPU-only PyTorch installed${NC}"
fi

echo ""
echo "Configuration:"
if [ "$CPU_ONLY" = true ]; then
    echo "  Mode: CPU-only"
else
    echo "  Mode: GPU-accelerated"
    echo "  CUDA: ${CUDA_VERSION}"
fi
echo ""

# Offer to run GPU test
if [ "$CPU_ONLY" = false ] && [ "$SKIP_VERIFY" = false ]; then
    echo "Would you like to run a quick GPU performance test? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Running GPU performance test..."
        python - <<'PERF_TEST'
import torch
import time

if torch.cuda.is_available():
    device = torch.device("cuda")
    print(f"Testing GPU: {torch.cuda.get_device_name(0)}")

    # Warmup
    x = torch.randn(1000, 1000).to(device)
    y = torch.matmul(x, x)

    # Test
    start = time.time()
    for _ in range(100):
        y = torch.matmul(x, x)
    torch.cuda.synchronize()
    duration = time.time() - start

    print(f"100 matrix multiplications: {duration:.3f}s")
    print(f"GPU is working correctly! ✓")
else:
    print("GPU not available for testing")
PERF_TEST
    fi
fi

echo ""
echo "Installation log complete."
