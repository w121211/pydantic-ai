import logging
from datetime import datetime
from uuid import uuid4

from .event_bus import IEventBus
from .repositories import TaskRepository
from .type_defs import (
    CreateTaskCommand,
    EventType,
    NextSubtaskTriggeredEvent,
    Role,
    StartSubtaskCommand,
    StartTaskCommand,
    Subtask,
    SubtaskStatus,
    Task,
    TaskCreatedEvent,
    TaskFolderCreatedEvent,
    TaskLoadedEvent,
    TaskStatus,
)
from .workspace_file_manager import WorkspaceFileManager


class TaskService:
    """Service for managing task lifecycle and operations."""

    def __init__(
        self,
        event_bus: IEventBus,
        task_repository: TaskRepository,
        workspace_manager: WorkspaceFileManager,
    ):
        self._event_bus = event_bus
        self._task_repository = task_repository
        self._workspace_manager = workspace_manager
        self._logger = logging.getLogger(__name__)

        # Register command handlers
        self._event_bus.subscribe(
            EventType.CREATE_TASK_COMMAND, self._handle_create_task_command
        )
        self._event_bus.subscribe(
            EventType.START_TASK_COMMAND, self._handle_start_task_command
        )
        self._event_bus.subscribe(
            EventType.NEXT_SUBTASK_TRIGGERED_EVENT, self._on_next_subtask_triggered
        )

    async def _handle_create_task_command(self, command: CreateTaskCommand) -> None:
        """Handle the creation of a new task.

        This method:
        1. Creates a new task with initial subtasks
        2. Creates the task folder
        3. Saves task metadata
        4. Auto-starts the task
        """
        task_id = str(uuid4())
        current_time = datetime.now()

        # Create initial task object
        task = Task(
            id=task_id,
            seq_number=0,  # Will be set by workspace manager
            title=command.task_name,
            status=TaskStatus.CREATED,
            folder_path='',  # Will be set after folder creation
            subtasks=[
                # Initial planning subtask
                Subtask(
                    id=str(uuid4()),
                    task_id=task_id,
                    seq_number=0,
                    title='Planning',
                    description='Initial planning phase',
                    status=SubtaskStatus.PENDING,
                    team={'agent': Role.ASSISTANT, 'human': None},
                    input_type='string',
                    output_type='json',
                ),
                # Setup subtask
                Subtask(
                    id=str(uuid4()),
                    task_id=task_id,
                    seq_number=1,
                    title='Setup',
                    description='Setup initial configuration',
                    status=SubtaskStatus.PENDING,
                    team={'agent': Role.FUNCTION_EXECUTOR, 'human': Role.USER},
                    input_type='json',
                    output_type='json',
                ),
            ],
            config=command.task_config,
            created_at=current_time,
            updated_at=current_time,
        )

        # Create task folder
        folder_path = await self._workspace_manager.create_task_folder(task)
        task.folder_path = folder_path

        # Publish TaskFolderCreated event
        await self._event_bus.publish(
            TaskFolderCreatedEvent(
                task_id=task_id,
                folder_path=folder_path,
                timestamp=datetime.now(),
                correlation_id=command.correlation_id,
            )
        )

        # Save task and publish TaskCreated event
        self._task_repository.save(task)
        await self._event_bus.publish(
            TaskCreatedEvent(
                task_id=task_id,
                task_name=command.task_name,
                config=command.task_config,
                timestamp=datetime.now(),
                correlation_id=command.correlation_id,
            )
        )

        # Auto-start the task
        await self._event_bus.publish(
            StartTaskCommand(
                task_id=task_id,
                timestamp=datetime.now(),
                correlation_id=command.correlation_id,
            )
        )

    async def _handle_start_task_command(self, command: StartTaskCommand) -> None:
        """Handle starting a task.

        This method:
        1. Loads the task state
        2. Validates task exists
        3. Starts the first subtask
        """
        task = self._task_repository.find_by_id(command.task_id)
        if not task:
            raise ValueError(f'Task {command.task_id} not found')

        # Load task state
        await self._event_bus.publish(
            TaskLoadedEvent(
                task_id=command.task_id,
                task_state=task,
                timestamp=datetime.now(),
                correlation_id=command.correlation_id,
            )
        )

        # Start first subtask if available
        if task.subtasks:
            first_subtask = task.subtasks[0]
            await self._event_bus.publish(
                StartSubtaskCommand(
                    task_id=task.id,
                    subtask_id=first_subtask.id,
                    timestamp=datetime.now(),
                    correlation_id=command.correlation_id,
                )
            )

    async def _on_next_subtask_triggered(
        self, event: NextSubtaskTriggeredEvent
    ) -> None:
        """Handle transitioning to the next subtask.

        This method:
        1. Validates current subtask is completed
        2. Finds and starts next subtask if available
        3. Completes task if no more subtasks
        """
        task = self._task_repository.find_by_id(event.task_id)
        if not task:
            raise ValueError(f'Task {event.task_id} not found')

        current_subtask = next(
            (s for s in task.subtasks if s.id == event.current_subtask_id), None
        )
        if not current_subtask:
            raise ValueError(f'Subtask {event.current_subtask_id} not found')

        if current_subtask.status != SubtaskStatus.COMPLETED:
            raise ValueError(
                f'Current subtask {event.current_subtask_id} not completed'
            )

        # Find next subtask
        next_subtask = next(
            (
                s
                for s in task.subtasks
                if s.seq_number == current_subtask.seq_number + 1
            ),
            None,
        )

        if next_subtask:
            # Start next subtask
            await self._event_bus.publish(
                StartSubtaskCommand(
                    task_id=task.id,
                    subtask_id=next_subtask.id,
                    timestamp=datetime.now(),
                    correlation_id=event.correlation_id,
                )
            )
        else:
            # Complete task if no more subtasks
            task.status = TaskStatus.COMPLETED
            await self._save_task(task)

    async def _save_task(self, task: Task) -> None:
        """Save task to both repository and file system."""
        task.updated_at = datetime.now()
        self._task_repository.save(task)
        await self._workspace_manager.save_task_to_json(task)
