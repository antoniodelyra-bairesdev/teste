import asyncio
import time
from typing import Any, Awaitable, TypeVar

from fastapi import HTTPException

from ehp.config import settings
from ehp.utils.base import log_error

T = TypeVar("T")


class QueryTimeoutError(Exception):
    """Custom exception for query timeouts."""

    def __init__(self, duration: float, timeout: float):
        self.duration = duration
        self.timeout = timeout
        super().__init__(f"Query timed out after {duration:.2f}s (limit: {timeout}s)")


async def with_query_timeout(
    coro: Awaitable[T], timeout_seconds: float = None
) -> T:
    """
    Execute a coroutine with a timeout and performance monitoring.
    
    Args:
        coro: The async coroutine to execute
        timeout_seconds: Timeout in seconds (defaults to settings.QUERY_TIMEOUT)
        
    Returns:
        The result of the coroutine
        
    Raises:
        HTTPException: 408 Request Timeout if query exceeds timeout
        QueryTimeoutError: Internal timeout exception with timing details
    """
    if timeout_seconds is None:
        timeout_seconds = settings.QUERY_TIMEOUT
    
    start_time = time.time()
    
    try:
        result = await asyncio.wait_for(coro, timeout=timeout_seconds)
        duration = time.time() - start_time
        
        # Log slow queries that didn't timeout
        if duration > settings.SLOW_QUERY_THRESHOLD:
            log_error(
                f"Slow query detected: {duration:.2f}s "
                f"(threshold: {settings.SLOW_QUERY_THRESHOLD}s)"
            )
        
        return result
        
    except asyncio.TimeoutError:
        duration = time.time() - start_time
        error_msg = f"Query timeout after {duration:.2f}s (limit: {timeout_seconds}s)"
        log_error(error_msg)
        
        # Raise HTTP 408 Request Timeout
        raise HTTPException(
            status_code=408,
            detail=f"Request timeout: Query took longer than {timeout_seconds}s"
        )
    except Exception as e:
        duration = time.time() - start_time
        log_error(f"Query failed after {duration:.2f}s: {e}")
        raise


def enforce_item_limit(limit: int, max_allowed: int = None) -> int:
    """
    Enforce maximum item limits for queries.
    
    Args:
        limit: Requested limit
        max_allowed: Maximum allowed items (defaults to settings.MAX_QUERY_ITEMS)
        
    Returns:
        Capped limit value
    """
    if max_allowed is None:
        max_allowed = settings.MAX_QUERY_ITEMS
    
    return min(limit, max_allowed)


def safe_page_size(size: int) -> int:
    """
    Ensure page size doesn't exceed safe limits.
    
    Args:
        size: Requested page size
        
    Returns:
        Safe page size
    """
    return enforce_item_limit(size, settings.MAX_QUERY_ITEMS)
