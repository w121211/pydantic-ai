from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# Enums
class TaskStatus(str, Enum):
    CREATED = 'CREATED'
    INITIALIZED = 'INITIALIZED'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'


class SubtaskStatus(str, Enum):
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'


class ChatStatus(str, Enum):
    ACTIVE = 'active'
    CLOSED = 'closed'


class Role(str, Enum):
    ASSISTANT = '@assistant'
    USER = '@user'
    FUNCTION_EXECUTOR = '@function_executor'


class EventType(str, Enum):
    # Task Commands
    CREATE_TASK_COMMAND = 'CREATE_TASK_COMMAND'
    START_TASK_COMMAND = 'START_TASK_COMMAND'

    # Task Events
    TASK_CREATED_EVENT = 'TASK_CREATED_EVENT'
    TASK_FOLDER_CREATED_EVENT = 'TASK_FOLDER_CREATED_EVENT'
    TASK_INITIALIZED_EVENT = 'TASK_INITIALIZED_EVENT'
    TASK_LOADED_EVENT = 'TASK_LOADED_EVENT'

    # Subtask Commands
    START_SUBTASK_COMMAND = 'START_SUBTASK_COMMAND'
    COMPLETE_SUBTASK_COMMAND = 'COMPLETE_SUBTASK_COMMAND'

    # Subtask Events
    SUBTASK_STARTED_EVENT = 'SUBTASK_STARTED_EVENT'
    SUBTASK_COMPLETED_EVENT = 'SUBTASK_COMPLETED_EVENT'
    SUBTASK_UPDATED_EVENT = 'SUBTASK_UPDATED_EVENT'
    NEXT_SUBTASK_TRIGGERED_EVENT = 'NEXT_SUBTASK_TRIGGERED_EVENT'

    # Chat Commands
    START_NEW_CHAT_COMMAND = 'START_NEW_CHAT_COMMAND'
    SUBMIT_INITIAL_PROMPT_COMMAND = 'SUBMIT_INITIAL_PROMPT_COMMAND'
    USER_SUBMIT_MESSAGE_COMMAND = 'USER_SUBMIT_MESSAGE_COMMAND'

    # Chat Events
    CHAT_CREATED_EVENT = 'CHAT_CREATED_EVENT'
    CHAT_FILE_CREATED_EVENT = 'CHAT_FILE_CREATED_EVENT'
    CHAT_UPDATED_EVENT = 'CHAT_UPDATED_EVENT'
    AGENT_PROCESSED_MESSAGE_EVENT = 'AGENT_PROCESSED_MESSAGE_EVENT'
    AGENT_RESPONSE_GENERATED_EVENT = 'AGENT_RESPONSE_GENERATED_EVENT'
    MESSAGE_RECEIVED_EVENT = 'MESSAGE_RECEIVED_EVENT'
    MESSAGE_SAVED_TO_CHAT_FILE_EVENT = 'MESSAGE_SAVED_TO_CHAT_FILE_EVENT'
    USER_APPROVE_WORK_EVENT = 'USER_APPROVE_WORK_EVENT'


# Base Models
class TeamConfig(BaseModel):
    agent: Role
    human: Optional[Role] = None


class Subtask(BaseModel):
    id: str
    task_id: str
    seq_number: int = Field(description='Step 1, 2, 3, etc for ordering')
    title: str = Field(description='Short, concise description for humans')
    status: SubtaskStatus
    description: str = Field(description='Detailed description')
    team: TeamConfig
    input_type: str = Field(description='Only string for now')
    output_type: str = Field(description='Only string for now')


class Task(BaseModel):
    id: str
    seq_number: int
    title: str
    status: TaskStatus
    current_subtask_id: Optional[str] = None
    subtasks: List[Subtask]
    folder_path: str
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class MessageMetadata(BaseModel):
    subtask_id: Optional[str] = None
    task_id: Optional[str] = None
    function_calls: Optional[List[Dict[str, Any]]] = None
    is_prompt: Optional[bool] = None


class Message(BaseModel):
    id: str
    role: Role
    content: str
    timestamp: datetime
    metadata: Optional[MessageMetadata] = None


