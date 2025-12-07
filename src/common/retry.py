"""Unified retry logic with exponential backoff."""

from typing import Type, Tuple, Callable, TypeVar, Any
from functools import wraps
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_attempts: int = 5,
    min_wait: int = 2,
    max_wait: int = 60,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        min_wait: Minimum wait time in seconds
        max_wait: Maximum wait time in seconds
        exceptions: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=min_wait, max=max_wait),
        retry=retry_if_exception_type(exceptions),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
