import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict

import aiofiles

from .type_defs import Message, Task, TaskStatus

TASK_FOLDER_REGEX = r'^task_(\d+)-\w*$'


class WorkspaceFileManager:
    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path)

    async def load_workspace(self) -> Dict[str, Task]:
        tasks = {}

        # Scan workspace directory
        async for entry in aiofiles.os.scandir(self.workspace_path):
            if not entry.is_dir():
                continue

            # Check if folder matches task pattern
            # if not re.match(r'^task_\d+-\w*$', entry.name):
            if not re.match(TASK_FOLDER_REGEX, entry.name):
                continue

            try:
                folder_path = Path(entry.path)
                task = await self.load_task_from_folder(folder_path)
                tasks[task.id] = task
            except Exception as e:
                print(f'Failed to load task folder {entry.name}: {e}')

        return tasks

    # ============================================================
    # Task file operations
    # ============================================================

    async def save_task_to_json(self, task: Task) -> None:
        task_file = Path(task.folder_path) / 'task.json'
        task_json = task.model_dump(exclude_none=True)

        # Convert datetime objects to ISO format strings
        task_json['created_at'] = task_json['created_at'].isoformat()
        task_json['updated_at'] = task_json['updated_at'].isoformat()

        async with aiofiles.open(task_file, mode='w', encoding='utf-8') as f:
            await f.write(json.dumps(task_json, indent=2))

    async def create_task_folder(self, task: Task) -> Path:
        formatted_name = self._format_task_name(task.title)
        folder_name = f'task_{task.seq_number:03d}-{formatted_name}'
        folder_path = self.workspace_path / folder_name

        # Create task folder
        await aiofiles.os.makedirs(folder_path, exist_ok=True)

        # Update task with folder path
        task.folder_path = str(folder_path)

        # Save task data
        await self.save_task_to_json(task)

        return folder_path

    async def get_next_task_seq_number(self) -> int:
        matches = [
            match
            for item in await aiofiles.os.listdir(self.workspace_path)
            if (self.workspace_path / item).is_dir()
            and (match := re.match(TASK_FOLDER_REGEX, item))
        ]

        task_folders = [match.string for match in matches]
        sequence_numbers = [int(match.group(1)) for match in matches]

        return max(sequence_numbers) + 1 if sequence_numbers else 1

    async def load_task_from_folder(self, folder_path: Path) -> Task:
        task_json_path = folder_path / 'task.json'

        try:
            # Try loading existing task file
            async with aiofiles.open(task_json_path, encoding='utf-8') as f:
                content = await f.read()
                task_data = json.loads(content)

                # Convert ISO format strings back to datetime objects
                task_data['created_at'] = datetime.fromisoformat(
                    task_data['created_at']
                )
                task_data['updated_at'] = datetime.fromisoformat(
                    task_data['updated_at']
                )

                return Task(**task_data)

        except FileNotFoundError:
            # Try to recreate from step0 output
            seq_number = self._extract_task_seq_number(folder_path.name)
            return await self._recreate_task_json(folder_path, seq_number)

    async def _recreate_task_json(self, folder_path: Path, seq_number: int) -> Task:
        step0_path = folder_path / 'step0_planning'
        output_path = step0_path / 'output.json'

        try:
            async with aiofiles.open(output_path, encoding='utf-8') as f:
                output_data = json.loads(await f.read())

            # Create minimal task object
            task = Task(
                id=f'task_{seq_number:03d}',
                seq_number=seq_number,
                title=self._format_task_folder_name(folder_path.name.split('-')[1]),
                status=TaskStatus.CREATED,
                subtasks=[],
                folder_path=str(folder_path),
                config=output_data.get('config', {}),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # Save recreated task file
            await self.save_task_to_json(task)

            return task

        except FileNotFoundError as e:
            raise FileNotFoundError(f'Cannot recreate task.json: {e}')

    @staticmethod
    def _format_task_folder_name(name: str) -> str:
        return re.sub(r'[^\w\d]', '_', name, flags=re.UNICODE)

    @staticmethod
    def _extract_task_seq_number(folder_name: str) -> int:
        if match := re.match(TASK_FOLDER_REGEX, folder_name):
            return int(match.group(1))
        raise ValueError(f'Invalid task folder name: {folder_name}')

    # ============================================================
    # Chat file operations
    # ============================================================

    async def get_chat_file_path(
        self, task_id: str, subtask_id: str, chat_id: str
    ) -> str:
        task_folder = next(
            (
                folder
                for folder in self.workspace_path.iterdir()
                if folder.is_dir()
                and folder.name.startswith(f'task_{int(task_id):03d}-')
            ),
            None,
        )
        if not task_folder:
            raise ValueError(f'Task folder for task {task_id} not found')

        return str(task_folder / subtask_id / f'chat_{chat_id}.json')

    async def create_chat_file(
        self, task_id: str, subtask_id: str, chat_id: str
    ) -> None:
        file_path = await self.get_chat_file_path(task_id, subtask_id, chat_id)
        directory = Path(file_path).parent
        await aiofiles.os.makedirs(directory, exist_ok=True)

        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write('{}')

    async def save_message_to_chat_file(self, chat_id: str, message: Message) -> str:
        # 從 message metadata 獲取 task_id 和 subtask_id
        if (
            not message.metadata
            or not message.metadata.task_id
            or not message.metadata.subtask_id
        ):
            raise ValueError('Message metadata missing required task_id or subtask_id')

        file_path = await self.get_chat_file_path(
            message.metadata.task_id, message.metadata.subtask_id, chat_id
        )

        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(message.model_dump_json(indent=2))

        return file_path
