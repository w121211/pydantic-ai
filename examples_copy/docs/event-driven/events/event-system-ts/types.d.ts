export type Task = {
  id: string;
  title: string;
  status: "CREATED" | "INITIALIZED" | "IN_PROGRESS" | "COMPLETED";
  currentSubtaskId?: string;
  subtasks: Subtask[];
  // folderPath?: string;
  config: any;
  createdAt: number;
  updatedAt: number;
};

export type Subtask = {
  id: string;
  taskId: string;
  // This is currently satisfy to represent different subtask types, i.e. "pure-function", "pure-agent", "agent-human"
  team: {
    agent: "@assistant" | "@function_executor";
    human: "@user" | null; // "@user" can also represent the approval required
  };
  stepNumber: number; // 1, 2, 3, etc for ordering
  title: string; // Short, concise description for humans
  description: string; // Detailed description
  status: "pending" | "in_progress" | "completed";
  output?: any;
  inputType?: "string" | "json"; // e.g. "string", "json", etc
  outputType?: "string" | "json"; // e.g. "string", "json", etc
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
