#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPU Benchmark Script - Compare CPU vs GPU Performance

This script benchmarks the extraction pipeline on CPU vs GPU to measure
the performance improvement from GPU acceleration.

Features:
---------
- Tests small sample (configurable page count)
- Compares CPU vs GPU processing times
- Reports speedup factor
- Shows detailed timing breakdown
- GPU memory monitoring

Usage:
------
    # Quick test (5 pages)
    python benchmark_gpu.py

    # Custom page range
    python benchmark_gpu.py --pages 10

    # Specific PDF
    python benchmark_gpu.py --pdf path/to/document.pdf --pages 10

Author: Claude Code
Date: 2025-11-20
Version: 1.0.0
"""

import sys
import os

# MANDATORY UTF-8 SETUP
if sys.platform == 'win32':
    import io
    if not hasattr(sys.stdout, '_wrapped_utf8'):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stdout._wrapped_utf8 = True
        except (AttributeError, ValueError):
            os.system('chcp 65001')
    if not hasattr(sys.stderr, '_wrapped_utf8'):
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            sys.stderr._wrapped_utf8 = True
        except (AttributeError, ValueError):
            pass

import argparse
from pathlib import Path
from datetime import datetime
import time

# Import GPU utilities
try:
    from pipelines.shared.packages.common.src.gpu_utils import (
        GPUManager,
        print_gpu_summary,
        configure_multiprocessing_for_cuda
    )
    GPU_UTILS_AVAILABLE = True
except ImportError:
    print("❌ GPU utilities not available. Please ensure gpu_utils.py is installed.")
    sys.exit(1)

# CRITICAL: Configure multiprocessing for CUDA BEFORE any multiprocessing operations
configure_multiprocessing_for_cuda()

# Import detection module
try:
    from pipelines.extraction.packages.detection_v14_P14.src.unified.unified_detection_module import UnifiedDetectionModule
    DETECTION_AVAILABLE = True
except ImportError:
    print("❌ Unified detection module not available.")
    DETECTION_AVAILABLE = False


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)


def format_time(seconds: float) -> str:
    """Format time in seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.1f}s"


def benchmark_detection(pdf_path: Path, model_path: Path, num_pages: int,
                       use_gpu: bool, num_workers: int = 8):
    """
    Benchmark detection pipeline.

    Args:
        pdf_path: Path to PDF
        model_path: Path to YOLO model
        num_pages: Number of pages to process
        use_gpu: Enable GPU acceleration
        num_workers: Number of parallel workers

    Returns:
        tuple: (duration_seconds, num_detections, gpu_stats)
    """
    print(f"\n{'GPU' if use_gpu else 'CPU'} Benchmark:")
    print(f"  Pages: {num_pages}")
    print(f"  Workers: {num_workers}")

    # Initialize detector
    detector = UnifiedDetectionModule(
        model_path=str(model_path),
        confidence_threshold=0.2,
        use_gpu=use_gpu,
        enable_mixed_precision=True
    )

    # Get GPU stats before
    gpu_stats_before = None
    if use_gpu and detector.gpu_manager and detector.gpu_manager.is_available():
        gpu_stats_before = detector.gpu_manager.get_memory_stats()

    # Run detection
    start_time = time.time()
    zones = detector.detect_all_objects(
        pdf_path=pdf_path,
        num_workers=num_workers,
        start_page=0,
        end_page=num_pages - 1
    )
    duration = time.time() - start_time

    # Get GPU stats after
    gpu_stats_after = None
    if use_gpu and detector.gpu_manager and detector.gpu_manager.is_available():
        gpu_stats_after = detector.gpu_manager.get_memory_stats()

    num_detections = len(zones)

    return duration, num_detections, (gpu_stats_before, gpu_stats_after)


