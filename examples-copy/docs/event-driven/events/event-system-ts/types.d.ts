export type Task = {
  id: string;
  seqNumber: number;
  title: string;
  status: "CREATED" | "INITIALIZED" | "IN_PROGRESS" | "COMPLETED";
  currentSubtaskId?: string;
  subtasks: Subtask[];
  folderPath: string;
  config: any;
  createdAt: number;
  updatedAt: number;
};

/**
 * Remarks:
 * - No need subtaskType. It can be inferred from team.
 */
export type Subtask = {
  id: string;
  taskId: string;
  seqNumber: number; // Step 1, 2, 3, etc for ordering
  title: string; // Short, concise description for humans
  status: "pending" | "in_progress" | "completed";
  description: string; // Detailed description
  team: {
    agent: "@assistant" | "@function_executor";
    human: "@user" | null; // "@user" can also represent the approval required
  };
  // inputType?: "string" | "json"; // e.g. "string", "json", etc
  // outputType?: "string" | "json"; // e.g. "string", "json", etc
  inputType: string; // Only string for now
  outputType: string; // Only string for now
};

export type Message = {
  id: string;
  role: "@assistant" | "@user" | "@function_executor";
  content: string;
  timestamp: number;
  metadata?: {
    subtaskId?: string;
    taskId?: string;
    functionCalls?: any[];
    isPrompt?: true;
    // Additional metadata fields can be added as needed
  };
};

export type Chat = {
  id: string;
  taskId: string;

  // TO BE DISCUSSED: Should we allow chats without subtasks, i.e. task-wide chats?
  //
  subtaskId: string;
  messages: Message[];
  status: "active" | "closed";
  createdAt: number;
  updatedAt: number;
  metadata?: {
    title?: string;
    summary?: string;
    tags?: string[];
    // Additional metadata fields can be added as needed
  };
};

// Events

export interface BaseEvent {
  type: string;
  timestamp: number;
  // correlationId: string;
}

// export interface BaseCommand {
//   type: string;
//   timestamp: number;
//   // correlationId: string;
// }

// Task Events

export interface StartTaskCommand extends BaseEvent {
  type: "StartTaskCommand";
  taskId: string;
}

export interface CreateTaskCommand extends BaseEvent {
  type: "CreateTaskCommand";
  taskName: string;
  taskConfig: any;
}

export interface TaskCreatedEvent extends BaseEvent {
  type: "TaskCreatedEvent";
  taskId: string;
  taskName: string;
  config: any;
}

export interface TaskFolderCreatedEvent extends BaseEvent {
  type: "TaskFolderCreatedEvent";
  taskId: string;
  folderPath: string;
}

export interface TaskInitializedEvent extends BaseEvent {
  type: "TaskInitializedEvent";
  taskId: string;
  initialState: any;
}

export interface TaskLoadedEvent extends BaseEvent {
  type: "TaskLoadedEvent";
  taskId: string;
  taskState: Task;
}

// Subtask Events

export interface StartSubtaskCommand extends BaseEvent {
  type: "StartSubtaskCommand";
  taskId: string;
  subtaskId: string;
}

export interface CompleteSubtaskCommand extends BaseEvent {
  type: "CompleteSubtaskCommand";
  taskId: string;
  subtaskId: string;
  // output: string | Record<string, unknown>;
  output: string; // For simplicity, we are using string output
  requiresApproval: boolean;
}

export interface SubtaskInitializedEvent extends BaseEvent {
  type: "SubtaskInitializedEvent";
  taskId: string;
  subtaskId: string;
  subtaskType: string;
}

/**
 * Remarks:
 * - Output will not be included in the event. It will be saved in the subtask folder.
 */
export interface SubtaskCompletedEvent extends BaseEvent {
  type: "SubtaskCompletedEvent";
  taskId: string;
  subtaskId: string;
}

export interface SubtaskStartedEvent extends BaseEvent {
  type: "SubtaskStartedEvent";
  taskId: string;
  subtaskId: string;
  input?: any;
}

export interface SubtaskPausedEvent extends BaseEvent {
  type: "SubtaskPausedEvent";
  taskId: string;
  subtaskId: string;
}

export interface SubtaskUpdatedEvent extends BaseEvent {
  type: "SubtaskUpdatedEvent";
  taskId: string;
  subtaskId: string;
  status: "pending" | "in_progress" | "completed";
}

export interface SubtaskFolderCreatedEvent extends BaseEvent {
  type: "SubtaskFolderCreatedEvent";
  taskId: string;
  subtaskId: string;
  folderPath: string;
}

export interface NextSubtaskTriggeredEvent extends BaseEvent {
  type: "NextSubtaskTriggeredEvent";
  taskId: string;
  currentSubtaskId: string;
}

// Chat Events

export interface StartNewChatCommand extends BaseEvent {
  type: "StartNewChatCommand";
  taskId: string;
  subtaskId: string;
  metadata?: {
    title?: string;
    tags?: string[];
  };
}

export interface UserSubmitMessageCommand extends BaseEvent {
  type: "UserSubmitMessageCommand";
  chatId: string;
  content: string;
}

export interface SubmitInitialPromptCommand extends BaseEvent {
  type: "SubmitInitialPromptCommand";
  chatId: string;
  prompt: string;
}

export interface ChatCreatedEvent extends BaseEvent {
  type: "ChatCreatedEvent";
  taskId: string;
  subtaskId: string;
  chatId: string;
}

export interface ChatFileCreatedEvent extends BaseEvent {
  type: "ChatFileCreatedEvent";
  taskId: string;
  subtaskId: string;
  chatId: string;
  filePath: string;
}

export interface MessageReceivedEvent extends BaseEvent {
  type: "MessageReceivedEvent";
  chatId: string;
  message: Message;
}

export interface MessageSavedToChatFileEvent extends BaseEvent {
  type: "MessageSavedToChatFileEvent";
  chatId: string;
  messageId: string;
  filePath: string;
}

export interface ChatUpdatedEvent extends BaseEvent {
  type: "ChatUpdatedEvent";
  chatId: string;
  lastMessageId: string;
}

export interface AgentProcessedMessageEvent extends BaseEvent {
  type: "AgentProcessedMessageEvent";
  chatId: string;
  messageId: string;
}

export interface AgentResponseGeneratedEvent extends BaseEvent {
  type: "AgentResponseGeneratedEvent";
  chatId: string;
  response: Message;
}
