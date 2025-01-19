import asyncio
from datetime import datetime
from pathlib import Path

from .chat_service import ChatService
from .event_bus import EventBus
from .repositories import ChatRepository, TaskRepository
from .type_defs import (
    Chat,
    ChatMetadata,
    ChatStatus,
    Message,
    Role,
    StartNewChatCommand,
)
from .workspace_file_manager import WorkspaceFileManager


async def main():
    # Initialize dependencies
    event_bus = EventBus(max_workers=5)
    chat_repo = ChatRepository()
    task_repo = TaskRepository()
    workspace_manager = WorkspaceFileManager(workspace_path=Path('./workspace'))

    # Initialize ChatService
    chat_service = ChatService(
        event_bus=event_bus, chat_repo=chat_repo, workspace_manager=workspace_manager
    )

    # Example: Start a new chat
    task_id = 'task_001'
    subtask_id = 'validate_input'

    start_chat_command = StartNewChatCommand(
        task_id=task_id,
        subtask_id=subtask_id,
        timestamp=datetime.now(),
        metadata=ChatMetadata(
            title='Data Validation Chat', tags=['validation', 'initial-review']
        ),
    )

    # Start new chat (this will trigger chat creation and initial prompt)
    await event_bus.publish(start_chat_command)

    # Example: Submit a user message
    chat = Chat(
        id='chat_001',
        task_id=task_id,
        subtask_id=subtask_id,
        messages=[],
        status=ChatStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        metadata=None,
    )
    chat_repo.save(chat)

    # Create and submit a user message
    message = Message(
        id='msg_001',
        role=Role.USER,
        content='Please validate this input data',
        timestamp=datetime.now(),
        metadata={
            'task_id': task_id,
            'subtask_id': subtask_id,
        },
    )

    # Process the message
    await chat_service._on_message_received(chat, message, correlation_id='corr_001')

    # Example: Submit a message with approval
    approve_message = Message(
        id='msg_002',
        role=Role.USER,
        content='APPROVE',
        timestamp=datetime.now(),
        metadata={
            'task_id': task_id,
            'subtask_id': subtask_id,
        },
    )

    # Process the approval message
    await chat_service._on_message_received(
        chat, approve_message, correlation_id='corr_002'
    )


if __name__ == '__main__':
    # Run the example
    asyncio.run(main())
