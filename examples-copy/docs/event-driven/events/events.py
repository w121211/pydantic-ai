from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    TypedDict,
)


# Event Types and Definitions
class EventType(str, Enum):
    # Task Events
    TASK_CREATE = 'task.create'
    TASK_RUN = 'task.run'
    TASK_COMPLETE = 'task.complete'
    TASK_ERROR = 'task.error'

    # Subtask Events
    SUBTASK_CREATE = 'subtask.create'
    SUBTASK_RUN = 'subtask.run'
    SUBTASK_COMPLETE = 'subtask.complete'
    SUBTASK_ERROR = 'subtask.error'
    SUBTASK_RERUN = 'subtask.rerun'

    # Chat Events
    CHAT_START = 'chat.start'
    CHAT_MESSAGE = 'chat.message'
    CHAT_COMPLETE = 'chat.complete'
    CHAT_ERROR = 'chat.error'

    # Function Events
    FUNCTION_RUN = 'function.run'
    FUNCTION_COMPLETE = 'function.complete'
    FUNCTION_ERROR = 'function.error'

    # Agent Events
    AGENT_RUN = 'agent.run'
    AGENT_COMPLETE = 'agent.complete'
    AGENT_ERROR = 'agent.error'


@dataclass
class Event:
    type: EventType
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


# Event Stream Manager
class EventStream:
    def __init__(self):
        self.subscribers: List[Callable[[Event], None]] = []

    def subscribe(self, callback: Callable[[Event], None]):
        self.subscribers.append(callback)

    def publish(self, event: Event):
        for subscriber in self.subscribers:
            subscriber(event)


