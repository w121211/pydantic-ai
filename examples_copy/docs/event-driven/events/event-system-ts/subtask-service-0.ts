import { BaseEvent, IEventBus } from "./event-system-0";
import { TaskStore } from "./stores-0";
import { Subtask } from "./types";
import { promises as fs } from "fs";
import * as path from "path";

// Subtask Events
interface SubtaskInitializedEvent extends BaseEvent {
  type: "SubtaskInitialized";
  taskId: string;
  subtaskId: string;
  subtaskType: string;
}

interface SubtaskCompletedEvent extends BaseEvent {
  type: "SubtaskCompleted";
  taskId: string;
  subtaskId: string;
  output: any;
}

interface StartSubtaskCommand extends BaseEvent {
  type: "StartSubtaskCommand";
  taskId: string;
  subtaskId: string;
  subtaskType: string;
}

interface CompleteSubtaskCommand extends BaseEvent {
  type: "CompleteSubtaskCommand";
  taskId: string;
  subtaskId: string;
  output: any;
  requiresApproval: boolean;
}

interface SubtaskStartedEvent extends BaseEvent {
  type: "SubtaskStarted";
  taskId: string;
  subtaskId: string;
  input?: any;
}

interface SubtaskPausedEvent extends BaseEvent {
  type: "SubtaskPaused";
  taskId: string;
  subtaskId: string;
}

interface StartNewChatCommand extends BaseEvent {
  type: "StartNewChatCommand";
  taskId: string;
  subtaskId: string;
  input?: any;
}

interface SubtaskFolderCreatedEvent extends BaseEvent {
  type: "SubtaskFolderCreated";
  taskId: string;
  subtaskId: string;
  folderPath: string;
}

class SubtaskService {
  private subtasks: Map<string, Subtask> = new Map();

  constructor(private eventBus: IEventBus, private taskStore: TaskStore) {
    this.eventBus.subscribe<StartSubtaskCommand>(
      "StartSubtaskCommand",
      this.handleStartSubtaskCommand.bind(this)
    );

    this.eventBus.subscribe<CompleteSubtaskCommand>(
      "CompleteSubtaskCommand",
      this.handleFinishSubtask.bind(this)
    );
  }

  private async getSubtaskInput(subtaskId: string): Promise<string> {
    /**
     * Gets the input data for a subtask.
     *
     * The function retrieves input from one of the following sources, in priority order:
     * 1. Previous subtask's output.json file located at:
     *    ${workspace}/${task_id}/${prev_step_number}_${prev_subtask_name}/output.json
     *
     * 2. For the first subtask in a sequence:
     *    Initial input stored in TaskStore
     *
     * @remarks
     * - Currently assumes all input is of type 'string' with no parsing required
     * - File structure follows the convention:
     *   ${workspace}/${task_id}/
     *     step1_validate_input/
     *       output.json             # Latest output
     *       history/                # Historical records
     *         output_YYYYMMDD_HHMMSS.json
     *
     * @example Output JSON format:
     * {
     *   "summary": {
     *     "step": "驗證輸入資料",
     *     "status": "成功",
     *     "completed_at": "2024-01-13 15:30:00",
     *     "message": "驗證通過：共處理 100 筆資料"
     *   },
     *   "result": {
     *     // Actual output content
     *   }
     * }
     */

    // TODO
    return "This is an example output string";
  }

