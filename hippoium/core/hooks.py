# hippoium/core/hooks.py

import inspect
import asyncio
from typing import Callable, Dict, List, Any, Optional

class HookRegistry:
    """
    Registry for managing event hooks. Allows registration of callbacks (sync or async)
    for specific events and notifies them on event trigger.
    """
    def __init__(self) -> None:
        # Mapping from event name to list of callbacks
        self._hooks: Dict[str, List[Callable[..., Any]]] = {}

    def register(self, event: str, callback: Callable[..., Any]) -> None:
        """Register a callback for a given event."""
        if event not in self._hooks:
            self._hooks[event] = []
        if callback not in self._hooks[event]:
            self._hooks[event].append(callback)

    def unregister(self, event: str, callback: Callable[..., Any]) -> None:
        """Unregister a previously registered callback from an event."""
        if event in self._hooks:
            try:
                self._hooks[event].remove(callback)
            except ValueError:
                pass  # Ignore if callback not found
        # Clean up the event list if empty
        if event in self._hooks and not self._hooks[event]:
            del self._hooks[event]

    def notify(self, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Notify all callbacks registered to an event. Supports both sync and async callbacks.
        Async callbacks are executed to completion; if called outside an event loop, this method will block until all async hooks complete.
        If called from within an existing event loop, async hooks are scheduled to run concurrently.
        """
        if event not in self._hooks:
            return
        async_tasks: List[Any] = []
        for callback in list(self._hooks[event]):
            try:
                result = callback(*args, **kwargs)
            except Exception:
                # If a hook raises an exception, we continue to the next (you may log the error here)
                continue
            if inspect.isawaitable(result):
                async_tasks.append(result)
        if async_tasks:
            # Determine if we're in an existing event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                # In an active event loop: schedule tasks to run asynchronously (do not await here)
                for task in async_tasks:
                    loop.create_task(task)
            else:
                # No active event loop: run tasks synchronously and wait for completion
                asyncio.run(asyncio.gather(*async_tasks))

    async def notify_async(self, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Async version of notify. Awaits all async callbacks. Use this within async functions if needed.
        """
        if event not in self._hooks:
            return
        tasks: List[Any] = []
        for callback in list(self._hooks[event]):
            if inspect.iscoroutinefunction(callback):
                tasks.append(callback(*args, **kwargs))
            else:
                callback(*args, **kwargs)
        if tasks:
            await asyncio.gather(*tasks)

# Create a global hook registry instance for use throughout the system
hook_registry = HookRegistry()