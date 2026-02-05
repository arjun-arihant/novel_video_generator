/"""
Async context managers and utilities for resource management.
"""

import asyncio
import contextlib
import time
from contextlib import asynccontextmanager
from typing import Optional, Type, List, Any, AsyncGenerator, Callable
from dataclasses import dataclass

from .exceptions import CancelledError, TimeoutError


@dataclass
class TaskResult:
    """Result from a managed task."""
    success: bool
    result: Any = None
    error: Optional[Exception] = None
    duration: float = 0.0


@asynccontextmanager
async def managed_task(
    coro,
    timeout: Optional[float] = None,
    cancellation_event: Optional[asyncio.Event] = None,
    on_cancel: Optional[Callable] = None
) -> AsyncGenerator[Any, None]:
    """
    Context manager for running async tasks with proper cleanup.
    
    Args:
        coro: Coroutine to run
        timeout: Optional timeout in seconds
        cancellation_event: Optional event to signal cancellation
        on_cancel: Optional callback when cancelled
        
    Example:
        async with managed_task(long_running_coro(), timeout=30) as result:
            print(result)
    """
    task = None
    try:
        task = asyncio.create_task(coro)
        
        # Wait for completion, timeout, or cancellation
        done, pending = await asyncio.wait(
            [task],
            timeout=timeout,
            return_when=asyncio.FIRST_COMPLETED
        )
        
        if task in done:
            yield await task
        else:
            # Timeout occurred
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            raise TimeoutError(
                "Operation timed out",
                timeout_seconds=timeout
            )
            
    except asyncio.CancelledError:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        if on_cancel:
            await on_cancel()
        
        raise CancelledError("Operation was cancelled")
        
    finally:
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


@asynccontextmanager
async def semaphore_pool(
    max_concurrent: int,
    timeout: Optional[float] = None
) -> AsyncGenerator[asyncio.Semaphore, None]:
    """
    Context manager for managing a semaphore pool.
    
    Args:
        max_concurrent: Maximum number of concurrent operations
        timeout: Optional timeout for acquiring semaphore
        
    Example:
        async with semaphore_pool(5) as sem:
            async with sem:
                await process_item(item)
    """
    sem = asyncio.Semaphore(max_concurrent)
    
    try:
        yield sem
    finally:
        # Semaphore doesn't need explicit cleanup
        pass


@asynccontextmanager
async def rate_limiter(
    rate: float = 1.0,  # requests per second
    burst: int = 1
) -> AsyncGenerator[None, None]:
    """
    Token bucket rate limiter.
    
    Args:
        rate: Average rate of requests per second
        burst: Maximum burst size
        
    Example:
        async with rate_limiter(rate=2.0):  # 2 requests per second
            await api_call()
    """
    tokens = burst
    last_update = time.time()
    lock = asyncio.Lock()
    
    async def acquire():
        nonlocal tokens, last_update
        async with lock:
            now = time.time()
            elapsed = now - last_update
            tokens = min(burst, tokens + elapsed * rate)
            last_update = now
            
            if tokens < 1:
                wait_time = (1 - tokens) / rate
                await asyncio.sleep(wait_time)
                tokens = 0
            else:
                tokens -= 1
    
    await acquire()
    try:
        yield
    finally:
        pass


@asynccontextmanager
async def managed_session(
    session_factory: Callable,
    cleanup: Optional[Callable] = None
) -> AsyncGenerator[Any, None]:
    """
    Context manager for managing external sessions (HTTP, DB, etc.).
    
    Args:
        session_factory: Callable that creates the session
        cleanup: Optional cleanup function
        
    Example:
        async with managed_session(create_http_session) as session:
            await session.get(url)
    """
    session = None
    try:
        if asyncio.iscoroutinefunction(session_factory):
            session = await session_factory()
        else:
            session = session_factory()
        
        yield session
        
    finally:
        if session and cleanup:
            if asyncio.iscoroutinefunction(cleanup):
                await cleanup(session)
            else:
                cleanup(session)


class AsyncBatchProcessor:
    """
    Process items in batches with concurrency control.
    
    Example:
        processor = AsyncBatchProcessor(max_concurrent=5)
        results = await processor.process(items, process_func)
    """
    
    def __init__(
        self,
        max_concurrent: int = 5,
        retry_count: int = 3,
        retry_delay: float = 1.0
    ):
        self.max_concurrent = max_concurrent
        self.retry_count = retry_count
        self.retry_delay = retry_delay
    
    async def process(
        self,
        items: List[Any],
        processor: Callable[[Any], Any],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[TaskResult]:
        """
        Process items with concurrency control and retry logic.
        
        Args:
            items: List of items to process
            processor: Async function to process each item
            on_progress: Optional progress callback(current, total)
            
        Returns:
            List of TaskResult objects
        """
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = []
        completed = 0
        
        async def process_with_semaphore(item: Any) -> TaskResult:
            async with semaphore:
                return await self._process_with_retry(item, processor)
        
        # Create all tasks
        tasks = [process_with_semaphore(item) for item in items]
        
        # Process and update progress
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            completed += 1
            
            if on_progress:
                on_progress(completed, len(items))
        
        return results
    
    async def _process_with_retry(
        self,
        item: Any,
        processor: Callable[[Any], Any]
    ) -> TaskResult:
        """Process an item with retry logic."""
        start_time = time.time()
        
        for attempt in range(self.retry_count):
            try:
                if asyncio.iscoroutinefunction(processor):
                    result = await processor(item)
                else:
                    result = processor(item)
                
                return TaskResult(
                    success=True,
                    result=result,
                    duration=time.time() - start_time
                )
                
            except Exception as e:
                if attempt == self.retry_count - 1:
                    return TaskResult(
                        success=False,
                        error=e,
                        duration=time.time() - start_time
                    )
                
                await asyncio.sleep(self.retry_delay * (attempt + 1))
        
        # Should never reach here
        return TaskResult(success=False, error=Exception("Max retries exceeded"))


@contextlib.asynccontextmanager
async def temporary_file(
    suffix: str = "",
    prefix: str = "tmp",
    directory: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Context manager for temporary file cleanup.
    
    Example:
        async with temporary_file(suffix='.mp3') as path:
            await generate_audio(path)
            # File is automatically deleted when exiting context
    """
    import tempfile
    import os
    
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=directory)
    os.close(fd)
    
    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


@contextlib.asynccontextmanager
async def temporary_directory(
    prefix: str = "tmp",
    directory: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Context manager for temporary directory cleanup.
    
    Example:
        async with temporary_directory() as tmpdir:
            await process_files(tmpdir)
            # Directory is automatically deleted when exiting context
    """
    import tempfile
    import shutil
    
    tmpdir = tempfile.mkdtemp(prefix=prefix, dir=directory)
    
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except FileNotFoundError:
            pass
