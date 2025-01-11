from __future__ import annotations

import json
from datetime import datetime

import aiofiles
from pydantic import BaseModel


class MessageEvent(BaseModel):
    chat_id: str
    task_id: str
    subtask_id: str
    content: str
    timestamp: datetime


class HumanMessageEvent(MessageEvent):
    pass


class AgentMessageEvent(MessageEvent):
    pass


class ChatStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"


class Chat:
    async def send_human_message(self, content: str) -> None:
        pass

    async def on_receive_human_message(self, content: str) -> None:
        pass


class Chat:
    def __init__(self, chat_id: str, subtask: Subtask, event_manager: EventManager):
        self.chat_id = chat_id
        self.subtask = subtask
        self.event_manager = event_manager
        self.path = subtask.path / "chats" / chat_id
        self.status = ChatStatus.ACTIVE
        self.messages_file = self.path / "messages.jsonl"
        self.agent = Agent(subtask)

    async def init(self) -> None:
        """Initialize chat and subscribe to events"""
        if not self.path.exists():
            self.path.mkdir(parents=True)

        # Subscribe to message events
        self.event_manager.subscribe(EventType.HUMAN_MESSAGE, self.handle_human_message)
        self.event_manager.subscribe(EventType.AGENT_MESSAGE, self.handle_agent_message)

    async def start(self) -> None:
        """Start the chat session"""
        await self.init()

        await self.event_manager.publish(
            Event(
                type=EventType.CHAT_START,
                data=EventData(
                    chat_id=self.chat_id,
                    task_id=self.subtask.task.task_id,
                    subtask_id=self.subtask.subtask_id,
                ),
            )
        )

        # Send initial prompt from subtask
        initial_prompt = self.subtask.info.prompt
        if initial_prompt:
            await self._send_event(
                EventType.AGENT_MESSAGE,
                AgentMessageEvent(
                    chat_id=self.chat_id,
                    task_id=self.subtask.task.task_id,
                    subtask_id=self.subtask.subtask_id,
                    content=initial_prompt,
                    timestamp=datetime.now(),
                ),
            )

    async def send_human_message(self, content: str) -> None:
        """Send human message event"""
        if self.status != ChatStatus.ACTIVE:
            raise RuntimeError("Chat is not active")

        await self._send_event(
            EventType.HUMAN_MESSAGE,
            HumanMessageEvent(
                chat_id=self.chat_id,
                task_id=self.subtask.task.task_id,
                subtask_id=self.subtask.subtask_id,
                content=content,
                timestamp=datetime.now(),
            ),
        )

    async def send_agent_message(self, content: str) -> None:
        """Send agent message event"""
        if self.status != ChatStatus.ACTIVE:
            raise RuntimeError("Chat is not active")

        await self._send_event(
            EventType.AGENT_MESSAGE,
            AgentMessageEvent(
                chat_id=self.chat_id,
                task_id=self.subtask.task.task_id,
                subtask_id=self.subtask.subtask_id,
                content=content,
                timestamp=datetime.now(),
            ),
        )

    async def _send_event(
        self, event_type: EventType, message_data: MessageEvent
    ) -> None:
        """Helper method to send events"""
        await self.event_manager.publish(Event(type=event_type, data=message_data))

    async def handle_human_message(self, event: Event[HumanMessageEvent]) -> None:
        """Handle incoming human message event"""
        message_data = event.data

        # Only handle messages for this chat
        if message_data.chat_id != self.chat_id:
            return

        # Persist message
        await self._persist_message("human", message_data)

        # Get agent response
        response = await self.agent.handle_message(message_data.content)
        if response:
            await self.send_agent_message(response)

    async def handle_agent_message(self, event: Event[AgentMessageEvent]) -> None:
        """Handle incoming agent message event"""
        message_data = event.data

        # Only handle messages for this chat
        if message_data.chat_id != self.chat_id:
            return

        # Persist message
        await self._persist_message("agent", message_data)

    async def _persist_message(self, role: str, message_data: MessageEvent) -> None:
        """Persist message to file"""
        async with aiofiles.open(self.messages_file, mode="a") as f:
            await f.write(
                json.dumps(
                    {
                        "role": role,
                        "content": message_data.content,
                        "timestamp": message_data.timestamp.isoformat(),
                    }
                )
                + "\n"
            )

    async def complete(self) -> None:
        """Complete the chat session"""
        self.status = ChatStatus.COMPLETED

        # Unsubscribe from events
        self.event_manager.unsubscribe(
            EventType.HUMAN_MESSAGE, self.handle_human_message
        )
        self.event_manager.unsubscribe(
            EventType.AGENT_MESSAGE, self.handle_agent_message
        )

        # Publish complete event
        await self.event_manager.publish(
            Event(
                type=EventType.CHAT_COMPLETE,
                data=EventData(
                    chat_id=self.chat_id,
                    task_id=self.subtask.task.task_id,
                    subtask_id=self.subtask.subtask_id,
                ),
            )
        )

        # Notify subtask
        await self.subtask.on_chat_complete()


# Example usage:
async def create_chat(subtask: Subtask, event_manager: EventManager) -> Chat:
    chat = Chat(
        chat_id=f"chat_{datetime.now().timestamp()}",
        subtask=subtask,
        event_manager=event_manager,
    )
    await chat.start()
    return chat