# Task System Models
class TaskStatus(str, Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    ERROR = 'error'


class SubtaskStatus(str, Enum):
    PENDING = 'pending'
    WAITING_EXTERNAL = 'waiting_external'
    WAITING_USER = 'waiting_user'
    RUNNING = 'running'
    COMPLETED = 'completed'
    ERROR = 'error'


class SubtaskType(str, Enum):
    PURE_AGENT = 'pure_agent'
    PURE_FUNCTION = 'pure_function'
    HUMAN_AGENT = 'human_agent'


class TaskLock(TypedDict):
    task_id: str
    status: TaskStatus
    current_subtask: Optional[str]
    subtasks: Dict[str, SubtaskInfo]


class SubtaskInfo(TypedDict):
    type: SubtaskType
    status: SubtaskStatus
    prompt: str


class Task:
    def __init__(self, task_id: str, path: Path, event_stream: EventStream):
        self.task_id = task_id
        self.path = path
        self.event_stream = event_stream
        self.lock_file = path / 'task.lock'

    async def init(self):
        """Initialize task from step 0 or existing lock file"""
        if not self.lock_file.exists():
            step0_folder = self.path / 'step0'
            if step0_folder.exists():
                # Generate task.json from step0 results
                pass
            else:
                # Run step 0
                await self._run_step0()

    async def run(self):
        """Run task from current state"""
        self.event_stream.publish(Event(EventType.TASK_RUN, {'task_id': self.task_id}))

        try:
            lock = self._load_lock()
            current = lock['current_subtask']

            if current:
                # Continue from current subtask
                subtask = self._get_subtask(current)
                await subtask.run()
            else:
                # Start from beginning
                for subtask_id in lock['subtasks']:
                    subtask = self._get_subtask(subtask_id)
                    await subtask.run()

            self.event_stream.publish(
                Event(EventType.TASK_COMPLETE, {'task_id': self.task_id})
            )

        except Exception as e:
            self.event_stream.publish(
                Event(EventType.TASK_ERROR, {'task_id': self.task_id, 'error': str(e)})
            )
            raise

    def _load_lock(self) -> TaskLock:
        with open(self.lock_file) as f:
            return json.load(f)

    def _get_subtask(self, subtask_id: str) -> Subtask:
        lock = self._load_lock()
        info = lock['subtasks'][subtask_id]
        return Subtask(
            subtask_id=subtask_id,
            task=self,
            path=self.path / subtask_id,
            info=info,
            event_stream=self.event_stream,
        )


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

    async def run(self):
        """Run subtask based on type"""
        self.event_stream.publish(
            Event(
                EventType.SUBTASK_RUN,
                {'task_id': self.task.task_id, 'subtask_id': self.subtask_id},
            )
        )

        try:
            if not self.path.exists():
                os.makedirs(self.path)

            match self.info['type']:
                case SubtaskType.PURE_AGENT:
                    await self._run_pure_agent()
                case SubtaskType.PURE_FUNCTION:
                    await self._run_pure_function()
                case SubtaskType.HUMAN_AGENT:
                    await self._run_human_agent()

            self.event_stream.publish(
                Event(
                    EventType.SUBTASK_COMPLETE,
                    {'task_id': self.task.task_id, 'subtask_id': self.subtask_id},
                )
            )

        except Exception as e:
            self.event_stream.publish(
                Event(
                    EventType.SUBTASK_ERROR,
                    {
                        'task_id': self.task.task_id,
                        'subtask_id': self.subtask_id,
                        'error': str(e),
                    },
                )
            )
            raise

    async def rerun(self):
        """Rerun this subtask"""
        self.event_stream.publish(
            Event(
                EventType.SUBTASK_RERUN,
                {'task_id': self.task.task_id, 'subtask_id': self.subtask_id},
            )
        )
        await self.run()

    async def _run_pure_agent(self):
        agent = Agent(self)
        await agent.run()

    async def _run_pure_function(self):
        # Run pure function and emit events
        pass

    async def _run_human_agent(self):
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
        self.event_stream = subtask.event_stream

    async def start(self):
        """Start a new chat"""
        self.event_stream.publish(
            Event(
                EventType.CHAT_START,
                {
                    'task_id': self.subtask.task.task_id,
                    'subtask_id': self.subtask.subtask_id,
                },
            )
        )

    async def messages(self) -> AsyncGenerator[dict, None]:
        """Stream messages from chat"""
        while True:
            msg = await self._get_next_message()
            if not msg:
                break

            self.event_stream.publish(
                Event(
                    EventType.CHAT_MESSAGE,
                    {
                        'task_id': self.subtask.task.task_id,
                        'subtask_id': self.subtask.subtask_id,
                        'message': msg,
                    },
                )
            )

            yield msg

    async def complete(self):
        """Complete the chat"""
        self.event_stream.publish(
            Event(
                EventType.CHAT_COMPLETE,
                {
                    'task_id': self.subtask.task.task_id,
                    'subtask_id': self.subtask.subtask_id,
                },
            )
        )

    async def _get_next_message(self) -> Optional[dict]:
        # Get next message from chat files
        pass


class Agent:
    def __init__(self, subtask: Subtask):
        self.subtask = subtask
        self.event_stream = subtask.event_stream

    async def run(self):
        """Run pure agent workflow"""
        self.event_stream.publish(
            Event(
                EventType.AGENT_RUN,
                {
                    'task_id': self.subtask.task.task_id,
                    'subtask_id': self.subtask.subtask_id,
                },
            )
        )

        try:
            # Run agent workflow
            pass

            self.event_stream.publish(
                Event(
                    EventType.AGENT_COMPLETE,
                    {
                        'task_id': self.subtask.task.task_id,
                        'subtask_id': self.subtask.subtask_id,
                    },
                )
            )

        except Exception as e:
            self.event_stream.publish(
                Event(
                    EventType.AGENT_ERROR,
                    {
                        'task_id': self.subtask.task.task_id,
                        'subtask_id': self.subtask.subtask_id,
                        'error': str(e),
                    },
                )
            )
            raise

    async def setup(self):
        """Setup agent for human interaction"""
        pass

    async def handle_message(self, message: dict):
        """Handle a chat message"""
        pass


# Example Usage
async def main():
    # Setup event stream
    event_stream = EventStream()

    # Subscribe to events
    def log_event(event: Event):
        print(f'{event.timestamp}: {event.type} - {event.data}')

    event_stream.subscribe(log_event)

    # Create and run task
    task = Task('task-1', Path('./tasks/task-1'), event_stream)
    await task.init()
    await task.run()


if __name__ == '__main__':
    asyncio.run(main())
