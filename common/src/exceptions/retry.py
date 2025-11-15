#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Maintenance System - Retry Logic with Exponential Backoff
Decorator for retrying operations that may fail transiently

Author: Claude Sonnet 4.5 (Local)
Date: 2025-10-24
Version: 1.0.0
Purpose: Step 3 - Retry Logic (STANDARDS_COMPLIANCE_AUDIT remediation)
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

import time
import random
import logging
import functools
from typing import Callable, Any, TypeVar, Optional

from .exceptions import is_retryable

logger = logging.getLogger(__name__)

# Type variable for function return type preservation
T = TypeVar('T')


def retry_on_error(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying operations with exponential backoff and jitter.

    Only retries exceptions classified as retryable by is_retryable() function.
    Non-retryable exceptions are raised immediately.

    Args:
        max_attempts: Maximum number of attempts (including initial attempt)
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds (caps exponential growth)
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delay (recommended)

    Returns:
        Decorator function that wraps the target function with retry logic

    Retry Delay Formula:
        delay = min(initial_delay * (exponential_base ** attempt), max_delay)
        if jitter:
            delay = delay * random.uniform(0.5, 1.5)

    Example:
        @retry_on_error(max_attempts=3, initial_delay=1.0)
        def flaky_operation():
            # May fail with retryable exceptions
            pass

    Behavior:
        - Attempt 1: No delay (initial attempt)
        - Attempt 2: 1.0s delay (with jitter: 0.5-1.5s)
        - Attempt 3: 2.0s delay (with jitter: 1.0-3.0s)
        - Attempt 4: 4.0s delay (with jitter: 2.0-6.0s)
        - etc., capped at max_delay

    Notes:
        - Logs each retry attempt with delay information
        - Logs final failure if all attempts exhausted
        - Non-retryable exceptions bypass retry logic
        - Jitter prevents thundering herd problem
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(1, max_attempts + 1):
                try:
                    # Execute the wrapped function
                    result = func(*args, **kwargs)

                    # Success - log if this wasn't the first attempt
                    if attempt > 1:
                        logger.info(
                            f"✅ {func.__name__} succeeded on attempt {attempt}/{max_attempts}"
                        )

                    return result

                except Exception as e:
                    last_exception = e

                    # Check if exception is retryable
                    if not is_retryable(e):
                        # Non-retryable exception - fail immediately
                        logger.warning(
                            f"❌ {func.__name__} failed with non-retryable exception: {type(e).__name__}: {e}"
                        )
                        raise

                    # Check if we have more attempts
                    if attempt >= max_attempts:
                        # Exhausted all attempts
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {type(e).__name__}: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(
                        initial_delay * (exponential_base ** (attempt - 1)),
                        max_delay
                    )

                    # Add jitter to prevent thundering herd
                    if jitter:
                        jitter_factor = random.uniform(0.5, 1.5)
                        delay = delay * jitter_factor

                    # Log retry attempt
                    logger.warning(
                        f"⚠️ {func.__name__} failed on attempt {attempt}/{max_attempts} "
                        f"({type(e).__name__}: {e}). "
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Wait before retry
                    time.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            else:
                raise RuntimeError(f"{func.__name__} failed without exception")

        return wrapper
    return decorator


def retry_with_config(config: dict) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Convenience wrapper that accepts configuration dictionary.

    Useful for loading retry configuration from YAML files.

    Args:
        config: Dictionary with retry configuration keys:
            - max_attempts (int): Maximum retry attempts
            - initial_delay (float): Initial delay in seconds
            - max_delay (float): Maximum delay in seconds
            - exponential_base (float): Base for exponential backoff
            - jitter (bool): Whether to add jitter

    Returns:
        Configured retry decorator

    Example:
        retry_config = {
            'max_attempts': 5,
            'initial_delay': 2.0,
            'max_delay': 60.0,
            'exponential_base': 2.0,
            'jitter': True
        }

        @retry_with_config(retry_config)
        def my_operation():
            pass
    """
    return retry_on_error(
        max_attempts=config.get('max_attempts', 3),
        initial_delay=config.get('initial_delay', 1.0),
        max_delay=config.get('max_delay', 30.0),
        exponential_base=config.get('exponential_base', 2.0),
        jitter=config.get('jitter', True)
    )
