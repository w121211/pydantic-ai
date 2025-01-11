// Types
interface EventBus {
  emit(event: Event): void;
  subscribe(eventType: string, handler: (event: Event) => void): void;
}

interface Event {
  type: string;
  payload: any;
}

// Base Events
interface TaskEvent extends Event {
  payload: {
    taskId: string;
  };
}

interface SubtaskEvent extends Event {
  payload: {
    taskId: string;
    subtaskId: string;
  };
}

interface ChatEvent extends Event {
  payload: {
    taskId: string;
    subtaskId: string;
    chatId: string;
  };
}

// Task Service
class TaskService {
  constructor(private eventBus: EventBus) {
    this.setupSubscriptions();
  }

  private setupSubscriptions() {
    this.eventBus.subscribe('UserCreateTaskCommand', this.handleCreateTask.bind(this));
    this.eventBus.subscribe('StartTaskCommand', this.handleStartTask.bind(this));
    this.eventBus.subscribe('SubtaskCompleted', this.handleSubtaskCompleted.bind(this));
  }

  private async handleCreateTask(event: Event) {
    const taskId = crypto.randomUUID();
    
    // Create task folder and initialize
    this.eventBus.emit({
      type: 'TaskCreated',
      payload: { taskId }
    });

    this.eventBus.emit({
      type: 'TaskFolderCreated',
      payload: { taskId }
    });

    this.eventBus.emit({
      type: 'TaskInitialized',
      payload: { taskId }
    });

    // Automatically start the task
    this.eventBus.emit({
      type: 'StartTaskCommand',
      payload: { taskId }
    });
  }

  private async handleStartTask(event: TaskEvent) {
    const { taskId } = event.payload;

    this.eventBus.emit({
      type: 'TaskLoaded',
      payload: { taskId }
    });

    this.eventBus.emit({
      type: 'TaskInitialized',
      payload: { taskId }
    });

    // Start first subtask
    this.eventBus.emit({
      type: 'StartSubtaskCommand',
      payload: { 
        taskId,
        subtaskId: crypto.randomUUID()
      }
    });
  }

  private async handleSubtaskCompleted(event: SubtaskEvent) {
    const { taskId, subtaskId } = event.payload;
    
    // Determine next subtask
    const nextSubtaskId = await this.determineNextSubtask(taskId, subtaskId);
    
    if (nextSubtaskId) {
      this.eventBus.emit({
        type: 'StartSubtaskCommand',
        payload: { 
          taskId,
          subtaskId: nextSubtaskId
        }
      });
    }
  }

  private async determineNextSubtask(taskId: string, currentSubtaskId: string): Promise<string | null> {
    // Implementation to determine next subtask
    return null;
  }
}

// Subtask Service
class SubtaskService {
  constructor(private eventBus: EventBus) {
    this.setupSubscriptions();
  }

  private setupSubscriptions() {
    this.eventBus.subscribe('StartSubtaskCommand', this.handleStartSubtask.bind(this));
    this.eventBus.subscribe('UserApproveSubtaskCommand', this.handleApproveSubtask.bind(this));
    this.eventBus.subscribe('FinishSubtaskCommand', this.handleFinishSubtask.bind(this));
  }

  private async handleStartSubtask(event: SubtaskEvent) {
    const { taskId, subtaskId } = event.payload;

    if (!await this.hasSubtaskFolder(taskId, subtaskId)) {
      this.eventBus.emit({
        type: 'SubtaskInitialized',
        payload: { taskId, subtaskId }
      });

      this.eventBus.emit({
        type: 'SubtaskFolderCreated',
        payload: { taskId, subtaskId }
      });
    } else {
      this.eventBus.emit({
        type: 'SubtaskFolderLoaded',
        payload: { taskId, subtaskId }
      });

      this.eventBus.emit({
        type: 'SubtaskInitialized',
        payload: { taskId, subtaskId }
      });
    }

    // Create chat for the subtask
    this.eventBus.emit({
      type: 'CreateChatCommand',
      payload: { 
        taskId,
        subtaskId,
        chatId: crypto.randomUUID()
      }
    });
  }

