// Types
interface Event {
  type: string;
  payload: any;
}

// Base command and event types
interface Command {
  type: string;
  payload: any;
}

// Task related types
interface Task {
  id: string;
  status: 'created' | 'initialized' | 'in_progress' | 'completed';
  currentSubtaskId?: string;
}

interface Subtask {
  id: string;
  taskId: string;
  status: 'initialized' | 'in_progress' | 'completed';
  output?: any;
}

// Event Bus interface (assumed to be provided)
interface EventBus {
  publish(event: Event): void;
  subscribe(eventType: string, handler: (event: Event) => void): void;
}

// Task Service
class TaskService {
  private tasks: Map<string, Task> = new Map();
  
  constructor(private eventBus: EventBus) {
    this.setupSubscriptions();
  }

  private setupSubscriptions() {
    this.eventBus.subscribe('UserCreateTaskCommand', this.handleCreateTask.bind(this));
    this.eventBus.subscribe('StartTaskCommand', this.handleStartTask.bind(this));
    this.eventBus.subscribe('SubtaskCompleted', this.handleSubtaskCompleted.bind(this));
  }

  private handleCreateTask(event: Event) {
    const taskId = event.payload.taskId;
    const task: Task = {
      id: taskId,
      status: 'created'
    };
    
    this.tasks.set(taskId, task);
    
    // Emit events according to the flow
    this.eventBus.publish({
      type: 'TaskCreated',
      payload: { taskId }
    });
    
    this.eventBus.publish({
      type: 'TaskFolderCreated',
      payload: { taskId }
    });
    
    this.eventBus.publish({
      type: 'TaskInitialized',
      payload: { taskId }
    });
    
    // Automatically start the task
    this.eventBus.publish({
      type: 'StartTaskCommand',
      payload: { taskId }
    });
  }

  private handleStartTask(event: Event) {
    const { taskId } = event.payload;
    const task = this.tasks.get(taskId);
    
    if (!task) return;
    
    this.eventBus.publish({
      type: 'TaskLoaded',
      payload: { taskId }
    });
    
    this.eventBus.publish({
      type: 'StartSubtaskCommand',
      payload: { 
        taskId,
        subtaskId: this.generateSubtaskId() // In real implementation, this would be more sophisticated
      }
    });
    
    task.status = 'in_progress';
    this.tasks.set(taskId, task);
  }

  private handleSubtaskCompleted(event: Event) {
    const { taskId, subtaskId } = event.payload;
    const task = this.tasks.get(taskId);
    
    if (!task) return;

    // Determine if there are more subtasks
    const nextSubtaskId = this.getNextSubtaskId(subtaskId);
    
    if (nextSubtaskId) {
      this.eventBus.publish({
        type: 'NextSubtaskTriggered',
        payload: { 
          taskId,
          subtaskId: nextSubtaskId
        }
      });
      
      this.eventBus.publish({
        type: 'StartSubtaskCommand',
        payload: { 
          taskId,
          subtaskId: nextSubtaskId
        }
      });
    } else {
      task.status = 'completed';
      this.tasks.set(taskId, task);
    }
  }

  private generateSubtaskId(): string {
    return `subtask_${Date.now()}`;
  }

  private getNextSubtaskId(currentSubtaskId: string): string | null {
    // Implementation would depend on how subtasks are defined/stored
    return null;
  }
}

// Subtask Service
class SubtaskService {
  private subtasks: Map<string, Subtask> = new Map();
  
  constructor(private eventBus: EventBus) {
    this.setupSubscriptions();
  }

  private setupSubscriptions() {
    this.eventBus.subscribe('StartSubtaskCommand', this.handleStartSubtask.bind(this));
    this.eventBus.subscribe('UserApproveSubtaskCommand', this.handleApproveSubtask.bind(this));
    this.eventBus.subscribe('SubtaskOutputGenerated', this.handleSubtaskOutput.bind(this));
  }

  private handleStartSubtask(event: Event) {
    const { taskId, subtaskId } = event.payload;
    
    // Check if subtask folder exists
    const subtaskExists = this.subtasks.has(subtaskId);
    
    if (!subtaskExists) {
      this.eventBus.publish({
        type: 'SubtaskInitialized',
        payload: { taskId, subtaskId }
      });
      
      this.eventBus.publish({
        type: 'SubtaskFolderCreated',
        payload: { taskId, subtaskId }
      });
    } else {
      this.eventBus.publish({
        type: 'SubtaskFolderLoaded',
        payload: { taskId, subtaskId }
      });
      
      this.eventBus.publish({
        type: 'SubtaskInitialized',
        payload: { taskId, subtaskId }
      });
    }

    // Create new chat for the subtask
    this.eventBus.publish({
      type: 'CreateChatCommand',
      payload: { taskId, subtaskId }
    });
    
    const subtask: Subtask = {
      id: subtaskId,
      taskId,
      status: 'in_progress'
    };
    
    this.subtasks.set(subtaskId, subtask);
  }

  private handleApproveSubtask(event: Event) {
    const { taskId, subtaskId } = event.payload;
    
    this.eventBus.publish({
      type: 'FinishSubtaskCommand',
      payload: { taskId, subtaskId }
    });
  }

  private handleSubtaskOutput(event: Event) {
    const { taskId, subtaskId, output } = event.payload;
    const subtask = this.subtasks.get(subtaskId);
    
    if (!subtask) return;
    
    subtask.output = output;
    subtask.status = 'completed';
    this.subtasks.set(subtaskId, subtask);
    
    this.eventBus.publish({
      type: 'SubtaskCompleted',
      payload: { 
        taskId,
        subtaskId,
        output 
      }
    });
  }
}

// Chat Service (basic implementation)
class ChatService {
  constructor(private eventBus: EventBus) {
    this.setupSubscriptions();
  }

  private setupSubscriptions() {
    this.eventBus.subscribe('CreateChatCommand', this.handleCreateChat.bind(this));
    this.eventBus.subscribe('UserSubmitMessageCommand', this.handleUserMessage.bind(this));
  }

  private handleCreateChat(event: Event) {
    const { taskId, subtaskId } = event.payload;
    
    this.eventBus.publish({
      type: 'ChatFileCreated',
      payload: { taskId, subtaskId }
    });
    
    this.eventBus.publish({
      type: 'ChatCreated',
      payload: { taskId, subtaskId }
    });
    
    this.eventBus.publish({
      type: 'AgentInitialized',
      payload: { taskId, subtaskId }
    });
    
    this.eventBus.publish({
      type: 'FirstPromptInitialized',
      payload: { taskId, subtaskId }
    });
  }

  private handleUserMessage(event: Event) {
    const { taskId, subtaskId, message } = event.payload;
    
    this.eventBus.publish({
      type: 'MessageReceived',
      payload: { taskId, subtaskId, message }
    });
    
    this.eventBus.publish({
      type: 'MessageSavedToFile',
      payload: { taskId, subtaskId, message }
    });
    
    this.eventBus.publish({
      type: 'ChatUpdated',
      payload: { taskId, subtaskId }
    });
  }
}

// Usage example
const eventBus: EventBus = {
  publish(event: Event) {
    console.log('Event published:', event);
  },
  subscribe(eventType: string, handler: (event: Event) => void) {
    console.log(`Subscribed to ${eventType}`);
  }
};

const taskService = new TaskService(eventBus);
const subtaskService = new SubtaskService(eventBus);
const chatService = new ChatService(eventBus);

// Start a new task
eventBus.publish({
  type: 'UserCreateTaskCommand',
  payload: { taskId: 'task_1' }
});