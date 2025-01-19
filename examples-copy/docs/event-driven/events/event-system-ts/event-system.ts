import { BaseCommand, BaseEvent } from "./types";

// Event Bus Interface
export interface IEventBus {
  publish<T extends BaseEvent>(event: T): Promise<void>;
  subscribe<T extends BaseEvent>(
    eventType: string,
    handler: EventHandler<T>
  ): void;
  subscribeSync<T extends BaseEvent>(
    eventType: string,
    handler: SyncEventHandler<T>
  ): void;
}

// Handler types
type EventHandler<T extends BaseEvent> = (event: T) => Promise<void>;
type SyncEventHandler<T extends BaseEvent> = (event: T) => void;

// Task Events
interface TaskCreatedEvent extends BaseEvent {
  type: "TaskCreated";
  taskId: string;
  taskName: string;
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

// Task Commands
interface CreateTaskCommand extends BaseCommand {
  type: "UserCreateTaskCommand";
  taskName: string;
  taskConfig: any;
}

interface StartTaskCommand extends BaseCommand {
  type: "StartTaskCommand";
  taskId: string;
}

// Chat Events
interface MessageReceivedEvent extends BaseEvent {
  type: "MessageReceived";
  chatId: string;
  messageId: string;
  content: string;
  sender: string;
}

interface ChatUpdatedEvent extends BaseEvent {
  type: "ChatUpdated";
  chatId: string;
  lastMessageId: string;
  updateType: "NewMessage" | "MessageSaved" | "AgentResponse";
}

// Chat Service
class ChatService {
  constructor(private eventBus: IEventBus) {
    this.eventBus.subscribe<CreateChatCommand>(
      "CreateChatCommand",
      this.handleCreateChat.bind(this)
    );

    this.eventBus.subscribe<UserSubmitMessageCommand>(
      "UserSubmitMessageCommand",
      this.handleUserMessage.bind(this)
    );
  }

  private async handleCreateChat(command: CreateChatCommand): Promise<void> {
    const chatId = crypto.randomUUID();

    await this.eventBus.publish<ChatFileCreatedEvent>({
      type: "ChatFileCreated",
      chatId,
      taskId: command.taskId,
      subtaskId: command.subtaskId,
      filePath: `/tasks/${command.taskId}/subtasks/${command.subtaskId}/chat.json`,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    await this.eventBus.publish<ChatCreatedEvent>({
      type: "ChatCreated",
      chatId,
      taskId: command.taskId,
      subtaskId: command.subtaskId,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    await this.eventBus.publish<AgentInitializedEvent>({
      type: "AgentInitialized",
      chatId,
      agentConfig: await this.getSubtaskAgentConfig(command.subtaskId),
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    const firstPrompt = await this.generateFirstPrompt(command.subtaskId);
    await this.eventBus.publish<FirstPromptInitializedEvent>({
      type: "FirstPromptInitialized",
      chatId,
      prompt: firstPrompt,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    await this.eventBus.publish<SubmitPromptCommand>({
      type: "SubmitPromptCommand",
      chatId,
      messageContent: firstPrompt,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });
  }

  private async handleUserMessage(
    command: UserSubmitMessageCommand
  ): Promise<void> {
    const messageId = crypto.randomUUID();

    await this.eventBus.publish<MessageReceivedEvent>({
      type: "MessageReceived",
      chatId: command.chatId,
      messageId,
      content: command.content,
      sender: "user",
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    await this.eventBus.publish<MessageSavedToFileEvent>({
      type: "MessageSavedToFile",
      chatId: command.chatId,
      messageId,
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    await this.eventBus.publish<ChatUpdatedEvent>({
      type: "ChatUpdated",
      chatId: command.chatId,
      lastMessageId: messageId,
      updateType: "NewMessage",
      timestamp: Date.now(),
      correlationId: command.correlationId,
    });

    // Check for approval command in message
    if (this.isApprovalMessage(command.content)) {
      await this.eventBus.publish<UserApproveSubtaskCommand>({
        type: "UserApproveSubtaskCommand",
        chatId: command.chatId,
        subtaskId: command.subtaskId!,
        timestamp: Date.now(),
        correlationId: command.correlationId,
      });
    } else {
      // Process normal message with agent
      await this.processMessageWithAgent(
        command.chatId,
        messageId,
        command.correlationId
      );
    }
  }

  private async processMessageWithAgent(
    chatId: string,
    messageId: string,
    correlationId: string
  ): Promise<void> {
    await this.eventBus.publish<AgentProcessedMessageEvent>({
      type: "AgentProcessedMessage",
      chatId,
      messageId,
      timestamp: Date.now(),
      correlationId,
    });

    const agentResponse = await this.generateAgentResponse(chatId, messageId);
    const responseId = crypto.randomUUID();

    await this.eventBus.publish<AgentResponseGeneratedEvent>({
      type: "AgentResponseGenerated",
      chatId,
      messageId: responseId,
      content: agentResponse,
      timestamp: Date.now(),
      correlationId,
    });

    await this.eventBus.publish<MessageSavedToFileEvent>({
      type: "MessageSavedToFile",
      chatId,
      messageId: responseId,
      timestamp: Date.now(),
      correlationId,
    });

    await this.eventBus.publish<ChatUpdatedEvent>({
      type: "ChatUpdated",
      chatId,
      lastMessageId: responseId,
      updateType: "AgentResponse",
      timestamp: Date.now(),
      correlationId,
    });
  }

  private async getSubtaskAgentConfig(subtaskId: string): Promise<any> {
    // Implementation to get agent configuration
    return {};
  }

  private async generateFirstPrompt(subtaskId: string): Promise<string> {
    // Implementation to generate first prompt
    return "";
  }

  private async generateAgentResponse(
    chatId: string,
    messageId: string
  ): Promise<string> {
    // Implementation to generate agent response
    return "";
  }

  private isApprovalMessage(content: string): boolean {
    // Implementation to check if message contains approval
    return false;
  }
}
