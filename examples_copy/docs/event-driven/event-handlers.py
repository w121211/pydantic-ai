import asyncio
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Generic, List, Protocol, TypeVar

T = TypeVar('T')


class Event(Generic[T]):
    def __init__(self, type: str, data: T):
        self.type = type
        self.data = data


class SyncEventHandler(Protocol[T]):
    def __call__(self, data: T) -> None: ...


class AsyncEventHandler(Protocol[T]):
    async def __call__(self, data: T) -> None: ...


EventHandler = AsyncEventHandler[T] | SyncEventHandler[T]


class EventStream(Generic[T]):
    """Event stream with type-based subscription support for both sync and async handlers"""

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        self._async_handlers: Dict[str, List[AsyncEventHandler[T]]] = defaultdict(list)
        self._sync_handlers: Dict[str, List[SyncEventHandler[T]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler[T]) -> None:
        if asyncio.iscoroutinefunction(handler):
            self._async_handlers[event_type].append(handler)
        else:
            self._sync_handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler[T]) -> None:
        try:
            if asyncio.iscoroutinefunction(handler):
                self._async_handlers[event_type].remove(handler)
            else:
                self._sync_handlers[event_type].remove(handler)
        except ValueError:
            self._logger.warning(f'Handler not found for event type: {event_type}')

    async def publish(self, event: Event[T]) -> None:
        event_type = event.type

        # Run sync handlers
        for handler in self._sync_handlers[event_type]:
            try:
                handler(event.data)
            except Exception as e:
                self._logger.error(f'Error in sync handler: {e}', exc_info=True)

        # Run async handlers concurrently
        tasks = [handler(event.data) for handler in self._async_handlers[event_type]]

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    self._logger.error(
                        f'Error in async handler: {result}', exc_info=True
                    )


class TaskManager:
    """Manages all running tasks"""

    def __init__(self, event_stream: EventStream):
        self.event_stream = event_stream
        self.active_tasks: Dict[str, Task] = {}
        self._setup_handlers()

    def _setup_handlers(self):
        # Task lifecycle
        self.event_stream.subscribe(EventType.TASK_CREATE, self._on_task_create)
        self.event_stream.subscribe(EventType.TASK_COMPLETE, self._on_task_complete)
        self.event_stream.subscribe(EventType.TASK_ERROR, self._on_task_error)

        # Subtask coordination
        self.event_stream.subscribe(
            EventType.SUBTASK_COMPLETE, self._on_subtask_complete
        )
        self.event_stream.subscribe(EventType.SUBTASK_ERROR, self._on_subtask_error)

    async def _on_task_create(self, data: Dict[str, Any]):
        task_id = data['task_id']
        task_path = Path(data['path'])

        task = Task(task_id, task_path, self.event_stream)
        await task.init()
        self.active_tasks[task_id] = task

    async def _on_task_complete(self, data: Dict[str, Any]):
        task_id = data['task_id']
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    async def _on_task_error(self, data: Dict[str, Any]):
        task_id = data['task_id']
        error = data['error']

        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            await self._update_task_status(task, TaskStatus.ERROR)

    async def _on_subtask_complete(self, data: Dict[str, Any]):
        task_id = data['task_id']
        subtask_id = data['subtask_id']

        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            await self._run_next_subtask(task, subtask_id)

    async def _on_subtask_error(self, data: Dict[str, Any]):
        task_id = data['task_id']
        subtask_id = data['subtask_id']

        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            await self._update_subtask_status(task, subtask_id, SubtaskStatus.ERROR)


class ChatManager:
    """Manages active chats"""

    def __init__(self, event_stream: EventStream):
        self.event_stream = event_stream
        self.active_chats: Dict[str, Chat] = {}
        self._setup_handlers()

    def _setup_handlers(self):
        self.event_stream.subscribe(EventType.CHAT_START, self._on_chat_start)
        self.event_stream.subscribe(EventType.CHAT_MESSAGE, self._on_chat_message)
        self.event_stream.subscribe(EventType.CHAT_COMPLETE, self._on_chat_complete)
        self.event_stream.subscribe(EventType.CHAT_ERROR, self._on_chat_error)

    async def _on_chat_start(self, data: Dict[str, Any]):
        task_id = data['task_id']
        subtask_id = data['subtask_id']
        chat_id = f'{task_id}_{subtask_id}'

        # Create new chat file
        await self._create_chat_file(chat_id)

    async def _on_chat_message(self, data: Dict[str, Any]):
        message = data['message']
        chat_id = data['chat_id']

        # Write message to chat file
        await self._append_message(chat_id, message)

        # Check for special commands
        if self._is_completion_command(message):
            await self._complete_chat(chat_id)

    async def _on_chat_complete(self, data: Dict[str, Any]):
        chat_id = data['chat_id']
        if chat_id in self.active_chats:
            await self._cleanup_chat(chat_id)

    async def _on_chat_error(self, data: Dict[str, Any]):
        chat_id = data['chat_id']
        error = data['error']
        await self._handle_chat_error(chat_id, error)


class FileSystemWatcher:
    """Handles file system operations"""

    def __init__(self, event_stream: EventStream):
        self.event_stream = event_stream
        self._setup_handlers()

    def _setup_handlers(self):
        self.event_stream.subscribe(EventType.CHAT_MESSAGE, self._on_chat_message)
        self.event_stream.subscribe(
            EventType.SUBTASK_COMPLETE, self._on_subtask_complete
        )

    async def _on_chat_message(self, data: Dict[str, Any]):
        chat_id = data['chat_id']
        message = data['message']

        async with self._get_file_lock(chat_id):
            await self._write_message(chat_id, message)

    async def _on_subtask_complete(self, data: Dict[str, Any]):
        task_id = data['task_id']
        subtask_id = data['subtask_id']

        async with self._get_file_lock(f'{task_id}_{subtask_id}'):
            await self._write_subtask_output(task_id, subtask_id)


# Example logging handler
def log_events(data: Dict[str, Any]):
    """Simple sync logging handler"""
    print(f'Event data: {data}')


# Example usage
async def setup_system():
    event_stream = EventStream()

    # Add general logging
    for event_type in EventType:
        event_stream.subscribe(event_type, log_events)

    # Initialize managers
    task_manager = TaskManager(event_stream)
    chat_manager = ChatManager(event_stream)
    fs_watcher = FileSystemWatcher(event_stream)

    return event_stream, task_manager, chat_manager, fs_watcher
