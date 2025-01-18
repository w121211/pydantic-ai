import { IEventBus } from "./event-system";
import { TaskRepository } from "./repositories";
import {
  CompleteSubtaskCommand,
  NextSubtaskTriggeredEvent,
  StartNewChatCommand,
  StartSubtaskCommand,
  Subtask,
  SubtaskCompletedEvent,
  SubtaskStartedEvent,
  SubtaskUpdatedEvent,
  Task,
} from "./types";
import { promises as fs } from "fs";
import * as path from "path";

class SubtaskService {
  constructor(private eventBus: IEventBus, private taskRepo: TaskRepository) {
    this.eventBus.subscribe<StartSubtaskCommand>(
      "StartSubtaskCommand",
      this.handleStartSubtaskCommand.bind(this)
    );
    this.eventBus.subscribe<CompleteSubtaskCommand>(
      "CompleteSubtaskCommand",
      this.handleCompleteSubtaskCommand.bind(this)
    );
    this.eventBus.subscribe<SubtaskUpdatedEvent>(
      "SubtaskUpdatedEvent",
      this.onSubtaskUpdated.bind(this)
    );
  }

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
  private async handleStartSubtaskCommand(
    command: StartSubtaskCommand
  ): Promise<void> {
    const { taskId, subtaskId } = command;

    // Get task and subtask from repository
    const { task, subtask } = this.taskRepo.getSubtask(taskId, subtaskId);

    // Get subtask's input
    const input = await this.getSubtaskInput(subtaskId);

    // Handle running task state
    if (task.status === "IN_PROGRESS" && task.currentSubtaskId) {
      if (task.currentSubtaskId === subtaskId) {
        console.warn(`Subtask ${subtaskId} is already running`);
        return;
      }

      // Pause the currently running subtask
      await this.pauseSubtask(taskId, subtaskId);
    }

    // Check and create subtask folder if needed
    const hasFolder = await this.checkSubtaskFolder(taskId, subtaskId);
    if (!hasFolder) {
      // Initialize subtask first
      await this.initSubtask(taskId, subtaskId);

      // Create folder and emit event
      await this.createSubtaskFolder(taskId, subtaskId);
    }

    // Start new chat (fire and forget)
    this.eventBus.publish<StartNewChatCommand>({
      type: "StartNewChatCommand",
      taskId,
      subtaskId,
      // input,
      timestamp: Date.now(),
    });

    // Update subtask status
    await this.eventBus.publish<SubtaskUpdatedEvent>({
      type: "SubtaskUpdatedEvent",
      taskId,
      subtaskId,
      status: "in_progress",
      timestamp: Date.now(),
    });

    // Mark subtask as started
    await this.eventBus.publish<SubtaskStartedEvent>({
      type: "SubtaskStartedEvent",
      taskId,
      subtaskId,
      input,
      timestamp: Date.now(),
    });
  }

  /**
   * This can be triggered when 1. the user approves the subtask output, 2. the subtask output is auto-approved.
   *
   * Steps:
   * 1. Move the previous subtask's output to the history folder.
   * 2. Save the output. The file name should be 'output.json'.
   * 3. Update the subtask status. Emit 'SubtaskUpdated' event.
   * 4. Emit NextSubtaskTriggeredEvent.
   */
  private async handleCompleteSubtaskCommand(
    command: CompleteSubtaskCommand
  ): Promise<void> {
    const { taskId, subtaskId, output } = command;

    // 1. Get the task and subtask
    const { task, subtask } = this.taskRepo.getSubtask(taskId, subtaskId);

    // 2. Save the current output to history
    const subtaskPath = this.getSubtaskFolderPath(taskId, subtaskId);
    const historyPath = path.join(subtaskPath, "history");
    await fs.mkdir(historyPath, { recursive: true });

    // Move existing output to history with timestamp
    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, "");
      const currentOutput = await fs.readFile(
        path.join(subtaskPath, "output.json")
      );
      await fs.writeFile(
        path.join(historyPath, `output_${timestamp}.json`),
        currentOutput
      );
    } catch (error) {
      // Ignore if no existing output
    }

    // 3. Save new output
    await fs.writeFile(
      path.join(subtaskPath, "output.json"),
      JSON.stringify(output, null, 2)
    );

    // 4. Update subtask status and emit event
    await this.eventBus.publish<SubtaskUpdatedEvent>({
      type: "SubtaskUpdatedEvent",
      taskId,
      subtaskId,
      status: "completed",
      timestamp: Date.now(),
      // correlationId,
    });

    // 5. Complete subtask and trigger next
    await this.eventBus.publish<SubtaskCompletedEvent>({
      type: "SubtaskCompletedEvent",
      taskId,
      subtaskId,
      timestamp: Date.now(),
      // correlationId,
    });

    await this.eventBus.publish<NextSubtaskTriggeredEvent>({
      type: "NextSubtaskTriggeredEvent",
      taskId,
      currentSubtaskId: subtaskId,
      timestamp: Date.now(),
      // correlationId,
    });
  }

  private async onSubtaskUpdated(event: SubtaskUpdatedEvent): Promise<void> {
    const { subtask } = this.taskRepo.getSubtask(event.taskId, event.subtaskId);
    subtask.status = event.status;
    this.taskRepo.saveSubtask(subtask);
  }

  // Helper methods

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
