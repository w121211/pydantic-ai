import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# Data Models
class TaskStatus(str, Enum):
    CREATED = 'created'
    INITIALIZED = 'initialized'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'


class SubtaskStatus(str, Enum):
    CREATED = 'created'
    INITIALIZED = 'initialized'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'


class ChatStatus(str, Enum):
    CREATED = 'created'
    ACTIVE = 'active'
    CLOSED = 'closed'


# Base Models
class Task(BaseModel):
    id: str
    status: TaskStatus
    created_at: datetime = Field(default_factory=datetime.now)
    folder_path: Path


class Subtask(BaseModel):
    id: str
    task_id: str
    status: SubtaskStatus
    created_at: datetime = Field(default_factory=datetime.now)
    folder_path: Path


class Chat(BaseModel):
    id: str
    subtask_id: str
    status: ChatStatus
    created_at: datetime = Field(default_factory=datetime.now)
    file_path: Path


# Event Types
class EventType(str, Enum):
    # Task Events
    TASK_CREATED = 'task_created'
    TASK_FOLDER_CREATED = 'task_folder_created'
    TASK_INITIALIZED = 'task_initialized'

    # Subtask Events
    SUBTASK_INITIALIZED = 'subtask_initialized'
    SUBTASK_FOLDER_CREATED = 'subtask_folder_created'
    SUBTASK_COMPLETED = 'subtask_completed'

    # Chat Events
    CHAT_CREATED = 'chat_created'
    MESSAGE_RECEIVED = 'message_received'
    MESSAGE_SAVED = 'message_saved'
    CHAT_UPDATED = 'chat_updated'


# Event Data Models
class BaseEventData(BaseModel):
    event_type: str


class TaskEventData(BaseEventData):
    event_type: Literal['task_created', 'task_folder_created', 'task_initialized']
    task_id: str
    status: Optional[TaskStatus] = None
    folder_path: Optional[Path] = None


class SubtaskEventData(BaseEventData):
    event_type: Literal[
        'subtask_initialized', 'subtask_folder_created', 'subtask_completed'
    ]
    subtask_id: str
    task_id: str
    status: Optional[SubtaskStatus] = None
    folder_path: Optional[Path] = None


class ChatEventData(BaseEventData):
    event_type: Literal[
        'chat_created', 'message_received', 'message_saved', 'chat_updated'
    ]
    chat_id: str
    subtask_id: str
    message_content: Optional[str] = None
    file_path: Optional[Path] = None


# Event Model
class Event(BaseModel):
    type: EventType
    data: Union[TaskEventData, SubtaskEventData, ChatEventData]
    timestamp: datetime = Field(default_factory=datetime.now)

    # @field_validator('data')
    # def validate_event_data(cls, v):
    #     if isinstance(v, BaseEventData) and not isinstance(v, (TaskEventData, SubtaskEventData, ChatEventData)):
    #         raise ValueError("Cannot use BaseEventData directly")
    #     return v

    @field_validator('data')
    def validate_event_data(cls, v: BaseEventData) -> BaseEventData:
        if type(v) == BaseEventData:
            raise ValueError('Cannot use BaseEventData directly')
        return v


# Event Handler Interface
class EventHandler(ABC):
    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        pass


# Event Bus Interface
class EventBus(ABC):
    @abstractmethod
    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        pass

    @abstractmethod
    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        pass

    @abstractmethod
    async def publish(self, event: Event) -> None:
        pass


# Simple Event Bus Implementation
class SimpleEventBus(EventBus):
    def __init__(self):
        self.handlers: Dict[EventType, List[EventHandler]] = {}

    def subscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: EventHandler) -> None:
        if event_type in self.handlers:
            self.handlers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        if event.type in self.handlers:
            await asyncio.gather(
                *[handler.handle_event(event) for handler in self.handlers[event.type]]
            )


# Service Examples
class TaskService(EventHandler):
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.tasks: Dict[str, Task] = {}

    async def handle_event(self, event: Event) -> None:
        if event.type == EventType.TASK_CREATED:
            await self.handle_task_created(event.data)
        # Add other event handlers...

    async def handle_task_created(self, data: TaskEventData) -> None:
        task = Task(
            id=data.task_id, status=TaskStatus.CREATED, folder_path=data.folder_path
        )
        self.tasks[task.id] = task

        # Publish folder creation event
        await self.event_bus.publish(
            Event(
                type=EventType.TASK_FOLDER_CREATED,
                data=TaskEventData(
                    event_type='task_folder_created',
                    task_id=task.id,
                    folder_path=task.folder_path,
                ),
            )
        )


class SubtaskService(EventHandler):
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.subtasks: Dict[str, Subtask] = {}

    async def handle_event(self, event: Event) -> None:
        if event.type == EventType.SUBTASK_INITIALIZED:
            await self.handle_subtask_initialized(event.data)
        # Add other event handlers...

    async def handle_subtask_initialized(self, data: SubtaskEventData) -> None:
        subtask = Subtask(
            id=data.subtask_id,
            task_id=data.task_id,
            status=SubtaskStatus.INITIALIZED,
            folder_path=data.folder_path,
        )
        self.subtasks[subtask.id] = subtask


# Usage Example
async def main():
    # Initialize event bus
    event_bus = SimpleEventBus()

    # Initialize services
    task_service = TaskService(event_bus)
    subtask_service = SubtaskService(event_bus)

    # Subscribe services to events
    event_bus.subscribe(EventType.TASK_CREATED, task_service)
    event_bus.subscribe(EventType.SUBTASK_INITIALIZED, subtask_service)

    # Create a task
    task_event = Event(
        type=EventType.TASK_CREATED,
        data=TaskEventData(
            event_type='task_created',
            task_id='task-1',
            folder_path=Path('/tasks/task-1'),
        ),
    )

    # Publish event
    await event_bus.publish(task_event)


if __name__ == '__main__':
    asyncio.run(main())
