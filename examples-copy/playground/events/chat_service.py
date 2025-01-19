import asyncio
from datetime import datetime
from typing import Optional
from uuid import uuid4

from .event_bus import IEventBus
from .repositories import ChatRepository
from .type_defs import (
    Chat,
    ChatCreatedEvent,
    EventType,
    Message,
    MessageSavedToChatFileEvent,
    Role,
    StartNewChatCommand,
    UserApproveWorkEvent,
)
from .workspace_file_manager import WorkspaceFileManager


class ChatService:
    def __init__(
        self,
        event_bus: IEventBus,
        chat_repo: ChatRepository,
        workspace_manager: WorkspaceFileManager,
    ):
        self._workspace = 'tasks'
        self._event_bus = event_bus
        self._chat_repo = chat_repo
        self._workspace_manager = workspace_manager

        # Subscribe to commands
        self._event_bus.subscribe_async(
            EventType.START_NEW_CHAT_COMMAND, self._handle_start_new_chat_command
        )
        self._event_bus.subscribe_async(
            EventType.USER_SUBMIT_MESSAGE_COMMAND,
            self._handle_user_submit_message_command,
        )
        self._event_bus.subscribe_async(
            EventType.SUBMIT_INITIAL_PROMPT_COMMAND,
            self._handle_submit_initial_prompt_command,
        )

    async def _handle_start_new_chat_command(
        self, command: StartNewChatCommand
    ) -> None:
        chat_id = self._generate_chat_id()

        # Initialize chat object
        chat = Chat(
            id=chat_id,
            task_id=command.task_id,
            subtask_id=command.subtask_id,
            messages=[],
            status='active',
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=command.metadata,
        )
        self._chat_repo.save(chat)

        # Create chat file using workspace manager
        await self._workspace_manager.create_chat_file(
            command.task_id, command.subtask_id, chat_id
        )

        await self._event_bus.publish(
            ChatCreatedEvent(
                task_id=command.task_id,
                subtask_id=command.subtask_id,
                chat_id=chat_id,
                timestamp=datetime.now(),
                correlation_id=command.correlation_id,
            )
        )

        # Initialize first prompt based on subtask configuration
        prompt = await self._generate_initial_prompt(
            command.task_id, command.subtask_id
        )
        message = Message(
            id=self._generate_message_id(),
            role=Role.USER,
            content=prompt,
            timestamp=datetime.now(),
            metadata={
                'task_id': chat.task_id,
                'subtask_id': chat.subtask_id,
                'is_prompt': True,
            },
        )

        asyncio.create_task(
            self._on_message_received(chat, message, command.correlation_id)
        )

    async def _on_message_received(
        self, chat: Chat, message: Message, correlation_id: Optional[str]
    ) -> None:
        # Add message to chat
        chat.messages.append(message)

        # Save message to file using workspace manager
        file_path = await self._workspace_manager.save_message_to_chat_file(
            chat.id, message
        )

        # Emit event for message saved
        await self._event_bus.publish(
            MessageSavedToChatFileEvent(
                chat_id=chat.id,
                message_id=message.id,
                file_path=file_path,
                timestamp=datetime.now(),
                correlation_id=correlation_id,
            )
        )

        # Process user message if needed
        if message.role == Role.USER:
            if 'APPROVE' in message.content:
                await self._event_bus.publish(
                    UserApproveWorkEvent(
                        chat_id=chat.id,
                        timestamp=datetime.now(),
                        correlation_id=correlation_id,
                    )
                )
                return

            # Generate and process agent response
            response = await self._generate_agent_response(chat, message)
            await self._on_message_received(chat, response, correlation_id)

    def _generate_chat_id(self) -> str:
        return f'chat_{int(datetime.now().timestamp())}_{uuid4().hex[:8]}'

    def _generate_message_id(self) -> str:
        return f'msg_{int(datetime.now().timestamp())}_{uuid4().hex[:8]}'
