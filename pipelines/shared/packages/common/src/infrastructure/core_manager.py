#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Centralized Core Manager for Document Translator V11

This module provides a singleton manager for CPU core allocation across all parallel
processing modules. It ensures that at least 8 cores (or 25% of total cores) are
reserved for the OS and other activities, preventing resource contention between
parallel modules.

Based on the proven CoreAssignmentManager from dual_scanning_agent_framework.py,
extended with singleton pattern and dynamic task allocation capabilities.

Key Features:
- Singleton pattern ensures single point of control
- Thread-safe allocation and release of cores
- Minimum 8 cores (or 25%) reserved for system
- Dynamic allocation based on task priorities
- Tracking of active allocations to prevent conflicts
"""

import threading
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from multiprocessing import cpu_count
import time

logger = logging.getLogger(__name__)


@dataclass
class CoreAllocation:
    """Represents a core allocation for a specific task"""
    task_id: str
    task_type: str  # 'table_extraction', 'equation_extraction', 'scanning', etc.
    allocated_cores: List[int]
    max_workers: int
    allocated_at: float
    priority: int = 5  # 1-10, higher = more priority


class CentralizedCoreManager:
    """
    Singleton manager for CPU core allocation across all parallel processing modules.

    Ensures coordinated resource usage and prevents over-allocation while maintaining
    system responsiveness by reserving adequate cores for OS operations.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        """Implement singleton pattern with thread safety"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the core manager (only runs once due to singleton)"""
        if self._initialized:
            return

        self.total_cores = cpu_count()
        self.allocations: Dict[str, CoreAllocation] = {}
        self.allocation_lock = threading.RLock()

        # Calculate system reservation (minimum 8 cores or 25% of total)
        self.system_reserved = max(8, self.total_cores // 4)
        self.available_for_allocation = self.total_cores - self.system_reserved

        # Track which cores are currently allocated
        self.allocated_cores: set = set()
        self.free_cores: List[int] = list(range(self.available_for_allocation))

        # Default task configurations (can be overridden)
        self.task_configs = {
            'table_extraction': {
                'max_workers': 8,
                'priority': 7,
                'core_percentage': 0.4  # 40% of available cores
            },
            'equation_extraction': {
                'max_workers': 8,
                'priority': 7,
                'core_percentage': 0.4  # 40% of available cores
            },
            'dual_scanning': {
                'max_workers': 12,
                'priority': 8,
                'core_percentage': 0.6  # 60% of available cores for complex scanning
            },
            'text_extraction': {
                'max_workers': 6,
                'priority': 5,
                'core_percentage': 0.3  # 30% of available cores
            },
            'default': {
                'max_workers': 4,
                'priority': 5,
                'core_percentage': 0.25  # 25% of available cores
            }
        }

        self._initialized = True

        logger.info(f"CentralizedCoreManager initialized:")
        logger.info(f"  Total cores: {self.total_cores}")
        logger.info(f"  System reserved: {self.system_reserved} cores")
        logger.info(f"  Available for allocation: {self.available_for_allocation} cores")

    def request_cores(self, task_id: str, task_type: str = 'default',
                      preferred_count: Optional[int] = None) -> Tuple[int, List[int]]:
        """
        Request core allocation for a specific task.

        Args:
            task_id: Unique identifier for the task
            task_type: Type of task (determines default allocation)
            preferred_count: Preferred number of cores (optional)

        Returns:
            Tuple of (num_workers, allocated_core_ids)
        """
        with self.allocation_lock:
            # Check if task already has allocation
            if task_id in self.allocations:
                existing = self.allocations[task_id]
                logger.debug(f"Task {task_id} already has {len(existing.allocated_cores)} cores")
                return existing.max_workers, existing.allocated_cores

            # Get task configuration
            config = self.task_configs.get(task_type, self.task_configs['default'])

            # Calculate how many cores to allocate
            if preferred_count is not None:
                requested_cores = preferred_count
            else:
                requested_cores = int(self.available_for_allocation * config['core_percentage'])

            # Ensure we don't exceed limits
            requested_cores = min(requested_cores, config['max_workers'])
            requested_cores = max(2, requested_cores)  # Minimum 2 cores for any task

            # Check how many cores are actually free
            currently_allocated = len(self.allocated_cores)
            cores_free = self.available_for_allocation - currently_allocated

            if cores_free <= 0:
                logger.warning(f"No cores available for task {task_id} ({task_type})")
                # Return minimum allocation
                return 1, []

            # Allocate what we can
            cores_to_allocate = min(requested_cores, cores_free)

            # Select specific core IDs
            allocated_core_ids = self.free_cores[:cores_to_allocate]
            self.free_cores = self.free_cores[cores_to_allocate:]
            self.allocated_cores.update(allocated_core_ids)

            # Create allocation record
            allocation = CoreAllocation(
                task_id=task_id,
                task_type=task_type,
                allocated_cores=allocated_core_ids,
                max_workers=cores_to_allocate,
                allocated_at=time.time(),
                priority=config['priority']
            )

            self.allocations[task_id] = allocation

            logger.info(f"Allocated {cores_to_allocate} cores to {task_id} ({task_type})")
            logger.debug(f"  Core IDs: {allocated_core_ids}")
            logger.debug(f"  Total allocated: {len(self.allocated_cores)}/{self.available_for_allocation}")

            return cores_to_allocate, allocated_core_ids

    def release_cores(self, task_id: str) -> bool:
        """
        Release cores allocated to a specific task.

        Args:
            task_id: Unique identifier for the task

        Returns:
            True if cores were released, False if task not found
        """
        with self.allocation_lock:
            if task_id not in self.allocations:
                logger.debug(f"No allocation found for task {task_id}")
                return False

            allocation = self.allocations[task_id]

            # Return cores to free pool
            self.free_cores.extend(allocation.allocated_cores)
            self.allocated_cores.difference_update(allocation.allocated_cores)

            # Remove allocation record
            del self.allocations[task_id]

            logger.info(f"Released {len(allocation.allocated_cores)} cores from {task_id}")
            logger.debug(f"  Total allocated: {len(self.allocated_cores)}/{self.available_for_allocation}")

            return True

    def get_worker_count_for_task(self, task_type: str = 'default',
                                  fallback: int = 2) -> int:
        """
        Get recommended worker count for a task type without allocation.

        This is a simplified method for modules that just need a worker count
        recommendation without formal allocation tracking.

        Args:
            task_type: Type of task
            fallback: Fallback value if no cores available

        Returns:
            Recommended number of workers
        """
        config = self.task_configs.get(task_type, self.task_configs['default'])

        with self.allocation_lock:
            currently_allocated = len(self.allocated_cores)
            cores_free = self.available_for_allocation - currently_allocated

            if cores_free <= 0:
                return fallback

            recommended = int(cores_free * config['core_percentage'])
            recommended = min(recommended, config['max_workers'])
            recommended = max(fallback, recommended)

            return recommended

    def get_status(self) -> Dict:
        """Get current allocation status"""
        with self.allocation_lock:
            return {
                'total_cores': self.total_cores,
                'system_reserved': self.system_reserved,
                'available_for_allocation': self.available_for_allocation,
                'currently_allocated': len(self.allocated_cores),
                'cores_free': self.available_for_allocation - len(self.allocated_cores),
                'active_tasks': len(self.allocations),
                'allocations': {
                    task_id: {
                        'type': alloc.task_type,
                        'cores': len(alloc.allocated_cores),
                        'priority': alloc.priority,
                        'duration': time.time() - alloc.allocated_at
                    }
                    for task_id, alloc in self.allocations.items()
                }
            }

    def cleanup_stale_allocations(self, max_age_seconds: float = 3600):
        """
        Clean up allocations older than specified age.

        Args:
            max_age_seconds: Maximum age for allocations (default 1 hour)
        """
        with self.allocation_lock:
            current_time = time.time()
            stale_tasks = []

            for task_id, allocation in self.allocations.items():
                age = current_time - allocation.allocated_at
                if age > max_age_seconds:
                    stale_tasks.append(task_id)

            for task_id in stale_tasks:
                logger.warning(f"Cleaning up stale allocation for {task_id}")
                self.release_cores(task_id)

    def reset(self):
        """Reset all allocations (use with caution!)"""
        with self.allocation_lock:
            self.allocations.clear()
            self.allocated_cores.clear()
            self.free_cores = list(range(self.available_for_allocation))
            logger.warning("CentralizedCoreManager reset - all allocations cleared")


# Convenience function for modules that just need worker count
def get_optimal_workers(task_type: str = 'default', fallback: int = 2) -> int:
    """
    Convenience function to get optimal worker count for a task.

    Args:
        task_type: Type of task ('table_extraction', 'equation_extraction', etc.)
        fallback: Fallback value if manager unavailable

    Returns:
        Recommended number of workers
    """
    try:
        manager = CentralizedCoreManager()
        return manager.get_worker_count_for_task(task_type, fallback)
    except Exception as e:
        logger.error(f"Failed to get worker count from CentralizedCoreManager: {e}")
        return fallback