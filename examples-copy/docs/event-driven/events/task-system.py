from __future__ import annotations

import asyncio
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Union, Callable
from pydantic import BaseModel, Field

# Event Types
class EventType(str, Enum):
    # Task Events
    TASK_CREATE = "task.create"
    TASK_RUN = "task.run"
    TASK_COMPLETE = "task.complete"
    TASK_ERROR = "task.error"

    # Subtask Events
    SUBTASK_CREATE = "subtask.create"
    SUBTASK_RUN = "subtask.run"
    SUBTASK_COMPLETE = "subtask.complete"
    SUBTASK_ERROR = "subtask.error"
    SUBTASK_RERUN = "subtask.rerun"

    # Chat Events
    CHAT_START = "chat.start"
    CHAT_MESSAGE = "chat.message"
    CHAT_COMPLETE = "chat.complete"
    CHAT_ERROR = "chat.error"

    # Function Events
    FUNCTION_RUN = "function.run"
    FUNCTION_COMPLETE = "function.complete"
    FUNCTION_ERROR = "function.error"

    # Agent Events
    AGENT_RUN = "agent.run"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"

# Models
class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

class SubtaskStatus(str, Enum):
    PENDING = "pending"
    WAITING_EXTERNAL = "waiting_external"
    WAITING_USER = "waiting_user"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"

class SubtaskType(str, Enum):
    PURE_AGENT = "pure_agent"
    PURE_FUNCTION = "pure_function"
    HUMAN_AGENT = "human_agent"

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

class EventData(BaseModel):
    task_id: str
    subtask_id: Optional[str] = None
    error: Optional[str] = None
    message: Optional[ChatMessage] = None
    status: Optional[Union[TaskStatus, SubtaskStatus]] = None

class Event(BaseModel):
    type: EventType
    data: EventData
    timestamp: datetime = Field(default_factory=datetime.now)

# Event Manager
class EventManager:
    def __init__(self):
        self.handlers: Dict[EventType, List[Callable[[Event], None]]] = {
            event_type: [] for event_type in EventType
        }
        self.tasks: Dict[str, Task] = {}
        self.chats: Dict[str, Chat] = {}

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        self.handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable[[Event], None]) -> None:
        if handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        for handler in self.handlers[event.type]:
            try:
                handler(event)
            except Exception as e:
                print(f"Error in event handler: {e}")

    async def create_task(self, task_id: str, path: Path) -> Task:
        task = Task(task_id=task_id, path=path, event_manager=self)
        await task.init()
        self.tasks[task_id] = task
        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

