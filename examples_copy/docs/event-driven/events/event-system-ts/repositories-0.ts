import { Task, Chat } from "./types";

interface IRepository<T> {
  get(id: string): T | undefined;
  add(item: T): void;
  update(id: string, update: Partial<T>): void;
  delete(id: string): void;
}

class BaseRepository<T extends { id: string }> implements IRepository<T> {
  protected items: Map<string, T> = new Map();

  get(id: string): T | undefined {
    return this.items.get(id);
  }

  add(item: T): void {
    this.items.set(item.id, item);
  }

  update(id: string, update: Partial<T>): void {
    const item = this.items.get(id);
    if (item) {
      this.items.set(id, { ...item, ...update });
    }
  }

  delete(id: string): void {
    this.items.delete(id);
  }
}

export class TaskRepository extends BaseRepository<Task> {}

export class ChatRepository extends BaseRepository<Chat> {}
