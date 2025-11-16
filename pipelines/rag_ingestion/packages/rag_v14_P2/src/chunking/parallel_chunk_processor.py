#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Parallel Chunk Processor for V9
Combines V8's proven intelligent chunking with multi-core parallel processing
to achieve sub-2-second processing times.

This maintains the V8 architecture that achieved 3.44s performance and adds
multi-core scaling to target 1-2s processing.
"""

import sys
import time
import multiprocessing
from multiprocessing import Process, Queue, cpu_count
from queue import Empty
import logging
from typing import Dict, Any, List, Optional, Iterator
from pathlib import Path

# Set UTF-8 encoding for Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from .streaming_processor import DocumentChunker
from .intelligent_chunker import LogicalChunker
from .document_types import DocumentChunk
from ..agents.base import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class ParallelChunkProcessor:
    """
    Multi-core processor for V8 intelligent chunks.
    
    Uses V8's proven intelligent chunking (3.44s baseline) with persistent
    workers to achieve 2-4x speedup through parallel chunk processing.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.chunker = DocumentChunker(config)
        
        # Worker configuration
        self.num_workers = self._determine_optimal_workers()
        self.worker_timeout = config.get("worker_timeout", 30.0)
        self.result_timeout = config.get("result_timeout", 60.0)
        
        logger.info(f"ParallelChunkProcessor initialized with {self.num_workers} workers")
    
    def _determine_optimal_workers(self) -> int:
        """Determine optimal number of workers based on available cores"""
        available_cores = cpu_count()
        
        # Use 50-75% of available cores, leaving headroom for system
        if available_cores >= 16:
            return min(12, available_cores - 4)  # 12 workers max for large systems
        elif available_cores >= 8:
            return min(6, available_cores - 2)   # 6 workers for medium systems  
        else:
            return max(2, available_cores - 1)   # At least 2 workers, leave 1 for system
    
    @staticmethod
    def _worker_process(worker_id: int, task_queue: Queue, result_queue: Queue,
                       agent_config: Dict[str, Any], agent_class_name: str):
        """
        Persistent worker process for processing chunks.
        Each worker loads its agent once and processes multiple chunks.
        """
        try:
            # Setup worker logging
            worker_logger = logging.getLogger(f"Worker-{worker_id}")
            worker_logger.info(f"Worker {worker_id} starting - loading agent")
            
            # Import and create agent (lightweight V8 agents, not Docling)
            if agent_class_name == "BasicTextExtractorAgent":
                from ..agents.text_extractor.basic_agent import BasicTextExtractorAgent
                agent = BasicTextExtractorAgent(agent_config)
            elif agent_class_name == "EnhancedTableAgent":
                from ..agents.table_extractor.enhanced_table_agent import EnhancedTableAgent
                agent = EnhancedTableAgent(agent_config)
            else:
                # Default to basic text extractor
                from ..agents.text_extractor.basic_agent import BasicTextExtractorAgent
                agent = BasicTextExtractorAgent(agent_config)
            
            worker_logger.info(f"Worker {worker_id} ready - agent loaded")
            
            # Process chunks from queue
            chunks_processed = 0
            while True:
                try:
                    # Get task with timeout
                    task = task_queue.get(timeout=1.0)
                    
                    if task == "SHUTDOWN":
                        worker_logger.info(f"Worker {worker_id} shutting down - processed {chunks_processed} chunks")
                        break
                    
                    chunk_index, chunk = task
                    worker_logger.debug(f"Worker {worker_id} processing chunk {chunk_index}")
                    
                    # Process chunk with the agent
                    start_time = time.time()
                    result = agent.process(chunk)
                    processing_time = time.time() - start_time
                    
                    # Send result back
                    result_queue.put(("SUCCESS", chunk_index, result, processing_time))
                    chunks_processed += 1
                    
                except Empty:
                    # Timeout on queue.get() - continue waiting
                    continue
                except Exception as e:
                    worker_logger.error(f"Worker {worker_id} error processing chunk: {e}")
                    result_queue.put(("ERROR", chunk_index, str(e), 0))
                    
        except Exception as e:
            # Worker initialization failed
            result_queue.put(("ERROR", f"Worker {worker_id} failed to initialize: {e}"))
    
    def process_document_parallel(self, document_path: str, agent_class_name: str = "BasicTextExtractorAgent") -> Dict[str, Any]:
        """
        Process document using V8 intelligent chunking + multi-core parallel processing.
        
        Args:
            document_path: Path to PDF document
            agent_class_name: Which agent to use for processing chunks
            
        Returns:
            Combined results from all chunks with performance metrics
        """
        try:
            logger.info(f"Starting parallel processing: {document_path}")
            logger.info(f"Using {self.num_workers} workers with {agent_class_name}")
            overall_start_time = time.time()
            
            # Phase 1: V8 Intelligent Chunking (proven fast approach)
            logger.info("Phase 1: V8 Intelligent Chunking")
            chunking_start = time.time()
            
            chunks = list(self.chunker.chunk_document(document_path))
            
            chunking_time = time.time() - chunking_start
            logger.info(f"Created {len(chunks)} intelligent chunks in {chunking_time:.2f}s")
            
            if not chunks:
                return {
                    "error": "No chunks created from document",
                    "chunks_processed": 0,
                    "processing_time": 0
                }
            
            # Phase 2: Multi-Core Parallel Processing
            logger.info("Phase 2: Multi-Core Parallel Processing")
            parallel_start = time.time()
            
            # Create communication queues
            task_queue = Queue()
            result_queue = Queue()
            
            # Agent configuration for workers
            agent_config = self.config.get("agent_config", {"model_version": "v9_optimized"})
            
            # Start persistent workers
            workers = []
            for worker_id in range(self.num_workers):
                worker = Process(
                    target=self._worker_process,
                    args=(worker_id, task_queue, result_queue, agent_config, agent_class_name)
                )
                worker.start()
                workers.append(worker)
            
            logger.info(f"Started {len(workers)} persistent workers")
            
            # Queue all chunks for processing
            for i, chunk in enumerate(chunks):
                task_queue.put((i, chunk))
            
            logger.info(f"Queued {len(chunks)} chunks for parallel processing")
            
            # Collect results
            all_results = {}
            results_collected = 0
            processing_errors = []
            total_chunk_time = 0
            
            while results_collected < len(chunks):
                try:
                    result = result_queue.get(timeout=self.result_timeout)
                    
                    if result[0] == "SUCCESS":
                        _, chunk_index, chunk_result, chunk_time = result
                        all_results[chunk_index] = chunk_result
                        total_chunk_time += chunk_time
                        results_collected += 1
                        
                        if results_collected % 10 == 0 or results_collected == len(chunks):
                            logger.info(f"Collected {results_collected}/{len(chunks)} results")
                    
                    elif result[0] == "ERROR":
                        if len(result) >= 3:
                            _, chunk_index, error_msg = result[:3]
                            processing_errors.append(f"Chunk {chunk_index}: {error_msg}")
                        else:
                            processing_errors.append(result[1])
                        results_collected += 1
                        
                except Empty:
                    logger.warning("Timeout waiting for results from workers")
                    break
            
            # Shutdown workers
            for _ in range(self.num_workers):
                task_queue.put("SHUTDOWN")
            
            # Wait for workers to finish
            for worker in workers:
                worker.join(timeout=5.0)
                if worker.is_alive():
                    logger.warning(f"Worker {worker.pid} still running, terminating")
                    worker.terminate()
            
            parallel_time = time.time() - parallel_start
            total_time = time.time() - overall_start_time
            
            # Combine results in order
            combined_results = []
            for i in range(len(chunks)):
                if i in all_results:
                    combined_results.append(all_results[i])
            
            # Performance analysis
            sequential_estimate = len(chunks) * (total_chunk_time / max(results_collected, 1))
            speedup = sequential_estimate / parallel_time if parallel_time > 0 else 1.0
            
            logger.info(f"Parallel processing completed in {total_time:.2f}s")
            logger.info(f"Chunking: {chunking_time:.2f}s, Parallel: {parallel_time:.2f}s")
            logger.info(f"Estimated speedup: {speedup:.1f}x over sequential")
            
            return {
                "results": combined_results,
                "chunks_processed": results_collected,
                "processing_time": total_time,
                "chunking_time": chunking_time,
                "parallel_time": parallel_time,
                "estimated_speedup": speedup,
                "processing_errors": processing_errors,
                "performance_metrics": {
                    "chunks_per_second": results_collected / total_time,
                    "average_chunk_time": total_chunk_time / max(results_collected, 1),
                    "workers_used": self.num_workers,
                    "system_cores": cpu_count()
                }
            }
            
        except Exception as e:
            logger.error(f"Parallel processing failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "chunks_processed": 0,
                "processing_time": time.time() - overall_start_time if 'overall_start_time' in locals() else 0
            }
    
    def process_with_table_extraction(self, document_path: str) -> Dict[str, Any]:
        """
        Process document with focus on table extraction using parallel processing.
        Uses V8's proven approach with multi-core scaling.
        """
        logger.info("Processing document with table extraction focus")
        
        # Use enhanced table agent for parallel processing
        result = self.process_document_parallel(document_path, "EnhancedTableAgent")
        
        if "error" in result:
            return result
        
        # Extract tables from results
        all_tables = []
        for chunk_result in result.get("results", []):
            if hasattr(chunk_result, 'data') and isinstance(chunk_result.data, dict):
                tables = chunk_result.data.get('tables', [])
                all_tables.extend(tables)
        
        result["tables_found"] = len(all_tables)
        result["tables"] = all_tables
        
        logger.info(f"Table extraction complete: {len(all_tables)} tables found")
        
        return result