  private async handleApproveSubtask(event: SubtaskEvent) {
    const { taskId, subtaskId } = event.payload;
    
    this.eventBus.emit({
      type: 'FinishSubtaskCommand',
      payload: { taskId, subtaskId }
    });
  }

  private async handleFinishSubtask(event: SubtaskEvent) {
    const { taskId, subtaskId } = event.payload;
    
    this.eventBus.emit({
      type: 'SubtaskOutputGenerated',
      payload: { taskId, subtaskId }
    });

    this.eventBus.emit({
      type: 'SubtaskCompleted',
      payload: { taskId, subtaskId }
    });

    this.eventBus.emit({
      type: 'NextSubtaskTriggered',
      payload: { taskId, subtaskId }
    });
  }

  private async hasSubtaskFolder(taskId: string, subtaskId: string): Promise<boolean> {
    // Implementation to check if subtask folder exists
    return false;
  }
}

// Chat Service
class ChatService {
  constructor(private eventBus: EventBus) {
    this.setupSubscriptions();
  }

  private setupSubscriptions() {
    this.eventBus.subscribe('CreateChatCommand', this.handleCreateChat.bind(this));
    this.eventBus.subscribe('UserSubmitMessageCommand', this.handleUserMessage.bind(this));
  }

  private async handleCreateChat(event: ChatEvent) {
    const { taskId, subtaskId, chatId } = event.payload;

    this.eventBus.emit({
      type: 'ChatFileCreated',
      payload: { taskId, subtaskId, chatId }
    });

    this.eventBus.emit({
      type: 'ChatCreated',
      payload: { taskId, subtaskId, chatId }
    });

    this.eventBus.emit({
      type: 'AgentInitialized',
      payload: { taskId, subtaskId, chatId }
    });

    this.eventBus.emit({
      type: 'FirstPromptInitialized',
      payload: { taskId, subtaskId, chatId }
    });

    this.eventBus.emit({
      type: 'SubmitPromptCommand',
      payload: { taskId, subtaskId, chatId }
    });
  }

  private async handleUserMessage(event: ChatEvent & { message: string }) {
    const { taskId, subtaskId, chatId, message } = event.payload;

    this.eventBus.emit({
      type: 'MessageReceived',
      payload: { taskId, subtaskId, chatId, message }
    });

    this.eventBus.emit({
      type: 'MessageSavedToFile',
      payload: { taskId, subtaskId, chatId, message }
    });

    this.eventBus.emit({
      type: 'ChatUpdated',
      payload: { taskId, subtaskId, chatId }
    });

    this.eventBus.emit({
      type: 'AgentProcessedMessage',
      payload: { taskId, subtaskId, chatId, message }
    });

    // Handle agent response
    const agentResponse = await this.generateAgentResponse(message);
    
    this.eventBus.emit({
      type: 'AgentResponseGenerated',
      payload: { 
        taskId, 
        subtaskId, 
        chatId,
        message: agentResponse 
      }
    });

    this.eventBus.emit({
      type: 'MessageSavedToFile',
      payload: { 
        taskId, 
        subtaskId, 
        chatId,
        message: agentResponse 
      }
    });

    this.eventBus.emit({
      type: 'ChatUpdated',
      payload: { taskId, subtaskId, chatId }
    });
  }

  private async generateAgentResponse(message: string): Promise<string> {
    // Implementation to generate agent response
    return '';
  }
}

// Usage example
const eventBus: EventBus = {
  emit: (event: Event) => {
    console.log('Event emitted:', event.type, event.payload);
  },
  subscribe: (eventType: string, handler: (event: Event) => void) => {
    console.log('Subscribed to:', eventType);
  }
};

const taskService = new TaskService(eventBus);
const subtaskService = new SubtaskService(eventBus);
const chatService = new ChatService(eventBus);

// Start a new task
eventBus.emit({
  type: 'UserCreateTaskCommand',
  payload: {}
});