# Task System
class Task:
    def __init__(self, task_id: str, path: Path, event_manager: EventManager):
        self.task_id = task_id
        self.path = path
        self.event_manager = event_manager
        self.lock_file = path / "task.lock"
        self.subtasks: Dict[str, Subtask] = {}

    async def init(self) -> None:
        if not self.path.exists():
            self.path.mkdir(parents=True)
            
        if not self.lock_file.exists():
            # Initialize with step0
            step0_folder = self.path / "step0"
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
                event_manager=self.event_manager,
            )

    async def run(self) -> None:
        await self.event_manager.publish(
            Event(
                type=EventType.TASK_RUN,
                data=EventData(task_id=self.task_id)
            )
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

            await self.event_manager.publish(
                Event(
                    type=EventType.TASK_COMPLETE,
                    data=EventData(task_id=self.task_id)
                )
            )

        except Exception as e:
            await self.event_manager.publish(
                Event(
                    type=EventType.TASK_ERROR,
                    data=EventData(task_id=self.task_id, error=str(e))
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
        event_manager: EventManager,
    ):
        self.subtask_id = subtask_id
        self.task = task
        self.path = path
        self.info = info
        self.event_manager = event_manager

    async def run(self) -> None:
        await self.event_manager.publish(
            Event(
                type=EventType.SUBTASK_RUN,
                data=EventData(
                    task_id=self.task.task_id,
                    subtask_id=self.subtask_id
                )
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

            await self.event_manager.publish(
                Event(
                    type=EventType.SUBTASK_COMPLETE,
                    data=EventData(
                        task_id=self.task.task_id,
                        subtask_id=self.subtask_id
                    )
                )
            )

        except Exception as e:
            await self.event_manager.publish(
                Event(
                    type=EventType.SUBTASK_ERROR,
                    data=EventData(
                        task_id=self.task.task_id,
                        subtask_id=self.subtask_id,
                        error=str(e)
                    )
                )
            )
            raise

    async def rerun(self) -> None:
        await self.event_manager.publish(
            Event(
                type=EventType.SUBTASK_RERUN,
                data=EventData(
                    task_id=self.task.task_id,
                    subtask_id=self.subtask_id
                )
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
        agent = Agent(self)
        chat = Chat(self)

        await agent.setup()
        await chat.start()

        async for msg in chat.messages():
            await agent.handle_message(msg)

        await chat.complete()

class Chat:
    def __init__(self, subtask: Subtask):
        self.subtask = subtask
        self.path = subtask.path
        self.event_manager = subtask.event_manager

    async def start(self) -> None:
        await self.event_manager.publish(
            Event(
                type=EventType.CHAT_START,
                data=EventData(
                    task_id=self.subtask.task.task_id,
                    subtask_id=self.subtask.subtask_id
                )
            )
        )

    async def messages(self) -> AsyncGenerator[ChatMessage, None]:
        while True:
            msg = await self._get_next_message()
            if not msg:
                break

            await self.event_manager.publish(
                Event(
                    type=EventType.CHAT_MESSAGE,
                    data=EventData(
                        task_id=self.subtask.task.task_id,
                        subtask_id=self.subtask.subtask_id,
                        message=msg
                    )
                )
            )

            yield msg

    async def complete(self) -> None:
        await self.event_manager.publish(
            Event(
                type=EventType.CHAT_COMPLETE,
                data=EventData(
                    task_id=self.subtask.task.task_id,
                    subtask_id=self.subtask.subtask_id
                )
            )
        )

    async def _get_next_message(self) -> Optional[ChatMessage]:
        # Implementation to get next message from chat files
        pass

class Agent:
    def __init__(self, subtask: Subtask):
        self.subtask = subtask
        self.event_manager = subtask.event_manager

    async def run(self) -> None:
        await self.event_manager.publish(
            Event(
                type=EventType.AGENT_RUN,
                data=EventData(
                    task_id=self.subtask.task.task_id,
                    subtask_id=self.subtask.subtask_id
                )
            )
        )

        try:
            # Run agent workflow implementation
            pass

            await self.event_manager.publish(
                Event(
                    type=EventType.AGENT_COMPLETE,
                    data=EventData(
                        task_id=self.subtask.task.task_id,
                        subtask_id=self.subtask.subtask_id
                    )
                )
            )

        except Exception as e:
            await self.event_manager.publish(
                Event(
                    type=EventType.AGENT_ERROR,
                    data=EventData(
                        task_id=self.subtask.task.task_id,
                        subtask_id=self.subtask.subtask_id,
                        error=str(e)
                    )
                )
            )
            raise

    async def setup(self) -> None:
        # Setup agent for human interaction
        pass

    async def handle_message(self, message: ChatMessage) -> None:
        # Handle chat message implementation
        pass

# Example Usage
async def main():
    # Initialize event manager
    event_manager = EventManager()

    # Add logging handler
    def log_event(event: Event):
        print(f"{event.timestamp}: {event.type} - {event.data}")

    for event_type in EventType:
        event_manager.subscribe(event_type, log_event)

    # Create and run task
    task = await event_manager.create_task("task-1", Path("./tasks/task-1"))
    await task.run()

if __name__ == "__main__":
    asyncio.run(main())
