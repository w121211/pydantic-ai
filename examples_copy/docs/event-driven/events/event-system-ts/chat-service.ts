import { IEventBus } from "./event-system-0";
import { ChatStore } from "./stores-0";
import { Chat, Message } from "./types";
import { promises as fs } from "fs";
import * as path from "path";

class ChatService {
  private workspace: string = "tasks";

  constructor(private eventBus: IEventBus, private chatStore: ChatStore) {
    // Subscribe to commands
    this.eventBus.subscribe<StartNewChatCommand>(
      "StartNewChatCommand",
      this.handleCreateChat.bind(this)
    );

    this.eventBus.subscribe<UserSubmitMessageCommand>(
      "UserSubmitMessageCommand",
      this.handleUserMessage.bind(this)
    );

    this.eventBus.subscribe<SubmitInitialPromptCommand>(
      "SubmitInitialPromptCommand",
      this.handlePromptMessage.bind(this)
    );
  }

  private async handleStartNewChatCommand(
    command: StartNewChatCommand
  ): Promise<void> {
    const { taskId, subtaskId, metadata, correlationId } = command;
    const chatId = this.generateChatId();

    // Initialize chat object
    const chat: Chat = {
      id: chatId,
      taskId,
      subtaskId,
      messages: [],
      status: "active",
      createdAt: Date.now(),
      updatedAt: Date.now(),
      metadata,
    };
    this.chatStore.add(chat);

    // Create chat file
    await this.createChatFile(taskId, subtaskId, chatId);

    await this.eventBus.publish<ChatCreatedEvent>({
      type: "ChatCreated",
      taskId,
      subtaskId,
      chatId,
      timestamp: Date.now(),
      correlationId,
    });

    // Initialize first prompt based on subtask configuration
    const prompt = await this.generateInitialPrompt(taskId, subtaskId);
    const message: Message = {
      id: this.generateMessageId(),
      role: "@user", // This message is automatically sent by the system on behalf of user.
      content: prompt,
      timestamp: Date.now(),
      metadata: {
        taskId: chat.taskId,
        subtaskId: chat.subtaskId,
        isPrompt: true,
      },
    };

    // A trick to directly process the message. No need to wait.
    this.onMessageReceived(chat, message, correlationId);

    await this.eventBus.publish<ChatStartedEvent>({
      type: "ChatStarted",
      taskId,
      subtaskId,
      chatId,
      timestamp: Date.now(),
      correlationId,
    });
  }

  private async handleUserSubmitMessageCommand(
    command: UserSubmitMessageCommand
  ): Promise<void> {
    const { chatId, content, correlationId } = command;
    const chat = this.chats.get(chatId);

    if (!chat) {
      throw new Error(`Chat ${chatId} not found`);
    }

    const message: Message = {
      id: this.generateMessageId(),
      role: "@user",
      content,
      timestamp: Date.now(),
      metadata: {
        taskId: chat.taskId,
        subtaskId: chat.subtaskId,
      },
    };

    // 1. Save message to memory
    chat.messages.push(message);
    chat.updatedAt = Date.now();

    // 2. Emit MessageReceived event
    await this.eventBus.publish<MessageReceivedEvent>({
      type: "MessageReceived",
      chatId,
      message,
      timestamp: Date.now(),
      correlationId,
    });

    // 3. Save message to file
    const filePath = await this.saveMessageToFile(chat, message);

    // 4. Emit MessageSavedToFile event
    await this.eventBus.publish<MessageSavedToFileEvent>({
      type: "MessageSavedToFile",
      chatId,
      messageId: message.id,
      filePath,
      timestamp: Date.now(),
      correlationId,
    });

    // 5. Update chat status
    await this.eventBus.publish<ChatUpdatedEvent>({
      type: "ChatUpdated",
      chatId,
      lastMessageId: message.id,
      timestamp: Date.now(),
      correlationId,
    });

    // 6. Process message with agent
    await this.processMessageWithAgent(chat, message, correlationId);
  }

  private async onMessageReceived(
    chat: Chat,
    message: Message,
    correlationId: string
  ): Promise<void> {
    /**
     * Steps:
     * 1. Add to chat's meesage
     * 2. Update chat file
     * 3. If is agent message, do nothing and return
     * 3. If is user message
     *   - If has 'APPROVE' -> process the approval & generate the output -> output command
     *   - If not, generate the agent response.
     */

    chat.messages.push(message);

    // Save message to file
    const filePath = await this.saveMessageToChatFile(chat, message);

    // Should we emit here or emit at saveMessageToChatFile(...)
    await this.eventBus.publish<MessageSavedToChatFileEvent>({
      type: "MessageSavedToChatFileEvent",
      chatId,
      messageId: message.id,
      filePath,
      timestamp: Date.now(),
      correlationId,
    });

    // Process user message
    if (message.role === "@user") {
      // When user approve the work
      if (message.content.includes("APPROVE")) {
        await this.eventBus.publish<UserApprovedWorkEvent>({
          type: "UserApprovedWorkEvent",
          chatId: chat.id,
          timestamp: Date.now(),
          correlationId,
        });
        return;
      }

      // Continue to generate the agent response
      const response = await this.generateAgentResponse(
        chat,
        message,
        correlationId
      );
      await this.onMessageReceived(chat, response, correlationId);
    }
  }

  private async createChatFile() {
    // TODO
  }

  private async generateAgentResponse(
    chat: Chat,
    prompt: Message, // The last message of the chat
    correlationId: string
  ): Promise<Message> {
    // TODO: Generate agent response (this would be implemented by the agent service)
    const response: Message = {
      id: this.generateMessageId(),
      role: "@assistant",
      content: "Agent response placeholder",
      timestamp: Date.now(),
      metadata: {
        taskId: chat.taskId,
        subtaskId: chat.subtaskId,
      },
    };

    // Emit AgentResponseGenerated event
    await this.eventBus.publish<AgentResponseGeneratedEvent>({
      type: "AgentResponseGenerated",
      chatId: chat.id,
      response,
      timestamp: Date.now(),
      correlationId,
    });

    return response;
  }

  private getChatFilerPath(
    taskId: string,
    subtaskId: string,
    chatId: string
  ): string {
    return path.join(this.workspace, taskId, subtaskId, `chat_${chatId}.json`);
  }

  private async createChatFile(
    taskId: string,
    subtaskId: string,
    chatId: string
  ): Promise<void> {
    // await fs.mkdir(folderPath, { recursive: true });
    await fs.mkdir(this.getChatFilerPath(taskId, subtaskId, chatId), {
      recursive: true,
    });
  }

  private async saveMessageToChatFile(
    chat: Chat,
    message: Message
  ): Promise<string> {
    const { taskId, subtaskId, id: chatId } = chat;
    const filePath = this.getChatFilerPath(taskId, subtaskId, chatId);
    await fs.writeFile(filePath, JSON.stringify(message, null, 2));
    return filePath;
  }

  private async generateInitialPrompt(
    taskId: string,
    subtaskId: string
  ): Promise<string> {
    // TODO: This would be implemented based on the subtask configuration
    return "This is a sample initial prompt";
  }

  private generateChatId(): string {
    return `chat_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

export default ChatService;
