import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from collections.abc import Awaitable
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict, List

from .type_defs import BaseEvent, EventType

# T = TypeVar('T', bound=BaseEvent)

EventHandler = Callable[[BaseEvent], None]  # Synchronous handler
AsyncEventHandler = Callable[[BaseEvent], Awaitable[None]]  # Asynchronous handler


class IEventBus(ABC):
    """Event bus interface defining core functionality."""

    @abstractmethod
    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to all registered handlers."""
        pass

    @abstractmethod
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a synchronous handler to an event type."""
        pass

    @abstractmethod
    def subscribe_async(
        self, event_type: EventType, handler: AsyncEventHandler
    ) -> None:
        """Subscribe an asynchronous handler to an event type."""
        pass

    @abstractmethod
    def unsubscribe(
        self, event_type: EventType, handler: EventHandler | AsyncEventHandler
    ) -> None:
        """Unsubscribe a handler from an event type."""
        pass


class EventBus(IEventBus):
    """Implementation of the event bus that supports both synchronous and asynchronous event handlers."""

    def __init__(self, max_workers: int = 5):
        """Initialize the event bus."""
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._async_handlers: Dict[EventType, List[AsyncEventHandler]] = {}
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._logger = logging.getLogger(__name__)

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        """Subscribe a synchronous handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        self._logger.debug(f'Subscribed sync handler to {event_type}')

    def subscribe_async(
        self, event_type: EventType, handler: AsyncEventHandler
    ) -> None:
        """Subscribe an asynchronous handler to an event type."""
        if event_type not in self._async_handlers:
            self._async_handlers[event_type] = []
        self._async_handlers[event_type].append(handler)
        self._logger.debug(f'Subscribed async handler to {event_type}')

    def unsubscribe(
        self, event_type: EventType, handler: EventHandler | AsyncEventHandler
    ) -> None:
        """Unsubscribe a handler from an event type."""
        # 檢查 handler 是否是非同步函數
        is_async = inspect.iscoroutinefunction(handler)

        # 根據 handler 類型選擇對應的 handlers 字典
        handlers = self._async_handlers if is_async else self._handlers

        # 嘗試移除 handler
        if event_type in handlers:
            try:
                handlers[event_type].remove(handler)  # type: ignore
                self._logger.debug(
                    f'Unsubscribed {"async" if is_async else "sync"} handler from {event_type}'
                )
            except ValueError:
                pass

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to all registered handlers."""
        event_type = event.type
        tasks: List[asyncio.Task[None]] = []

        # Handle synchronous handlers
        sync_handlers = self._handlers.get(event_type, [])
        for handler in sync_handlers:
            # Run sync handlers in thread pool to avoid blocking
            task = asyncio.create_task(
                asyncio.to_thread(self._execute_sync_handler, handler, event)
            )
            tasks.append(task)

        # Handle asynchronous handlers
        async_handlers = self._async_handlers.get(event_type, [])
        for handler in async_handlers:
            task = asyncio.create_task(self._execute_async_handler(handler, event))
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks)
            self._logger.debug(f'Published event {event_type} to {len(tasks)} handlers')

    async def _execute_async_handler(
        self, handler: AsyncEventHandler, event: BaseEvent
    ) -> None:
        """Execute an async handler safely with error handling."""
        try:
            await handler(event)
        except Exception as e:
            self._logger.error(f'Error in async event handler: {str(e)}', exc_info=True)

    def _execute_sync_handler(self, handler: EventHandler, event: BaseEvent) -> None:
        """Execute a sync handler safely with error handling."""
        try:
            handler(event)
        except Exception as e:
            self._logger.error(f'Error in sync event handler: {str(e)}', exc_info=True)

    def __del__(self):
        """Cleanup thread pool on deletion."""
        self._thread_pool.shutdown(wait=True)
