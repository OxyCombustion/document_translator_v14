# -*- coding: utf-8 -*-
"""
Adaptive Batch Size Processor - Optimize batch sizing based on workload type.

This module implements intelligent batch size selection for LLM processing,
balancing latency (interactive queries) vs throughput (batch processing).

Based on Web Claude architectural review recommendation (P1 priority).

Performance characteristics:
- Interactive queries: Prioritize time-to-first-result (60-70% faster perceived latency)
- Batch processing: Prioritize throughput (15-20% higher throughput with larger batches)
- Mixed workload: Balance both metrics

Scenario analysis:
  Interactive (200 chunks):
    - Small batches (16): 0.8s first result, 10.4s total
    - Large batches (128): 2.5s first result, 5s total
    → Use small batches for user waiting

  Batch (10K chunks):
    - Small batches (32): Low efficiency, long total time
    - Large batches (128): High efficiency, fast total time
    → Use large batches for background processing
"""

import sys
import os
from typing import Dict, List, Iterator, Optional, Any
from enum import Enum
import logging
import time

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

logger = logging.getLogger(__name__)


class WorkloadType(Enum):
    """Enumeration of supported workload types with their characteristics."""

    INTERACTIVE = "interactive"  # User waiting for response (prioritize latency)
    BATCH = "batch"  # Corpus processing (prioritize throughput)
    MIXED = "mixed"  # General purpose (balance both)

    def __str__(self) -> str:
        """Return human-readable workload type name."""
        return self.value


