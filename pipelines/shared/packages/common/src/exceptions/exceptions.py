#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Maintenance System - Custom Exception Hierarchy
Specific exception types for better error handling and debugging

Author: Claude Sonnet 4.5 (Local)
Date: 2025-10-23
Version: 1.0.0
Purpose: Step 2 - Custom Exceptions (STANDARDS_COMPLIANCE_AUDIT remediation)
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


# ==============================================================================
# BASE EXCEPTION
# ==============================================================================

class MaintenanceError(Exception):
    """
    Base exception for all context maintenance errors.

    All maintenance-specific exceptions inherit from this class.
    This allows catching all maintenance errors with a single except clause
    while still supporting specific error handling.

    Example:
        try:
            maintenance_operation()
        except MaintenanceError as e:
            logger.error(f"Maintenance failed: {e}")
    """
    pass


# ==============================================================================
# CONFIGURATION ERRORS
# ==============================================================================

class ConfigurationError(MaintenanceError):
    """
    Configuration-related errors.

    Raised when configuration is invalid, missing, or cannot be loaded.
    This is a non-retryable error - requires user intervention.

    Examples:
        - YAML file is malformed
        - Required configuration value is missing
        - Configuration value fails validation
        - Environment variable has invalid format

    Example:
        raise ConfigurationError("message_threshold must be >= 1, got -5")
    """
    pass


class ConfigurationNotFoundError(ConfigurationError):
    """
    Configuration file not found.

    Raised when expected configuration file doesn't exist and no fallback
    is available. This is distinct from missing values within the file.

    Example:
        raise ConfigurationNotFoundError("config/maintenance_config.yaml not found")
    """
    pass


class ConfigurationValidationError(ConfigurationError):
    """
    Configuration value failed validation.

    Raised when configuration value is present but fails validation rules
    (e.g., negative threshold, invalid timeout).

    Example:
        raise ConfigurationValidationError("timeout_seconds must be > 0, got -1")
    """
    pass


# ==============================================================================
# STATE PERSISTENCE ERRORS
# ==============================================================================

class StatePersistenceError(MaintenanceError):
    """
    State file persistence errors.

    Raised when state cannot be loaded, saved, or is corrupted.
    May be retryable depending on the specific cause.

    Examples:
        - State file corrupted (invalid JSON)
        - Permission denied reading/writing state
        - Disk full when saving state
        - Lock file cannot be acquired

    Example:
        raise StatePersistenceError("Failed to save state: disk full")
    """
    pass


class StateFileCorruptedError(StatePersistenceError):
    """
    State file is corrupted or invalid.

    Raised when state file exists but cannot be parsed as valid JSON
    or contains invalid data structure.

    Example:
        raise StateFileCorruptedError("Invalid JSON in maintenance_state.json")
    """
    pass


class StateLockError(StatePersistenceError):
    """
    Failed to acquire state file lock.

    Raised when file locking fails, usually due to another process
    holding the lock. This is typically retryable.

    Example:
        raise StateLockError("Another process holds the lock")
    """
    pass


# ==============================================================================
# EXECUTION ERRORS
# ==============================================================================

class ExecutionError(MaintenanceError):
    """
    Maintenance operation execution errors.

    Raised when maintenance operation fails to execute.
    Base class for specific execution failures.

    Examples:
        - Subprocess failed to start
        - Operation timed out
        - Operation returned non-zero exit code
        - Semaphore cannot be acquired

    Example:
        raise ExecutionError("Requirements sync subprocess failed")
    """
    pass


class OperationTimeoutError(ExecutionError):
    """
    Maintenance operation exceeded timeout.

    Raised when an operation takes longer than the configured timeout.
    This prevents hung processes from blocking the system.

    Example:
        raise OperationTimeoutError("version_update exceeded 300s timeout")
    """
    pass


class OperationFailedError(ExecutionError):
    """
    Maintenance operation failed.

    Raised when operation completes but returns error status
    (non-zero exit code or explicit failure signal).

    Example:
        raise OperationFailedError("requirements_sync exited with code 1")
    """
    pass


class SemaphoreError(ExecutionError):
    """
    Failed to acquire execution semaphore.

    Raised when another maintenance execution is already running
    (single-flight protection). This is expected and not an error condition.

    Example:
        raise SemaphoreError("Maintenance already running (PID 12345)")
    """
    pass


# ==============================================================================
# VERSION DETECTION ERRORS
# ==============================================================================

class VersionDetectionError(MaintenanceError):
    """
    Failed to detect system version.

    Raised when VERSION file cannot be read or contains invalid data.
    This may trigger maintenance even though it's an error.

    Examples:
        - VERSION file missing
        - VERSION file empty
        - VERSION file contains invalid format

    Example:
        raise VersionDetectionError("VERSION file not found")
    """
    pass


# ==============================================================================
# REGISTRY ERRORS
# ==============================================================================

class RegistryError(MaintenanceError):
    """
    Module registry errors.

    Raised when MODULE_REGISTRY.json cannot be read or is invalid.
    This is typically a non-critical error.

    Examples:
        - MODULE_REGISTRY.json missing
        - MODULE_REGISTRY.json corrupted
        - MODULE_REGISTRY.json has invalid structure

    Example:
        raise RegistryError("MODULE_REGISTRY.json is not valid JSON")
    """
    pass


# ==============================================================================
# RETRYABLE VS NON-RETRYABLE CLASSIFICATION
# ==============================================================================

# Exceptions that are typically retryable (transient failures)
RETRYABLE_EXCEPTIONS = (
    StateLockError,
    OperationTimeoutError,
    # SemaphoreError is expected, not retryable but not an error either
)

# Exceptions that are NOT retryable (require intervention)
NON_RETRYABLE_EXCEPTIONS = (
    ConfigurationError,
    ConfigurationNotFoundError,
    ConfigurationValidationError,
    StateFileCorruptedError,
    VersionDetectionError,
    RegistryError,
)


def is_retryable(exception: Exception) -> bool:
    """
    Check if an exception is retryable.

    Retryable exceptions are transient failures that may succeed if
    the operation is retried after a delay.

    Args:
        exception: Exception instance to check

    Returns:
        True if exception is retryable, False otherwise

    Example:
        try:
            operation()
        except MaintenanceError as e:
            if is_retryable(e):
                retry_operation()
            else:
                log_permanent_failure()
    """
    return isinstance(exception, RETRYABLE_EXCEPTIONS)


def is_non_retryable(exception: Exception) -> bool:
    """
    Check if an exception is non-retryable.

    Non-retryable exceptions require user intervention (fixing
    configuration, file permissions, etc.) and will not succeed
    even if retried.

    Args:
        exception: Exception instance to check

    Returns:
        True if exception is non-retryable, False otherwise
    """
    return isinstance(exception, NON_RETRYABLE_EXCEPTIONS)
