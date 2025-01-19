from abc import ABC
from typing import Dict, Generic, List, Optional, Protocol, Tuple, TypeVar

from .type_defs import Chat, Subtask, Task


class EntityProtocol(Protocol):
    id: str


T = TypeVar('T', bound=EntityProtocol)


class Repository(ABC, Generic[T]):
    def __init__(self):
        self._entities: Dict[str, T] = {}

    def find_by_id(self, id: str) -> Optional[T]:
        return self._entities.get(id)

    def find_all(self) -> List[T]:
        return list(self._entities.values())

    def save(self, entity: T) -> None:
        if not hasattr(entity, 'id'):
            raise ValueError("Entity must have an 'id' attribute")
        self._entities[entity.id] = entity

    def remove(self, entity_id: str) -> None:
        self._entities.pop(entity_id, None)


class TaskRepository(Repository[Task]):
    def get_subtask(self, task_id: str, subtask_id: str) -> Tuple[Task, Subtask]:
        task = self.find_by_id(task_id)
        if task is None:
            raise KeyError(f'Task {task_id} not found')

        subtask = next((s for s in task.subtasks if s.id == subtask_id), None)
        if subtask is None:
            raise KeyError(f'Subtask {subtask_id} not found in task {task_id}')

        return task, subtask

    def save_subtask(self, subtask: Subtask) -> None:
        task = self.find_by_id(subtask.task_id)
        if task is None:
            raise KeyError(f'Task {subtask.task_id} not found')

        # Find and update the existing subtask
        for i, existing_subtask in enumerate(task.subtasks):
            if existing_subtask.id == subtask.id:
                task.subtasks[i] = subtask
                self.save(task)
                return

        # If subtask wasn't found, append it
        task.subtasks.append(subtask)
        self.save(task)


class ChatRepository(Repository[Chat]):
    pass