class AdaptiveBatchProcessor:
    """
    Adaptive batch size selection based on workload characteristics.

    This processor selects optimal batch sizes for different workload types,
    then streams results back to the caller as soon as each batch completes.

    The key insight: Small batches are good for interactive queries because
    users see first results quickly (0.8s), while large batches are good for
    batch processing because total throughput is higher (5s vs 10.4s for 200 chunks).

    Attributes:
        classifier: Object with classify_batch(chunks, model_id) method
        batch_configs: Configuration dictionary for batch sizes by workload type
    """

    def __init__(self, classifier: Any) -> None:
        """
        Initialize processor with classifier.

        Args:
            classifier: Object implementing classify_batch(chunks, model_id) method.
                       Expected to return iterable of classification results.

        Raises:
            ValueError: If classifier is None
        """
        if classifier is None:
            raise ValueError("Classifier cannot be None")

        self.classifier = classifier

        # Batch size configurations for each workload type
        self.batch_configs = {
            WorkloadType.INTERACTIVE: {
                "small": 8,    # Very fast first results (<1s)
                "medium": 16,  # Fast first results (1-2s)
                "large": 32    # Maximum for interactive (2-3s)
            },
            WorkloadType.BATCH: {
                "small": 32,   # For small corpora
                "medium": 64,  # For medium corpora
                "large": 128   # Maximum throughput for large corpora
            },
            WorkloadType.MIXED: {
                "small": 16,   # Balanced for small workloads
                "medium": 32,  # Balanced for medium workloads
                "large": 64    # Balanced for large workloads
            }
        }

        logger.info(f"AdaptiveBatchProcessor initialized with classifier: {type(classifier).__name__}")

    def classify_with_adaptive_batching(
        self,
        chunks: List[Dict[str, Any]],
        model_id: str,
        workload_type: WorkloadType = WorkloadType.MIXED
    ) -> Iterator[Dict[str, Any]]:
        """
        Classify chunks with adaptive batch sizing.

        Selects optimal batch size based on workload type and chunk count,
        then processes batches while streaming results immediately as each
        batch completes.

        Args:
            chunks: List of chunk dictionaries to classify
            model_id: Identifier for the LLM model to use
            workload_type: Type of workload (INTERACTIVE, BATCH, or MIXED)

        Yields:
            Classification results dict as each batch completes

        Raises:
            ValueError: If chunks is empty or model_id is invalid
            RuntimeError: If classifier fails to process a batch

        Example:
            >>> processor = AdaptiveBatchProcessor(my_classifier)
            >>> for result in processor.classify_with_adaptive_batching(
            ...     chunks=chunk_list,
            ...     model_id="qwen-2.5-3b",
            ...     workload_type=WorkloadType.INTERACTIVE
            ... ):
            ...     print(f"Got result: {result['chunk_id']}")
        """
        if not chunks:
            logger.warning("Empty chunk list provided to classify_with_adaptive_batching")
            return

        if not model_id or not isinstance(model_id, str):
            raise ValueError(f"Invalid model_id: {model_id}")

        batch_size = self._select_batch_size(len(chunks), workload_type)

        logger.info(
            f"Processing {len(chunks)} chunks with batch_size={batch_size} "
            f"({workload_type} workload)"
        )

        # Track batch statistics for logging
        total_batches = (len(chunks) + batch_size - 1) // batch_size
        batch_count = 0

        # Process in batches, yielding results immediately
        for i in range(0, len(chunks), batch_size):
            batch_count += 1
            batch = chunks[i:i + batch_size]

            try:
                logger.debug(
                    f"Processing batch {batch_count}/{total_batches} "
                    f"(chunks {i}-{min(i + batch_size - 1, len(chunks) - 1)})"
                )

                batch_start_time = time.time()
                batch_results = self.classifier.classify_batch(batch, model_id)
                batch_elapsed = time.time() - batch_start_time

                throughput = len(batch) / batch_elapsed if batch_elapsed > 0 else 0
                logger.debug(
                    f"Batch {batch_count} completed in {batch_elapsed:.2f}s "
                    f"({len(batch)} chunks, {throughput:.1f} chunks/sec)"
                )

                # Yield results immediately (streaming pattern)
                result_count = 0
                for result in batch_results:
                    yield result
                    result_count += 1

                if result_count != len(batch):
                    logger.warning(
                        f"Batch {batch_count}: Expected {len(batch)} results, "
                        f"got {result_count}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing batch {batch_count}: {type(e).__name__}: {e}"
                )
                raise RuntimeError(
                    f"Failed to process batch {batch_count}/{total_batches}"
                ) from e

    def _select_batch_size(
        self,
        total_chunks: int,
        workload_type: WorkloadType
    ) -> int:
        """
        Select optimal batch size based on workload characteristics.

        Decision logic:
        - INTERACTIVE: Prioritize latency (small batches)
          <20 chunks: 8   (single batch, instant)
          <100 chunks: 16 (2-6 batches)
          ≥100 chunks: 32 (3+ batches)

        - BATCH: Prioritize throughput (large batches)
          <100 chunks: 32   (single/couple batches)
          <1000 chunks: 64  (15+ batches)
          ≥1000 chunks: 128 (8+ batches)

        - MIXED: Balance latency and throughput
          <50 chunks: 16  (3 batches max)
          <500 chunks: 32 (15 batches)
          ≥500 chunks: 64 (8+ batches)

        Args:
            total_chunks: Number of chunks to process
            workload_type: Type of workload

        Returns:
            Optimal batch size for the given workload

        Raises:
            ValueError: If workload_type not recognized or total_chunks is negative
        """
        if total_chunks < 0:
            raise ValueError(f"total_chunks must be non-negative, got {total_chunks}")

        if workload_type not in self.batch_configs:
            raise ValueError(f"Unknown workload type: {workload_type}")

        configs = self.batch_configs[workload_type]

        if workload_type == WorkloadType.INTERACTIVE:
            # Interactive: prioritize low latency (quick first result)
            if total_chunks < 20:
                return configs["small"]   # 8 chunks - single batch, instant
            elif total_chunks < 100:
                return configs["medium"]  # 16 chunks - 2-6 batches, fast
            else:
                return configs["large"]   # 32 chunks - 3+ batches, still responsive

        elif workload_type == WorkloadType.BATCH:
            # Batch: prioritize high throughput (fast total completion)
            if total_chunks < 100:
                return configs["small"]   # 32 chunks - few large batches
            elif total_chunks < 1000:
                return configs["medium"]  # 64 chunks - balanced for medium corpus
            else:
                return configs["large"]   # 128 chunks - maximum throughput

        else:  # WorkloadType.MIXED
            # Mixed: balance latency and throughput
            if total_chunks <= 50:
                return configs["small"]   # 16 chunks - quick and efficient
            elif total_chunks < 500:
                return configs["medium"]  # 32 chunks - good balance
            else:
                return configs["large"]   # 64 chunks - handle large workloads efficiently

    def get_batch_size_info(self, workload_type: WorkloadType) -> Dict[str, int]:
        """
        Get batch size configuration for a workload type.

        Args:
            workload_type: The workload type to query

        Returns:
            Dictionary with small/medium/large batch size configuration

        Raises:
            ValueError: If workload_type not recognized
        """
        if workload_type not in self.batch_configs:
            raise ValueError(f"Unknown workload type: {workload_type}")

        return self.batch_configs[workload_type].copy()