class ChatMetadata(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None


class Chat(BaseModel):
    id: str
    task_id: str
    subtask_id: str
    messages: List[Message]
    status: ChatStatus
    created_at: datetime
    updated_at: datetime
    metadata: Optional[ChatMetadata] = None


# Base Event
class BaseEvent(BaseModel):
    type: EventType
    timestamp: datetime
    correlation_id: Optional[str] = None

    class Config:
        allow_population_by_field_name = True


# Task Events
class CreateTaskCommand(BaseEvent):
    type: EventType = EventType.CREATE_TASK_COMMAND
    task_name: str
    task_config: Dict[str, Any]


class StartTaskCommand(BaseEvent):
    type: EventType = EventType.START_TASK_COMMAND
    task_id: str


class TaskCreatedEvent(BaseEvent):
    type: EventType = EventType.TASK_CREATED_EVENT
    task_id: str
    task_name: str
    config: Dict[str, Any]


class TaskFolderCreatedEvent(BaseEvent):
    type: EventType = EventType.TASK_FOLDER_CREATED_EVENT
    task_id: str
    folder_path: str


class TaskInitializedEvent(BaseEvent):
    type: EventType = EventType.TASK_INITIALIZED_EVENT
    task_id: str
    initial_state: Dict[str, Any]


class TaskLoadedEvent(BaseEvent):
    type: EventType = EventType.TASK_LOADED_EVENT
    task_id: str
    task_state: Task


# Subtask Events
class StartSubtaskCommand(BaseEvent):
    type: EventType = EventType.START_SUBTASK_COMMAND
    task_id: str
    subtask_id: str


class CompleteSubtaskCommand(BaseEvent):
    type: EventType = EventType.COMPLETE_SUBTASK_COMMAND
    task_id: str
    subtask_id: str
    output: str  # For simplicity, we are using string output
    requires_approval: bool


class SubtaskStartedEvent(BaseEvent):
    type: EventType = EventType.SUBTASK_STARTED_EVENT
    task_id: str
    subtask_id: str
    input: Optional[Any] = None


class SubtaskCompletedEvent(BaseEvent):
    type: EventType = EventType.SUBTASK_COMPLETED_EVENT
    task_id: str
    subtask_id: str


class SubtaskUpdatedEvent(BaseEvent):
    type: EventType = EventType.SUBTASK_UPDATED_EVENT
    task_id: str
    subtask_id: str
    status: SubtaskStatus


class NextSubtaskTriggeredEvent(BaseEvent):
    type: EventType = EventType.NEXT_SUBTASK_TRIGGERED_EVENT
    task_id: str
    current_subtask_id: str


# Chat Events
class StartNewChatCommand(BaseEvent):
    type: EventType = EventType.START_NEW_CHAT_COMMAND
    task_id: str
    subtask_id: str
    metadata: Optional[ChatMetadata] = None


class SubmitInitialPromptCommand(BaseEvent):
    type: EventType = EventType.SUBMIT_INITIAL_PROMPT_COMMAND
    chat_id: str
    prompt: str


class UserSubmitMessageCommand(BaseEvent):
    type: EventType = EventType.USER_SUBMIT_MESSAGE_COMMAND
    chat_id: str
    content: str


class ChatCreatedEvent(BaseEvent):
    type: EventType = EventType.CHAT_CREATED_EVENT
    task_id: str
    subtask_id: str
    chat_id: str


class ChatFileCreatedEvent(BaseEvent):
    type: EventType = EventType.CHAT_FILE_CREATED_EVENT
    task_id: str
    subtask_id: str
    chat_id: str
    file_path: str


class ChatUpdatedEvent(BaseEvent):
    type: EventType = EventType.CHAT_UPDATED_EVENT
    chat_id: str
    last_message_id: str


class AgentProcessedMessageEvent(BaseEvent):
    type: EventType = EventType.AGENT_PROCESSED_MESSAGE_EVENT
    chat_id: str
    message_id: str


class AgentResponseGeneratedEvent(BaseEvent):
    type: EventType = EventType.AGENT_RESPONSE_GENERATED_EVENT
    chat_id: str
    response: Message


class MessageReceivedEvent(BaseEvent):
    type: EventType = EventType.MESSAGE_RECEIVED_EVENT
    chat_id: str
    message: Message


class MessageSavedToChatFileEvent(BaseEvent):
    type: EventType = EventType.MESSAGE_SAVED_TO_CHAT_FILE_EVENT
    chat_id: str
    message_id: str
    file_path: str


class UserApproveWorkEvent(BaseEvent):
    type: EventType = EventType.USER_APPROVE_WORK_EVENT
    chat_id: str

    # The work that was approved - could be file path, commit hash, etc.
    # TODO: Define specific approved work identifier
    approved_work: Optional[str] = None

    update_type: Literal['NewMessage', 'MessageSaved', 'AgentResponse']
