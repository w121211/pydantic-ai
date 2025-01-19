import * as fs from "fs/promises";
import * as path from "path";
import { Task } from "./types";

export class WorkspaceFileManager {
  constructor(private workspacePath: string) {}

  public async saveTaskToJson(task: Task): Promise<void> {
    await fs.writeFile(
      path.join(task.folderPath, "task.json"),
      JSON.stringify(task, null, 2),
      "utf-8"
    );
  }

  public async createTaskFolder(task: Task): Promise<string> {
    const formattedName = this.formatTaskName(task.title);
    const folderName = `task_${task.seqNumber}-${formattedName}`;
    const folderPath = path.join(this.workspacePath, folderName);

    await fs.mkdir(folderPath);

    // Set the folder path on the task
    task.folderPath = folderPath;

    // Save task.json
    await this.saveTaskToJson(task);

    return folderPath;
  }

  private async getNextTaskSeqNumber(): Promise<number> {
    const entries = await fs.readdir(this.workspacePath, {
      withFileTypes: true,
    });

    const taskNumbers = entries
      .filter(
        (entry) => entry.isDirectory() && /^task_\d+-\w*$/.test(entry.name)
      )
      .map((entry) => {
        const match = entry.name.match(/^task_(\d+)-/);
        return match ? parseInt(match[1]) : 0;
      });

    return taskNumbers.length > 0 ? Math.max(...taskNumbers) + 1 : 1;
  }

  private formatTaskName(name: string): string {
    // Replace spaces and special characters with underscores
    return name.replace(/[^a-zA-Z0-9]/g, "_");
  }

  async loadWorkspace(): Promise<Map<string, Task>> {
    const tasks = new Map<string, Task>();

    // 1. Scan workspace directory
    const entries = await fs.readdir(this.workspacePath, {
      withFileTypes: true,
    });

    // 2. Filter for task folders (pattern: task_[id]-[name])
    const taskFolders: fs.Dirent[] = entries
      .filter((entry: fs.Dirent): boolean => entry.isDirectory())
      .filter((entry: fs.Dirent): boolean => /^task_\d+-\w*$/.test(entry.name));

    // 3. Load each task folder
    for (const folder of taskFolders) {
      try {
        const taskSeqNumber = this.extractTaskSeqNumber(folder.name);
        const task = await this.loadTaskFromFolder(
          path.join(this.workspacePath, folder.name),
          taskId
        );
        tasks.set(taskId, task);
      } catch (error) {
        console.error(`Failed to load task folder ${folder.name}:`, error);
      }
    }

    return tasks;
  }

  public async loadTaskFromFolder(folderPath: string): Promise<Task> {
    const taskJsonPath = path.join(folderPath, "task.json");

    try {
      // Try loading existing lock file
      const fileContent = await fs.readFile(taskJsonPath, "utf-8");
      return JSON.parse(fileContent);
    } catch (error) {
      throw new Error(`Cannot load task json: ${error.message}`);

      // If lock doesn't exist, try to recreate from step0 output
      const taskSeqNumber = this.extractTaskSeqNumber(folderPath);
      return await this.recreateTaskJson(folderPath, taskSeqNumber);
    }
  }

  private extractTaskSeqNumber(folderName: string): string {
    const match = folderName.match(/^task_(\d+)-[a-zA-Z0-9_]+$/);
    if (!match) {
      throw new Error(`Invalid task folder name: ${folderName}`);
    }
    return match[1];
  }

  private async recreateTaskJson(
    folderPath: string,
    taskSeqNumber: string
  ): Promise<Task> {
    throw new Error("Method not implemented.");

    const step0Path = path.join(folderPath, "step0_planning");
    const outputPath = path.join(step0Path, "output.json");

    try {
      const outputContent = await fs.readFile(outputPath, "utf-8");
      const outputData = JSON.parse(outputContent);

      // Create minimal task object
      const task: Task = {
        id: `task_${taskSeqNumber}`, // TODO: Generate unique ID
        seqNumber: parseInt(taskSeqNumber),
        title: this.formatTaskName(path.basename(folderPath).split("-")[1]),
        status: "CREATED",
        subtasks: [],
        folderPath: folderPath,
        config: outputData.config || {},
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

      // Write new task file
      await fs.writeFile(
        path.join(folderPath, "task.json"),
        JSON.stringify(task, null, 2),
        "utf-8"
      );

      return task;
    } catch (error) {
      throw new Error(`Cannot recreate task json: ${error.message}`);
    }
  }
}
