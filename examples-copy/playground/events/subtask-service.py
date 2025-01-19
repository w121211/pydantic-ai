import os
from typing import Optional

from .event_bus import IEventBus
from .repositories import TaskRepository
from .type_defs import (
    CompleteSubtaskCommand,
    NextSubtaskTriggeredEvent,
    StartNewChatCommand,
    StartSubtaskCommand,
    SubtaskCompletedEvent,
    SubtaskStartedEvent,
    SubtaskUpdatedEvent,
)


class SubtaskService:
    def __init__(self, event_bus: IEventBus, task_repo: TaskRepository):
        self._event_bus = event_bus
        self._task_repo = task_repo

        # Subscribe to events
        self._event_bus.subscribe(
            'StartSubtaskCommand', self._handle_start_subtask_command
        )
        self._event_bus.subscribe(
            'CompleteSubtaskCommand', self._handle_complete_subtask_command
        )
        self._event_bus.subscribe('SubtaskUpdatedEvent', self._on_subtask_updated)

    async def _handle_start_subtask_command(self, command: StartSubtaskCommand) -> None:
        """Handle the start subtask command and manage the task execution flow.

        Steps:
        1. Get task item and subtask item from store
        2. Get subtask input from previous output or initial input
        3. Check running task state and handle accordingly
        4. Create/verify subtask folder
        5. Start new chat and emit events
        """
        task, subtask = self._task_repo.get_subtask(command.task_id, command.subtask_id)

        # Get subtask's input
        input_data = await self._get_subtask_input(command.subtask_id)

        # Handle running task state
        if task.status == 'IN_PROGRESS' and task.current_subtask_id:
            if task.current_subtask_id == command.subtask_id:
                print(f'Warning: Subtask {command.subtask_id} is already running')
                return

            # Pause currently running subtask
            await self._pause_subtask(command.task_id, command.subtask_id)

        # Check and create subtask folder if needed
        has_folder = await self._check_subtask_folder(
            command.task_id, command.subtask_id
        )
        if not has_folder:
            # Initialize subtask first
            await self._init_subtask(command.task_id, command.subtask_id)
            await self._create_subtask_folder(command.task_id, command.subtask_id)

        # Start new chat (fire and forget)
        await self._event_bus.publish(
            StartNewChatCommand(
                task_id=command.task_id,
                subtask_id=command.subtask_id,
                timestamp=command.timestamp,
            )
        )

        # Update subtask status
        await self._event_bus.publish(
            SubtaskUpdatedEvent(
                task_id=command.task_id,
                subtask_id=command.subtask_id,
                status='in_progress',
                timestamp=command.timestamp,
            )
        )

        # Mark subtask as started
        await self._event_bus.publish(
            SubtaskStartedEvent(
                task_id=command.task_id,
                subtask_id=command.subtask_id,
                input=input_data,
                timestamp=command.timestamp,
            )
        )

    async def _handle_complete_subtask_command(
        self, command: CompleteSubtaskCommand
    ) -> None:
        """Steps to complete a subtask.

        1. Move previous output to history
        2. Save new output
        3. Update subtask status
        4. Trigger next subtask
        """
        task, subtask = self._task_repo.get_subtask(command.task_id, command.subtask_id)

        # Handle output files
        subtask_path = self._get_subtask_folder_path(
            command.task_id, command.subtask_id
        )
        history_path = os.path.join(subtask_path, 'history')
        os.makedirs(history_path, exist_ok=True)

        # Move existing output to history with timestamp
        try:
            from datetime import datetime

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_output_path = os.path.join(subtask_path, 'output.json')

            if os.path.exists(current_output_path):
                with open(current_output_path) as f:
                    current_output = f.read()

                history_file = os.path.join(history_path, f'output_{timestamp}.json')
                with open(history_file, 'w') as f:
                    f.write(current_output)
        except Exception:
            # Ignore if no existing output
            pass

        # Save new output
        with open(os.path.join(subtask_path, 'output.json'), 'w') as f:
            f.write(command.output)

        # Update subtask status and emit event
        await self._event_bus.publish(
            SubtaskUpdatedEvent(
                task_id=command.task_id,
                subtask_id=command.subtask_id,
                status='completed',
                timestamp=command.timestamp,
            )
        )

        # Complete subtask and trigger next
        await self._event_bus.publish(
            SubtaskCompletedEvent(
                task_id=command.task_id,
                subtask_id=command.subtask_id,
                timestamp=command.timestamp,
            )
        )

        await self._event_bus.publish(
            NextSubtaskTriggeredEvent(
                task_id=command.task_id,
                current_subtask_id=command.subtask_id,
                timestamp=command.timestamp,
            )
        )

    async def _on_subtask_updated(self, event: SubtaskUpdatedEvent) -> None:
        """Updates subtask status in repository when status changes."""
        task, subtask = self._task_repo.get_subtask(event.task_id, event.subtask_id)
        subtask.status = event.status
        self._task_repo.save_subtask(subtask)

    # ----------------
    # Helper Methods
    # ----------------

    async def _get_subtask_input(self, subtask_id: str) -> Optional[str]:
        """Gets input for a subtask from either specified sources.

        1. Previous subtask's output.json
        2. Initial input from task store for first subtask

        Note: Currently using string input/output only
        File structure:
            workspace/task_id/
                step1_validate_input/
                    output.json
                    history/
                        output_YYYYMMDD_HHMMSS.json
        """
        # TODO: Implement actual input retrieval logic
        return 'Example input string'

    def _get_subtask_folder_path(
        self, task_id: str, subtask_id: str, workspace: str = 'tasks'
    ) -> str:
        return os.path.join(workspace, task_id, 'subtasks', subtask_id)

    async def _check_subtask_folder(
        self, task_id: str, subtask_id: str, workspace: str = 'tasks'
    ) -> bool:
        folder_path = self._get_subtask_folder_path(task_id, subtask_id, workspace)
        return os.path.exists(folder_path)

    async def _init_subtask(self, task_id: str, subtask_id: str) -> None:
        raise NotImplementedError('Not yet implemented')

    async def _create_subtask_folder(self, task_id: str, subtask_id: str) -> None:
        raise NotImplementedError('Not yet implemented')

    async def _pause_subtask(self, task_id: str, subtask_id: str) -> None:
        """Handles pausing of a running subtask.

        Notes:
        1. Handles only subtask scope; task scope handled via SubtaskPaused event
        2. No parallel subtasks support yet
        3. Pausing subtask = pausing task for now

        Steps:
        - Verify subtask state and ID
        - Update task status
        - Save progress
        - Emit events
        """
        raise NotImplementedError('Not yet implemented')
