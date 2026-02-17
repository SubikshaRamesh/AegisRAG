"""
Error handling and custom exceptions for AegisRAG.
"""

import asyncio
import time
from typing import TypeVar, Callable, Any
from functools import wraps

from core.logger import get_logger

logger = get_logger(__name__)


# ============ CUSTOM EXCEPTIONS ============

class AegisRAGError(Exception):
    """Base exception for all AegisRAG errors."""
    pass


class IngestionError(AegisRAGError):
    """Raised when ingestion fails."""
    pass


class RetrievalError(AegisRAGError):
    """Raised when retrieval fails."""
    pass


class EmbeddingError(AegisRAGError):
    """Raised when embedding generation fails."""
    pass


class VectorStoreError(AegisRAGError):
    """Raised when vector store operations fail."""
    pass


class LLMError(AegisRAGError):
    """Raised when LLM inference fails."""
    pass


class ValidationError(AegisRAGError):
    """Raised when validation fails."""
    pass


class ConfigurationError(AegisRAGError):
    """Raised when configuration is invalid."""
    pass


# ============ RETRY LOGIC ============

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator to retry a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay each retry
        exceptions: Tuple of exceptions to catch
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    logger.debug(f"Attempt {attempt + 1}/{max_attempts} for {func.__name__}")
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")

            raise last_exception

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Async decorator to retry an async function with exponential backoff.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    logger.debug(
                        f"Attempt {attempt + 1}/{max_attempts} for {func.__name__}"
                    )
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )

            raise last_exception

        return wrapper

    return decorator


# ============ ERROR HANDLERS ============

def safe_execute(
    func: Callable,
    *args,
    default_return: Any = None,
    error_message: str = "Operation failed",
    **kwargs
) -> Any:
    """
    Safely execute a function with error handling.
    Returns default_return on failure.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"{error_message}: {e}")
        return default_return


async def safe_execute_async(
    func: Callable,
    *args,
    default_return: Any = None,
    error_message: str = "Operation failed",
    **kwargs
) -> Any:
    """
    Safely execute an async function with error handling.
    Returns default_return on failure.
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        logger.error(f"{error_message}: {e}")
        return default_return
