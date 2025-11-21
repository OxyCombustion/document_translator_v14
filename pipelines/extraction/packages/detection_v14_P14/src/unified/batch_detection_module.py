#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch GPU Detection Module - Optimized for Maximum GPU Utilization

This module implements batch processing to maximize GPU throughput:
- Persistent model loading (load once, reuse)
- Batch image preprocessing (render N pages at once)
- Batch GPU inference (process 8-16 pages simultaneously)
- Expected speedup: 5-10x over single-page processing

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

import fitz
from doclayout_yolo import YOLOv10
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Import from base module
from .unified_detection_module import Detection, Zone, UnifiedDetectionModule

# Import GPU utilities
try:
    from pipelines.shared.packages.common.src.gpu_utils import GPUManager
    GPU_UTILS_AVAILABLE = True
except ImportError:
    GPU_UTILS_AVAILABLE = False


class BatchDetectionModule(UnifiedDetectionModule):
    """
    Batch-optimized detection module for maximum GPU utilization.

    Key improvements over UnifiedDetectionModule:
    1. Persistent model loading (load once per process, not per page)
    2. Batch preprocessing (render multiple pages before GPU)
    3. Batch inference (process 8-16 pages simultaneously on GPU)

    Expected performance:
    - Single-page: ~5s for 5 pages (current)
    - Batch processing: ~0.5-1s for 5 pages (5-10x faster)
    """

    def __init__(self, model_path: str, confidence_threshold: float = 0.2,
                 use_gpu: bool = True, enable_mixed_precision: bool = True,
                 rendering_dpi: int = 300, batch_size: int = 8):
        """
        Initialize batch detector.

        Args:
            model_path: Path to DocLayout-YOLO model
            confidence_threshold: Minimum confidence (default: 0.2)
            use_gpu: Enable GPU acceleration (default: True)
            enable_mixed_precision: Enable FP16 (default: True)
            rendering_dpi: PDF rendering DPI (default: 300)
            batch_size: Pages to process per GPU batch (default: 8)
        """
        super().__init__(
            model_path=model_path,
            confidence_threshold=confidence_threshold,
            use_gpu=use_gpu,
            enable_mixed_precision=enable_mixed_precision,
            rendering_dpi=rendering_dpi
        )

        self.batch_size = batch_size
        self._model = None  # Persistent model instance

    def _load_model(self):
        """Load model once and keep in GPU memory."""
        if self._model is None:
            print(f"Loading model to {'GPU' if self.gpu_manager else 'CPU'}...")
            self._model = YOLOv10(self.model_path)

            # Move to GPU if available
            if self.gpu_manager and self.gpu_manager.is_available():
                device = self.gpu_manager.get_device()
                self._model.to(device)
                print(f"✅ Model loaded on {self.gpu_manager.get_info().device_name}")
            else:
                print("ℹ️  Model loaded on CPU")

        return self._model

    def detect_all_objects(self, pdf_path: Path, num_workers: int = 4,
                          start_page: int = 0, end_page: Optional[int] = None) -> List[Zone]:
        """
        Detect objects using batch processing for maximum GPU utilization.

        Strategy:
        1. Render PDF pages in parallel (CPU-bound, use ThreadPool)
        2. Batch GPU inference (process multiple pages at once)
        3. Combine results

        Args:
            pdf_path: Path to PDF
            num_workers: Rendering workers (default: 4, optimal for I/O)
            start_page: Starting page
            end_page: Ending page

        Returns:
            List of detected zones
        """
        print(f"\n{'='*80}")
        print(f"BATCH GPU DETECTION - OPTIMIZED")
        print(f"{'='*80}")
        print(f"PDF: {pdf_path}")
        print(f"Batch size: {self.batch_size}")
        print(f"Rendering workers: {num_workers}")
        print(f"Confidence: {self.confidence_threshold}")

        # Print GPU status
        if self.gpu_manager and self.gpu_manager.is_available():
            print(f"Device: {self.gpu_manager.get_info().device_name} (GPU)")
            if self.enable_mixed_precision:
                print(f"Precision: Mixed (FP16/FP32)")
        else:
            print(f"Device: CPU")
        print()

        # Get page range
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        if end_page is None:
            end_page = total_pages - 1
        doc.close()

        pages_to_process = list(range(start_page, end_page + 1))
        print(f"Processing {len(pages_to_process)} pages (pages {start_page+1} to {end_page+1})")
        print()

        # Load model once
        model = self._load_model()

        start_time = datetime.now()
        all_detections = []

        # Process in batches
        print("Starting batch processing...")
        for batch_start in range(0, len(pages_to_process), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(pages_to_process))
            batch_pages = pages_to_process[batch_start:batch_end]

            print(f"  Batch {batch_start//self.batch_size + 1}: Pages {batch_pages[0]+1}-{batch_pages[-1]+1} ({len(batch_pages)} pages)")

            # Step 1: Render pages in parallel (CPU-bound)
            render_start = time.time()
            page_images = self._render_pages_parallel(pdf_path, batch_pages, num_workers)
            render_time = time.time() - render_start
            print(f"    Rendering: {render_time:.2f}s")

            # Step 2: Batch GPU inference
            inference_start = time.time()
            batch_detections = self._batch_inference(model, page_images, batch_pages)
            inference_time = time.time() - inference_start
            print(f"    Inference: {inference_time:.2f}s ({len(batch_detections)} objects)")

            all_detections.extend(batch_detections)

            # Cleanup temp images
            for img_path, _ in page_images:
                if img_path.exists():
                    img_path.unlink()

        duration = (datetime.now() - start_time).total_seconds()

        print()
        print(f"Detection complete in {duration:.1f}s ({len(all_detections)} raw detections)")

        # Show GPU memory if available
        if self.gpu_manager and self.gpu_manager.is_available():
            mem = self.gpu_manager.get_memory_stats()
            print(f"GPU Memory: {mem.get('allocated_gb', 0):.2f}/{mem.get('total_gb', 0):.2f} GB "
                  f"({mem.get('utilization_percent', 0):.1f}% utilized)")

        # Convert to zones
        print()
        print("Converting detections to zones...")
        zones = self._convert_to_zones(all_detections)

        # Print summary
        print(f"{'='*80}")
        print(f"DETECTION SUMMARY")
        print(f"{'='*80}")
        print(f"Total zones: {len(zones)}")

        # Count by type
        zone_counts = {}
        for zone in zones:
            zone_counts[zone.type] = zone_counts.get(zone.type, 0) + 1

        for zone_type, count in sorted(zone_counts.items()):
            print(f"  {zone_type}: {count}")

        print()
        print(f"Processing time: {duration:.1f}s")
        print(f"Speed: {len(zones)/duration:.1f} zones/second")
        print()

        return zones

    def _render_pages_parallel(self, pdf_path: Path, page_nums: List[int],
                               num_workers: int) -> List[Tuple[Path, int]]:
        """
        Render multiple PDF pages in parallel.

        Args:
            pdf_path: PDF path
            page_nums: Page numbers to render
            num_workers: Number of parallel workers

        Returns:
            List of (image_path, page_num) tuples
        """
        temp_dir = Path("temp_detection")
        temp_dir.mkdir(exist_ok=True)

        page_images = []

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_page = {
                executor.submit(
                    self._render_single_page,
                    pdf_path,
                    page_num,
                    temp_dir
                ): page_num
                for page_num in page_nums
            }

            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    img_path = future.result()
                    page_images.append((img_path, page_num))
                except Exception as e:
                    print(f"    ERROR rendering page {page_num+1}: {e}")

        # Sort by page number
        page_images.sort(key=lambda x: x[1])
        return page_images

    def _render_single_page(self, pdf_path: Path, page_num: int,
                           temp_dir: Path) -> Path:
        """Render a single PDF page to PNG."""
        doc = fitz.open(pdf_path)
        page = doc[page_num]

        # Render at configured DPI
        mat = fitz.Matrix(self.rendering_dpi/72, self.rendering_dpi/72)
        pix = page.get_pixmap(matrix=mat)

        # Save temp image
        img_path = temp_dir / f"page_{page_num:04d}.png"
        pix.save(str(img_path))

        doc.close()
        return img_path

    def _batch_inference(self, model, page_images: List[Tuple[Path, int]],
                        page_nums: List[int]) -> List[Detection]:
        """
        Run YOLO inference on batch of images.

        Args:
            model: Loaded YOLO model
            page_images: List of (image_path, page_num)
            page_nums: Page numbers for this batch

        Returns:
            List of detections
        """
        # Extract image paths
        image_paths = [str(img_path) for img_path, _ in page_images]

        # Get device
        device_str = self.gpu_manager.get_device_string() if self.gpu_manager else 'cpu'

        # Run batch prediction
        try:
            if self.gpu_manager and self.enable_mixed_precision:
                # Use mixed precision context
                with self.gpu_manager.autocast():
                    results = model.predict(
                        image_paths,
                        imgsz=1024,
                        conf=self.confidence_threshold,
                        device=device_str,
                        verbose=False,
                        batch=len(image_paths)  # Process all at once
                    )
            else:
                results = model.predict(
                    image_paths,
                    imgsz=1024,
                    conf=self.confidence_threshold,
                    device=device_str,
                    verbose=False,
                    batch=len(image_paths)
                )
        except Exception as e:
            print(f"    ERROR during inference: {e}")
            return []

        # Parse detections
        detections = []
        for result_idx, result in enumerate(results):
            page_num = page_images[result_idx][1]

            for box in result.boxes:
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].tolist()

                # Get class name
                class_names = ['title', 'text', 'abandon', 'figure', 'figure_caption',
                              'table', 'table_caption', 'header', 'footer', 'reference',
                              'equation', 'isolate_formula', 'formula_caption']
                class_name = class_names[cls_id] if cls_id < len(class_names) else f'class_{cls_id}'

                detections.append(Detection(
                    class_name=class_name,
                    confidence=conf,
                    page_num=page_num,
                    bbox=(xyxy[0], xyxy[1], xyxy[2], xyxy[3])
                ))

        return detections

    # Inherit _convert_to_zones from parent UnifiedDetectionModule
    # This handles all the complex pairing logic correctly


# Example usage
if __name__ == "__main__":
    detector = BatchDetectionModule(
        model_path="models/doclayout_yolo_docstructbench_imgsz1024.pt",
        batch_size=8
    )

    zones = detector.detect_all_objects(
        pdf_path=Path("test_data/Ch-04_Heat_Transfer.pdf"),
        num_workers=4,
        start_page=0,
        end_page=4
    )

    print(f"Detected {len(zones)} zones")
