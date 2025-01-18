import { IEventBus } from "./event-system-0";
import { NextSubtaskTriggeredEvent, StartSubtaskCommand, Task } from "./types";
import { TaskRepository } from "./repositories-0";
import { WorkspaceFileManager } from "./workspace-loader";

// Utility types
// type TaskUpdate = Partial<Task>;
// type TaskCreateParams = Omit<Task, "id" | "createdAt" | "updatedAt">;

class TaskService {
  constructor(
    private eventBus: IEventBus,
    private taskRepository: TaskRepository,
    private workspaceFileManager: WorkspaceFileManager
  ) {
    // Command handlers
    this.eventBus.subscribe<CreateTaskCommand>(
      "CreateTaskCommand",
      this.handleCreateTaskCommand.bind(this)
    );
    this.eventBus.subscribe<StartTaskCommand>(
      "StartTaskCommand",
      this.handleStartTaskCommand.bind(this)
    );

    // Event handlers
    // this.eventBus.subscribe<TaskCreatedEvent>(
    //   "TaskCreated",
    //   this.handleTaskCreated.bind(this)
    // );
    // this.eventBus.subscribe<TaskFolderCreatedEvent>(
    //   "TaskFolderCreated",
    //   this.handleTaskFolderCreated.bind(this)
    // );
  }

  private async handleCreateTaskCommand(
    command: CreateTaskCommand
  ): Promise<void> {
    const taskId = crypto.randomUUID();

    const task: Task = {
      id: taskId,
      seqNumber: 0,
      title: "This is a task",
      status: "CREATED",
      folderPath: "",
      subtasks: [
        {
          id: crypto.randomUUID(),
          taskId: taskId,
          team: {
            agent: "@assistant",
            human: null,
          },
          stepNumber: 0,
          title: "Planning",
          description: "Initial planning phase",
          status: "pending",
          inputType: "string",
          outputType: "json",
        },
        {
          id: crypto.randomUUID(),
          taskId: taskId,
          team: {
            agent: "@function_executor",
            human: "@user",
          },
          stepNumber: 1,
          title: "Setup",
          description: "Setup initial configuration",
          status: "pending",
          inputType: "json",
          outputType: "json",
        },
      ],
      config: command.taskConfig,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    // Create task folder
    const folderPath = await this.workspaceFileManager.createTaskFolder(task);
    task.folderPath = folderPath;

    await this.eventBus.publish<TaskFolderCreatedEvent>({
      type: "TaskFolderCreated",
      taskId,
      folderPath,
      timestamp: Date.now(),
      // correlationId: command.correlationId,
    });

    // Emit TaskCreated event
    await this.eventBus.publish<TaskCreatedEvent>({
      type: "TaskCreated",
      taskId,
      taskName: command.taskName,
      config: command.taskConfig,
      timestamp: Date.now(),
      // correlationId: command.correlationId,
    });
    this.taskRepository.save(task);

    // Auto start task
    await this.eventBus.publish<StartTaskCommand>({
      type: "StartTaskCommand",
      taskId,
      timestamp: Date.now(),
      // correlationId: command.correlationId,
    });
  }

  private async handleStartTaskCommand(
    command: StartTaskCommand
  ): Promise<void> {
    const { taskId } = command;
    const task = this.taskRepository.findById(taskId);

    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }

    // Load task state first
    await this.eventBus.publish<TaskLoadedEvent>({
      type: "TaskLoaded",
      taskId,
      taskState: task,
      timestamp: Date.now(),
      // correlationId: command.correlationId,
    });

    // Get first subtask and start it
    const subtaskId = task.subtasks[0].id;
    const correlationId = crypto.randomUUID();
    await this.eventBus.publish<StartSubtaskCommand>({
      type: "StartSubtaskCommand",
      taskId,
      subtaskId,
      timestamp: Date.now(),
      correlationId,
    });
  }

  private async onNextSubtaskTriggered(
    event: NextSubtaskTriggeredEvent
  ): Promise<void> {
    const task = this.taskRepository.findById(event.taskId);
    if (!task) {
      throw new Error(`Task ${event.taskId} not found`);
    }

    const subtask = task.subtasks.find((s) => s.id === event.currentSubtaskId);
    if (!subtask) {
      throw new Error(`Subtask ${event.currentSubtaskId} not found`);
    }
    if (subtask.status !== "completed") {
      throw new Error(`Subtask ${event.currentSubtaskId} not completed yet`);
    }

    // Find next subtask if any
    const nextSubtask = task.subtasks.find(
      (s) => s.stepNumber === subtask.stepNumber + 1
    );
    if (nextSubtask) {
      await this.eventBus.publish<StartSubtaskCommand>({
        type: "StartSubtaskCommand",
        taskId: task.id,
        subtaskId: nextSubtask.id,
        timestamp: Date.now(),
        correlationId: crypto.randomUUID(),
      });
    } else {
      // All subtasks completed, mark task as completed
      task.status = "COMPLETED";
    }

    await this.saveTask(task);
  }

  private async onUserRenamedTaskFolder(
    event: TaskFolderRenamedEvent
  ): Promise<void> {
    /**
     * 1. Is the new name followed the task folder naming convention? If not, warn the user.
     * 2. Update the task folder path in task.
     */
    const { taskId } = event;
    const task = this.taskRepository.findById(taskId);
    if (!task) {
      throw new Error(`Task ${event.taskId} not found`);
    }

    // Update task with new folder path
    task.folderPath = event.newFolderPath;
    task.updatedAt = Date.now();

    // Save updated task
    await this.saveTask(task);
  }

  private async onUserDeletedTaskJson(): Promise<void> {
    /**
     * 1.
     */
  }

  private async saveTask(task: Task): Promise<void> {
    this.taskRepository.save(task);
    await this.workspaceFileManager.saveTaskToJson(task);
  }

  // private async onTaskCreated(event: TaskCreatedEvent): Promise<void> {
  //   const task: Task = {
  //     id: event.taskId,
  //     name: event.taskName,
  //     status: TaskStatus.CREATED,
  //     subtasks: [],
  //     config: event.config,
  //     createdAt: event.timestamp,
  //     updatedAt: event.timestamp,
  //   };

  //   this.taskRepository.save(task);
  // }

  // private async onTaskFolderCreated(
  //   event: TaskFolderCreatedEvent
  // ): Promise<void> {
  //   const task = this.tasks.get(event.taskId);
  //   if (task) {
  //     task.folderPath = event.folderPath;
  //     task.updatedAt = event.timestamp;
  //     this.tasks.set(event.taskId, task);
  //   }
  // }
}