def main():
    """Main benchmark function."""
    parser = argparse.ArgumentParser(
        description="Benchmark CPU vs GPU performance for extraction pipeline"
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("test_data/Ch-04_Heat_Transfer.pdf"),
        help="Path to PDF file"
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("/home/thermodynamics/document_translator_v12/models/models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt"),
        help="Path to YOLO model"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Number of pages to process (default: 5)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=8,
        help="Number of parallel workers (default: 8)"
    )
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="Only run CPU benchmark (skip GPU)"
    )
    parser.add_argument(
        "--gpu-only",
        action="store_true",
        help="Only run GPU benchmark (skip CPU)"
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.pdf.exists():
        print(f"❌ PDF not found: {args.pdf}")
        sys.exit(1)

    if not args.model.exists():
        print(f"❌ Model not found: {args.model}")
        sys.exit(1)

    if not DETECTION_AVAILABLE:
        print("❌ Detection module not available. Cannot run benchmark.")
        sys.exit(1)

    # Print header
    print_header("GPU PERFORMANCE BENCHMARK")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nConfiguration:")
    print(f"  PDF: {args.pdf.name}")
    print(f"  Pages: {args.pages}")
    print(f"  Workers: {args.workers}")

    # Check GPU availability
    print("\n" + "-" * 80)
    print("GPU Detection:")
    print("-" * 80)
    gpu_manager = GPUManager()
    gpu_available = gpu_manager.is_available()

    if gpu_available:
        info = gpu_manager.get_info()
        print(f"✅ GPU Available: {info.device_name}")
        print(f"   CUDA Version: {info.cuda_version}")
        print(f"   GPU Memory: {info.total_memory_gb:.2f} GB")
    else:
        print("❌ GPU Not Available")
        if not args.cpu_only:
            print("\nOnly CPU benchmark will be run.")
            args.cpu_only = True

    # Results storage
    results = {}

    # CPU Benchmark
    if not args.gpu_only:
        print_header("CPU BENCHMARK")
        try:
            cpu_duration, cpu_detections, _ = benchmark_detection(
                pdf_path=args.pdf,
                model_path=args.model,
                num_pages=args.pages,
                use_gpu=False,
                num_workers=args.workers
            )
            results['cpu'] = {
                'duration': cpu_duration,
                'detections': cpu_detections
            }
            print(f"\n✅ CPU Benchmark Complete")
            print(f"   Duration: {format_time(cpu_duration)}")
            print(f"   Detections: {cpu_detections}")
            print(f"   Speed: {cpu_detections / cpu_duration:.2f} detections/second")
        except Exception as e:
            print(f"\n❌ CPU Benchmark Failed: {e}")
            import traceback
            traceback.print_exc()

    # GPU Benchmark
    if not args.cpu_only and gpu_available:
        print_header("GPU BENCHMARK")
        try:
            gpu_duration, gpu_detections, gpu_stats = benchmark_detection(
                pdf_path=args.pdf,
                model_path=args.model,
                num_pages=args.pages,
                use_gpu=True,
                num_workers=args.workers
            )
            results['gpu'] = {
                'duration': gpu_duration,
                'detections': gpu_detections,
                'stats': gpu_stats
            }
            print(f"\n✅ GPU Benchmark Complete")
            print(f"   Duration: {format_time(gpu_duration)}")
            print(f"   Detections: {gpu_detections}")
            print(f"   Speed: {gpu_detections / gpu_duration:.2f} detections/second")

            # GPU stats
            if gpu_stats[1]:
                stats = gpu_stats[1]
                print(f"\n   GPU Memory:")
                print(f"     Peak Usage: {stats['allocated_gb']:.2f} GB / {stats['total_gb']:.2f} GB")
                print(f"     Utilization: {stats['utilization_percent']:.1f}%")
        except Exception as e:
            print(f"\n❌ GPU Benchmark Failed: {e}")
            import traceback
            traceback.print_exc()

    # Comparison
    if 'cpu' in results and 'gpu' in results:
        print_header("PERFORMANCE COMPARISON")

        cpu_time = results['cpu']['duration']
        gpu_time = results['gpu']['duration']
        speedup = cpu_time / gpu_time

        print(f"\nCPU Time:    {format_time(cpu_time)}")
        print(f"GPU Time:    {format_time(gpu_time)}")
        print(f"\nSpeedup:     {speedup:.2f}x faster on GPU")
        print(f"Time Saved:  {format_time(cpu_time - gpu_time)}")

        # Extrapolate to full document
        if args.pages < 34:  # Full document is 34 pages
            full_doc_pages = 34
            cpu_full = (cpu_time / args.pages) * full_doc_pages
            gpu_full = (gpu_time / args.pages) * full_doc_pages

            print(f"\nExtrapolated to {full_doc_pages} pages:")
            print(f"  CPU Time:    {format_time(cpu_full)}")
            print(f"  GPU Time:    {format_time(gpu_full)}")
            print(f"  Time Saved:  {format_time(cpu_full - gpu_full)}")

        # Visual bar chart
        print(f"\nPerformance Visualization:")
        cpu_bar = "█" * int(cpu_time / gpu_time * 20)
        gpu_bar = "█" * 20
        print(f"  CPU: {cpu_bar} {format_time(cpu_time)}")
        print(f"  GPU: {gpu_bar} {format_time(gpu_time)}")

    # Summary
    print_header("SUMMARY")

    if 'cpu' in results and 'gpu' in results:
        print(f"\n🎉 GPU acceleration provides {speedup:.1f}x speedup!")
        print(f"\nRecommendation: Use GPU for production workloads")
    elif 'gpu' in results:
        print(f"\n✅ GPU benchmark completed successfully")
    elif 'cpu' in results:
        print(f"\n✅ CPU benchmark completed successfully")
        print(f"\n💡 Install GPU support for significant speedup:")
        print(f"   ./install_gpu_support.sh --cuda-version 130")
    else:
        print(f"\n❌ No benchmarks completed")

    print(f"\nBenchmark completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
