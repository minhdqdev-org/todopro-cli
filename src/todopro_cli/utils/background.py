"""Background task runner with retry logic."""

import asyncio
import multiprocessing
import sys
from typing import Any, Callable, Dict, Optional

from todopro_cli.utils.error_logger import log_error


def run_in_background(
    func: Callable,
    command: str,
    context: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> None:
    """
    Run an async function in a background process with retry logic.
    
    Args:
        func: Async function to run
        command: Command name for logging
        context: Context information for logging
        max_retries: Maximum number of retry attempts (default: 3)
    """
    def _background_runner():
        """Worker function that runs in the background process."""
        import asyncio
        
        async def _run_with_retry():
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    await func()
                    return  # Success
                except Exception as e:
                    last_error = str(e)
                    if attempt < max_retries - 1:
                        # Wait before retry (exponential backoff)
                        await asyncio.sleep(2 ** attempt)
                    continue
            
            # All retries failed, log error
            if last_error:
                log_error(
                    command=command,
                    error=last_error,
                    context=context,
                    retries=max_retries - 1,
                )
        
        # Run the async function
        try:
            asyncio.run(_run_with_retry())
        except Exception:
            # Silently fail - error is already logged
            pass
    
    # Start background process
    process = multiprocessing.Process(target=_background_runner, daemon=True)
    process.start()
    # Don't wait for it to finish