  private async onStartSubtaskCommand(
    command: StartSubtaskCommand
  ): Promise<void> {
    /**
     * Steps
     * - Get the task item from the store. If not found, raise error
     * - Get the subtask item from the task item.
     * - Check is this subtask is prepared by
     *   - Need to have the input. If not, try to get it from the previous subtask's output.
     * - Check is the task currently running?
     *   - If yes, then check which subtask is running.
     *     - If the running subtask is this. Do nothing. Log a warnning message.
     *     - If the running subtask is not this. Pause the running subtask first.
     * - Check is the subtask folder is existed, if not, create one.
     *   - If is existed. Do nothing.
     * - emit 'StartNewChatCommand' -> This will trigger the proceeded process. No need to wait.
     * - emit 'SubtaskStarted'
     */

    const { taskId, subtaskId, correlationId } = command;

    // 1. Get task from store
    const task = this.taskStore.get(taskId);
    if (!task) {
      throw new Error(`Task ${taskId} not found`);
    }

    // 2. Get subtask from task
    const subtask = task.subtasks.find((s) => s.id === subtaskId);
    if (!subtask) {
      throw new Error(`Subtask ${subtaskId} not found in task ${taskId}`);
    }

    // 3. Get subtask's input
    const input = await this.getSubtaskInput(subtaskId);

    // 4. Handle running task state
    if (task.status === "IN_PROGRESS" && task.currentSubtaskId) {
      if (task.currentSubtaskId === subtaskId) {
        console.warn(`Subtask ${subtaskId} is already running`);
        return;
      }

      // Pause the currently running subtask
      await this.pauseSubtask(taskId, subtaskId);
    }

    // 5. Check and create subtask folder if needed
    const hasFolder = await this.checkSubtaskFolder(taskId, subtaskId);
    if (!hasFolder) {
      // Initialize subtask first
      await this.initSubtask(taskId, subtaskId);

      // Create folder and emit event
      await this.createSubtaskFolder(taskId, subtaskId);
    }

    // 6. Start new chat (fire and forget)
    this.eventBus.publish<StartNewChatCommand>({
      type: "StartNewChatCommand",
      taskId,
      subtaskId,
      input,
      timestamp: Date.now(),
      correlationId,
    });

    // 7. Mark subtask as started
    await this.eventBus.publish<SubtaskStartedEvent>({
      type: "SubtaskStarted",
      taskId,
      subtaskId,
      input,
      timestamp: Date.now(),
      correlationId,
    });
  }

  private async handleCompleteSubtaskCommand(
    command: CompleteSubtaskCommand
  ): Promise<void> {
    const { taskId, subtaskId, output } = command;

    await this.eventBus.publish<SubtaskOutputGeneratedEvent>({
      type: "SubtaskOutputGenerated",
      taskId,
      subtaskId,
      output,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    if (!command.requiresApproval) {
      // Auto complete if no approval needed
      await this.completeSubtask(taskId, subtaskId, command.correlationId);
    }
  }

  private async completeSubtask(
    taskId: string,
    subtaskId: string,
    correlationId: string
  ): Promise<void> {
    await this.eventBus.publish<SubtaskCompletedEvent>({
      type: "SubtaskCompleted",
      taskId,
      subtaskId,
      timestamp: Date.now(),
      correlationId,
    });

    await this.eventBus.publish<NextSubtaskTriggeredEvent>({
      type: "NextSubtaskTriggered",
      taskId,
      currentSubtaskId: subtaskId,
      timestamp: Date.now(),
      correlationId,
    });
  }

  private getSubtaskFolderPath(
    taskId: string,
    subtaskId: string,
    workspace: string = "tasks"
  ): string {
    return path.join(workspace, taskId, "subtasks", subtaskId);
  }

  private async checkSubtaskFolder(
    taskId: string,
    subtaskId: string,
    workspace: string = "tasks"
  ): Promise<boolean> {
    // Implementation to check if folder exists
    try {
      await fs.access(this.getSubtaskFolderPath(workspace, taskId, subtaskId));
      return true;
    } catch {
      return false;
    }
  }

  private async initSubtask(taskId: string, subtaskId: string): Promise<void> {
    throw new Error("Not yet implemented");
  }

  private async createSubtaskFolder(
    taskId: string,
    subtaskId: string
  ): Promise<void> {
    throw new Error("Not yet implemented");
  }

  private async pauseSubtask(taskId: string, subtaskId: string): Promise<void> {
    /**
     * Remarks:
     * 1. This method only consider the subtask's scope. For the task's scope, it will process the rest through 'SubtaskPaused' event. 
     * 2. For now we don't consider parallel subtasks, so when pausing the subtask, the task is also paused.
     * 3. Although we seperate the pauseSubtask and pauseTask methods, there is no difference for now.
     * 
     * Steps:
Subtask Status Check
Verify subtaskId matches current running subtask
Check if subtask is in a pausable state

Pause Actions
Update task status in store
Clear currentSubtaskId
Save any in-progress work

Event Publishing
Emit SubtaskPausedEvent
Include taskId, subtaskId, timestamp
Use consistent correlationId pattern
     */
    throw new Error("Not yet implemented");
  }
}
