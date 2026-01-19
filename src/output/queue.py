"""Retry queue for failed write operations.

Provides tenacity-based retry logic for output adapter calls
and an in-memory queue for tracking failed items.
"""

import functools
from collections.abc import Awaitable, Callable
from typing import TypeVar

import structlog
from tenacity import (
    RetryError,
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.adapters.base import WriteResult

logger = structlog.get_logger()

# Type variable for generic async functions returning WriteResult
T = TypeVar("T")

# Exceptions that are retriable (transient failures)
RETRIABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
)

# Try to add gspread and googleapiclient exceptions if available
try:
    import gspread.exceptions

    RETRIABLE_EXCEPTIONS = (*RETRIABLE_EXCEPTIONS, gspread.exceptions.APIError)
except ImportError:
    pass

try:
    from googleapiclient.errors import HttpError

    RETRIABLE_EXCEPTIONS = (*RETRIABLE_EXCEPTIONS, HttpError)
except ImportError:
    pass


def write_with_retry(
    func: Callable[..., Awaitable[WriteResult]],
) -> Callable[..., Awaitable[WriteResult]]:
    """Decorator to retry write operations with exponential backoff.

    Retries up to 5 times with exponential backoff (4s min, 60s max).
    Logs before each retry attempt.

    Args:
        func: Async function that returns WriteResult

    Returns:
        Wrapped function with retry logic
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> WriteResult:
        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            retry=retry_if_exception_type(RETRIABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, log_level=20),  # INFO level
            reraise=True,
        )
        async def inner():
            return await func(*args, **kwargs)

        try:
            return await inner()
        except RetryError as e:
            # All retries exhausted
            last_err = e.last_attempt.exception() if e.last_attempt else None
            logger.error(
                "retry exhausted",
                function=func.__name__,
                attempts=5,
                last_error=str(last_err) if last_err else None,
            )
            err_msg = f"Retry exhausted after 5 attempts: {last_err or 'unknown error'}"
            return WriteResult(
                success=False,
                error_message=err_msg,
            )
        except Exception as e:
            # Non-retriable exception
            logger.error(
                "non-retriable error",
                function=func.__name__,
                error=str(e),
            )
            return WriteResult(
                success=False,
                error_message=str(e),
            )

    return wrapper


class RetryQueue:
    """Simple in-memory queue for failed write operations.

    Stores failed items for later retry or manual intervention.
    SQLite persistence is planned for future work.
    """

    def __init__(self):
        """Initialize empty queue."""
        self._items: list[dict] = []

    def add(self, item: dict) -> None:
        """Add a failed item to the queue.

        Args:
            item: Dict containing item data and failure info
        """
        self._items.append(item)
        logger.info("item added to retry queue", item_type=item.get("type", "unknown"))

    def get_pending(self) -> list[dict]:
        """Get all pending items in the queue.

        Returns:
            List of queued items
        """
        return list(self._items)

    def clear(self) -> None:
        """Remove all items from the queue."""
        count = len(self._items)
        self._items.clear()
        logger.info("retry queue cleared", items_removed=count)

    def __len__(self) -> int:
        """Return number of items in queue."""
        return len(self._items)
