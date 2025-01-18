import { Task, Chat, Subtask } from "./types";

interface IRepository<T> {
  findById(id: string): T | undefined;
  findAll(): T[];
  save(item: T): void;
  remove(id: string): void;
}

class BaseRepository<T extends { id: string }> implements IRepository<T> {
  protected entities: Map<string, T> = new Map();

  findById(id: string): T | undefined {
    return this.entities.get(id);
  }

  findAll(): T[] {
    return Array.from(this.entities.values());
  }

  save(item: T): void {
    this.entities.set(item.id, item);
  }

  remove(id: string): void {
    this.entities.delete(id);
  }
}

export class TaskRepository extends BaseRepository<Task> {
  getSubtask(
    taskId: string,
    subtaskId: string
  ): { task: Task; subtask: Subtask } {
    const task = this.findById(taskId);
    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }

    const subtask = task.subtasks.find((s) => s.id === subtaskId);
    if (!subtask) {
      throw new Error(`Subtask ${subtaskId} not found in task ${taskId}`);
    }

    return { task, subtask };
  }

  saveSubtask(updatedSubtask: Subtask): void {
    const { taskId } = updatedSubtask;
    const task = this.findById(taskId);
    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }

    const index = task.subtasks.findIndex((s) => s.id === updatedSubtask.id);
    if (index === -1) {
      throw new Error(
        `Subtask ${updatedSubtask.id} not found in task ${taskId}`
      );
    }

    task.subtasks[index] = updatedSubtask;
    this.save(task);
  }
}

export class ChatRepository extends BaseRepository<Chat> {}
