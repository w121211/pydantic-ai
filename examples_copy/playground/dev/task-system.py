from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from pydantic import BaseModel, Field, ValidationError, field_validator


# Event Types
class EventType(str, Enum):
    # Task Events
    TASK_CREATE = 'TASK_CREATE'
    TASK_RUN = 'TASK_RUN'
    TASK_COMPLETE = 'TASK_COMPLETE'
    TASK_ERROR = 'TASK_ERROR'

    # Subtask Events
    SUBTASK_CREATE = 'SUBTASK_CREATE'
    SUBTASK_RUN = 'SUBTASK_RUN'
    SUBTASK_COMPLETE = 'SUBTASK_COMPLETE'
    SUBTASK_ERROR = 'SUBTASK_ERROR'
    SUBTASK_RERUN = 'SUBTASK_RERUN'

    # Chat Events
    CHAT_START = 'CHAT_START'
    CHAT_MESSAGE_SENT = 'CHAT_MESSAGE_SENT'
    CHAT_MESSAGE_RECEIVED = 'CHAT_MESSAGE_RECEIVED'
    CHAT_COMPLETE = 'CHAT_COMPLETE'
    CHAT_ERROR = 'CHAT_ERROR'

    # Function Events
    FUNCTION_RUN = 'FUNCTION_RUN'
    FUNCTION_COMPLETE = 'FUNCTION_COMPLETE'
    FUNCTION_ERROR = 'FUNCTION_ERROR'

    # Agent Events
    AGENT_RUN = 'AGENT_RUN'
    AGENT_COMPLETE = 'AGENT_COMPLETE'
    AGENT_ERROR = 'AGENT_ERROR'


