import { BaseCommand, BaseEvent, IEventBus } from "./event-system-0";

// Utility types
// type TaskUpdate = Partial<Task>;
// type TaskCreateParams = Omit<Task, "id" | "createdAt" | "updatedAt">;

// Commands
interface StartTaskCommand extends BaseCommand {
  type: "StartTaskCommand";
  taskId: string;
}

interface CreateTaskCommand extends BaseCommand {
  type: "UserCreateTaskCommand";
  taskName: string;
  taskConfig: any;
}

// Events
interface TaskCreatedEvent extends BaseEvent {
  type: "TaskCreated";
  taskId: string;
  taskName: string;
  config: any;
}

interface TaskFolderCreatedEvent extends BaseEvent {
  type: "TaskFolderCreated";
  taskId: string;
  folderPath: string;
}

interface TaskInitializedEvent extends BaseEvent {
  type: "TaskInitialized";
  taskId: string;
  initialState: any;
}

interface TaskLoadedEvent extends BaseEvent {
  type: "TaskLoaded";
  taskId: string;
  taskState: Task;
}

class TaskService {
  private tasks: Map<string, Task> = new Map();

  constructor(private eventBus: IEventBus) {
    // Command handlers
    this.eventBus.subscribe<CreateTaskCommand>(
      "UserCreateTaskCommand",
      this.handleCreateTask.bind(this)
    );
    this.eventBus.subscribe<StartTaskCommand>(
      "StartTaskCommand",
      this.handleStartTask.bind(this)
    );

    // Event handlers
    this.eventBus.subscribe<TaskCreatedEvent>(
      "TaskCreated",
      this.handleTaskCreated.bind(this)
    );
    this.eventBus.subscribe<TaskFolderCreatedEvent>(
      "TaskFolderCreated",
      this.handleTaskFolderCreated.bind(this)
    );
  }

  private async handleCreateTask(command: CreateTaskCommand): Promise<void> {
    const taskId = crypto.randomUUID();
    const task: Task = {
      id: taskId,
      name: command.taskName,
      status: "CREATED",
      subtasks: [],
      config: command.taskConfig,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    this.tasks.set(taskId, task);

    // Create task folder
    const folderPath = `${user_given_workspace}/tasks/${taskId}`;
    await fs.promises.mkdir(folderPath, { recursive: true });

    await this.eventBus.publish<TaskFolderCreatedEvent>({
      type: "TaskFolderCreated",
      taskId,
      folderPath,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    // Emit TaskCreated event
    await this.eventBus.publish<TaskCreatedEvent>({
      type: "TaskCreated",
      taskId,
      taskName: command.taskName,
      config: command.taskConfig,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    // Initialize task
    // 1. 創設 task.lock
    // 2.
    await this.eventBus.publish<TaskInitializedEvent>({
      type: "TaskInitialized",
      taskId,
      initialState: {
        status: TaskStatus.INITIALIZED,
        config: command.taskConfig,
      },
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    // Auto start task
    await this.eventBus.publish<StartTaskCommand>({
      type: "StartTaskCommand",
      taskId,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });
  }

  private async handleStartTask(command: StartTaskCommand): Promise<void> {
    const { taskId } = command;
    const task = this.tasks.get(taskId);

    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }

    // Load task state first
    await this.eventBus.publish<TaskLoadedEvent>({
      type: "TaskLoaded",
      taskId,
      taskState: task,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    // Re-initialize if needed
    if (task.status === TaskStatus.CREATED) {
      await this.eventBus.publish<TaskInitializedEvent>({
        type: "TaskInitialized",
        taskId,
        initialState: {
          status: TaskStatus.INITIALIZED,
          config: task.config,
        },
        timestamp: Date.now(),
        correlationId: command.correlationId,
      });
    }

    // Start first subtask
    await this.startFirstSubtask(taskId, command.correlationId);
  }

  private async startFirstSubtask(
    taskId: string,
    correlationId: string
  ): Promise<void> {
    const subtaskId = crypto.randomUUID();

    await this.eventBus.publish<StartSubtaskCommand>({
      type: "StartSubtaskCommand",
      taskId,
      subtaskId,
      subtaskType: "FIRST_TASK", // 依實際需求設定
      timestamp: Date.now(),
      correlationId,
    });
  }

  private async handleTaskCreated(event: TaskCreatedEvent): Promise<void> {
    const task: Task = {
      id: event.taskId,
      name: event.taskName,
      status: TaskStatus.CREATED,
      subtasks: [],
      config: event.config,
      createdAt: event.timestamp,
      updatedAt: event.timestamp,
    };

    this.tasks.set(event.taskId, task);
  }

  private async handleTaskFolderCreated(
    event: TaskFolderCreatedEvent
  ): Promise<void> {
    const task = this.tasks.get(event.taskId);
    if (task) {
      task.folderPath = event.folderPath;
      task.updatedAt = event.timestamp;
      this.tasks.set(event.taskId, task);
    }
  }
}