# Models
class TaskStatus(str, Enum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'


class SubtaskStatus(str, Enum):
    PENDING = 'PENDING'
    WAITING_EXTERNAL = 'WAITING_EXTERNAL'
    WAITING_USER = 'WAITING_USER'
    RUNNING = 'RUNNING'
    COMPLETED = 'COMPLETED'
    ERROR = 'ERROR'


class SubtaskType(str, Enum):
    PURE_AGENT = 'PURE_AGENT'
    PURE_FUNCTION = 'PURE_FUNCTION'
    HUMAN_AGENT = 'HUMAN_AGENT'


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class SubtaskInfo(BaseModel):
    type: SubtaskType
    status: SubtaskStatus
    prompt: str


class TaskLock(BaseModel):
    task_id: str
    status: TaskStatus
    current_subtask: Optional[str] = None
    subtasks: Dict[str, SubtaskInfo]


class BaseEventData(BaseModel):
    task_id: str
    subtask_id: Optional[str] = None
    error: Optional[str] = None
    message: Optional[ChatMessage] = None
    status: Optional[Union[TaskStatus, SubtaskStatus]] = None


class Event(BaseModel):
    type: EventType
    data: BaseEventData
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_validator('data')
    def validate_event_data(cls, v: BaseEventData):
        if type(v) == BaseEventData:
            raise ValidationError('Cannot use BaseEventData directly')
        return v


AsyncEventHandler = Callable[[BaseEventData], Awaitable[None]]
SyncEventHandler = Callable[[BaseEventData], None]


class EventStream:
    """Event stream with type-based subscription"""

    def __init__(self):
        # self.handlers: Dict[EventType, list[EventHandler]] = defaultdict(list)
        self.async_handlers: Dict[EventType, list[AsyncEventHandler]] = defaultdict(
            list
        )
        self.sync_handlers: Dict[EventType, list[SyncEventHandler]] = defaultdict(list)

    def subscribe(
        self, event_type: EventType, handler: Union[AsyncEventHandler, SyncEventHandler]
    ):
        """Subscribe to specific event type"""
        if asyncio.iscoroutinefunction(handler):
            self.async_handlers[event_type].append(handler)
        else:
            self.sync_handlers[event_type].append(handler)  # type: ignore

    def unsubscribe(
        self, event_type: EventType, handler: AsyncEventHandler | SyncEventHandler
    ):
        """Unsubscribe from specific event type"""
        if asyncio.iscoroutinefunction(handler):
            self.async_handlers[event_type].remove(handler)
        else:
            self.sync_handlers[event_type].remove(handler)  # type: ignore

    async def publish(self, event: Event):
        """Publish event to all subscribers"""
        event_type = event.type

        # Run sync handlers
        for handler in self.sync_handlers[event_type]:
            try:
                handler(event.data)
            except Exception as e:
                print(f'Error in sync handler: {e}')

        # Run async handlers concurrently
        tasks = [handler(event.data) for handler in self.async_handlers[event_type]]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


class TaskCreateEventData(BaseEventData):
    task_id: str
    task_path: Path


class Task:
    def __init__(self, task_id: str, path: Path, event_stream: EventStream):
        self.task_id = task_id
        self.path = path
        self.event_stream = event_stream
        self.lock_file = path / 'task.lock'
        self.subtasks: Dict[str, Subtask] = {}

    async def init(self) -> None:
        if not self.path.exists():
            self.path.mkdir(parents=True)

        if not self.lock_file.exists():
            # Initialize with step0
            step0_folder = self.path / 'step0'
            if step0_folder.exists():
                await self._init_from_step0()
            else:
                await self._run_step0()

        lock = self._load_lock()
        for subtask_id, info in lock.subtasks.items():
            self.subtasks[subtask_id] = Subtask(
                subtask_id=subtask_id,
                task=self,
                path=self.path / subtask_id,
                info=info,
                event_stream=self.event_stream,
            )

    async def run(self) -> None:
        await self.event_stream.publish(
            Event(type=EventType.TASK_RUN, data=EventData(task_id=self.task_id))
        )

        try:
            lock = self._load_lock()
            current = lock.current_subtask

            if current:
                # Continue from current subtask
                await self.subtasks[current].run()
            else:
                # Start from beginning
                for subtask in self.subtasks.values():
                    await subtask.run()

            await self.event_stream.publish(
                Event(
                    type=EventType.TASK_COMPLETE, data=EventData(task_id=self.task_id)
                )
            )

        except Exception as e:
            await self.event_stream.publish(
                Event(
                    type=EventType.TASK_ERROR,
                    data=EventData(task_id=self.task_id, error=str(e)),
                )
            )
            raise

    def _load_lock(self) -> TaskLock:
        with open(self.lock_file) as f:
            return TaskLock.parse_raw(f.read())

    async def _init_from_step0(self) -> None:
        # Initialize task from step0 results
        pass

    async def _run_step0(self) -> None:
        # Run initial step0
        pass


class Subtask:
    def __init__(
        self,
        subtask_id: str,
        task: Task,
        path: Path,
        info: SubtaskInfo,
        event_stream: EventStream,
    ):
        self.subtask_id = subtask_id
        self.task = task
        self.path = path
        self.info = info
        self.event_stream = event_stream

        # A subtask has multiple chats
        self.chats = {}

    async def init(self):
        """Initialize

        1. Load subtask path to get chat files in the path.
        2. Get the latest
        """
        pass

    async def run(self) -> None:
        """1. Determine the subtask kind. For now, we only consider the human-agent chat.
        2. Run the human-agent chat.
        3. ...
        """
        await self.event_stream.publish(
            Event(
                type=EventType.SUBTASK_RUN_START,
                data=EventData(task_id=self.task.task_id, subtask_id=self.subtask_id),
            )
        )

        try:
            if not self.path.exists():
                self.path.mkdir(parents=True)

            match self.info.type:
                case SubtaskType.PURE_AGENT:
                    await self._run_pure_agent()
                case SubtaskType.PURE_FUNCTION:
                    await self._run_pure_function()
                case SubtaskType.HUMAN_AGENT:
                    await self._run_human_agent()

            await self.event_stream.publish(
                Event(
                    type=EventType.SUBTASK_RUN_COMPLETE,
                    data=EventData(
                        task_id=self.task.task_id, subtask_id=self.subtask_id
                    ),
                )
            )

        except Exception as e:
            await self.event_stream.publish(
                Event(
                    type=EventType.SUBTASK_ERROR,
                    data=EventData(
                        task_id=self.task.task_id,
                        subtask_id=self.subtask_id,
                        error=str(e),
                    ),
                )
            )
            raise

    async def rerun(self) -> None:
        await self.event_stream.publish(
            Event(
                type=EventType.SUBTASK_RERUN,
                data=EventData(task_id=self.task.task_id, subtask_id=self.subtask_id),
            )
        )
        await self.run()

    async def _run_pure_agent(self) -> None:
        agent = Agent(self)
        await agent.run()

    async def _run_pure_function(self) -> None:
        # Run pure function implementation
        pass

    async def _run_human_agent(self) -> None:
        chat = Chat()
        # await chat.start()
        await chat.run()


class Chat:
    def __init__(
        self, path: Path, task_id: str, subtask_id: str, event_stream: EventStream
    ):
        self.path = path
        self.task_id = task_id
        self.subtask_id = subtask_id
        self.event_stream = event_stream

        self.message_history = []

        # Setup agent here
        self.agent = Agent()

        # Register event handlers
        self._register_handlers()

    def _register_handlers(self):
        self.event_stream.subscribe(
            EventType.CHAT_MESSAGE_RECEIVED, self._on_chat_message_received
        )

    async def start(self) -> None:
        await self.event_stream.publish(
            Event(
                type=EventType.CHAT_START,
                data=EventData(
                    task_id=self.subtask.task.task_id,
                    subtask_id=self.subtask.subtask_id,
                ),
            )
        )

    # async def _get_next_message(self) -> Optional[ChatMessage]:
    #     # Implementation to get next message from chat files
    #     pass

    # async def messages(self) -> AsyncGenerator[ChatMessage, None]:
    #     while True:
    #         msg = await self._get_next_message()
    #         if not msg:
    #             break
    #         await self.event_manager.publish(
    #             Event(
    #                 type=EventType.CHAT_MESSAGE,
    #                 data=EventData(
    #                     task_id=self.subtask.task.task_id,
    #                     subtask_id=self.subtask.subtask_id,
    #                     message=msg,
    #                 ),
    #             )
    #         )
    #         yield msg

    async def complete(self) -> None:
        await self.event_stream.publish(
            Event(
                type=EventType.CHAT_COMPLETE,
                data=EventData(
                    task_id=self.task_id,
                    subtask_id=self.subtask_id,
                ),
            )
        )

    async def _on_chat_message_received(self, data: EventData[ChatMessage]):
        message = data.message

        # Save the message
        # ...

        if message.role == 'user':
            await self.agent.run(message, self.message_history)
        elif message.role == 'agent':
            # No need to process
            pass
        else:
            raise ValueError(f'Unknown message role: {message.role}')


# We use pydantic-ai's Agent class instead. No need to create our own.

# class Agent:
#     def __init__(self, subtask: Subtask):
#         self.subtask = subtask
#         self.event_manager = subtask.event_manager
#     async def run(self) -> None:
#         await self.event_manager.publish(
#             Event(
#                 type=EventType.AGENT_RUN,
#                 data=EventData(
#                     task_id=self.subtask.task.task_id,
#                     subtask_id=self.subtask.subtask_id,
#                 ),
#             )
#         )

#         try:
#             # Run agent workflow implementation
#             pass

#             await self.event_manager.publish(
#                 Event(
#                     type=EventType.AGENT_COMPLETE,
#                     data=EventData(
#                         task_id=self.subtask.task.task_id,
#                         subtask_id=self.subtask.subtask_id,
#                     ),
#                 )
#             )

#         except Exception as e:
#             await self.event_manager.publish(
#                 Event(
#                     type=EventType.AGENT_ERROR,
#                     data=EventData(
#                         task_id=self.subtask.task.task_id,
#                         subtask_id=self.subtask.subtask_id,
#                         error=str(e),
#                     ),
#                 )
#             )
#             raise

#     async def setup(self) -> None:
#         # Setup agent for human interaction
#         pass

#     async def handle_message(self, message: ChatMessage) -> None:
#         # Handle chat message implementation
#         pass


class TaskManager:
    """Manages all running tasks, subtasks"""

    def __init__(self, event_stream: EventStream):
        self.event_stream = event_stream
        self.active_tasks: dict[str, Task] = {}
        self._register_handlers()

    def _register_handlers(self):
        # Task lifecycle
        self.event_stream.subscribe(EventType.TASK_CREATE, self._on_task_create)
        self.event_stream.subscribe(EventType.TASK_COMPLETE, self._on_task_complete)
        self.event_stream.subscribe(EventType.TASK_ERROR, self._on_task_error)

        # Subtask coordination
        self.event_stream.subscribe(
            EventType.SUBTASK_COMPLETE, self._on_subtask_complete
        )
        self.event_stream.subscribe(EventType.SUBTASK_ERROR, self._on_subtask_error)

    async def _on_task_create(self, data: TaskCreateEventData):
        task_id = data.task_id
        task_path = Path(data.task_path)

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

    def _get_chat(self, chat_id: str):
        if chat_id in self.active_chats:
            return self.active_chats[chat_id]
        else:
            raise ValueError(f'Chat with id {chat_id} not found')

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

    async def _on_chat_message_received(self, data: EventData[ChatMessage]):
        # message = data['message']
        # chat_id = data['chat_id']
        message = data.message
        chat_id = data.chat_id

        chat = self._get_chat(chat_id)

        if message.role == 'user':
            # self.agent.response(message)
            pass
        elif message.role == 'agent':
            chat.agent.response(message)
        else:
            raise


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


# Example Usage
async def main():
    # Initialize event manager
    event_manager = EventManager()

    # Add logging handler
    def log_event(event: Event):
        print(f'{event.timestamp}: {event.type} - {event.data}')

    for event_type in EventType:
        event_manager.subscribe(event_type, log_event)

    # Create and run task
    task = await event_manager.create_task('task-1', Path('./tasks/task-1'))
    await task.run()


if __name__ == '__main__':
    asyncio.run(main())
