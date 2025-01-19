# API Design Document

## Base URL
```
/api/v1
```

## Task APIs

### Create Task
- **Endpoint**: `POST /tasks`
- **Description**: 創建新任務
- **Request Body**:
  ```json
  {
    "taskType": "string",
    "input": {
      // task specific input
    },
    "config": {
      // optional task configuration
    }
  }
  ```
- **Response**:
  ```json
  {
    "taskId": "string",
    "status": "created",
    "createdAt": "timestamp"
  }
  ```
- **Events Generated**:
  - TaskCreated
  - TaskFolderCreated
  - TaskInitialized

### Start Task
- **Endpoint**: `POST /tasks/{taskId}/start`
- **Description**: 開始執行任務
- **Response**:
  ```json
  {
    "taskId": "string",
    "status": "running",
    "startedAt": "timestamp"
  }
  ```
- **Events Generated**:
  - TaskLoaded
  - TaskInitialized/TaskResumed
  - StartSubtaskCommand

### Get Task Status
- **Endpoint**: `GET /tasks/{taskId}`
- **Description**: 獲取任務狀態和進度
- **Response**:
  ```json
  {
    "taskId": "string",
    "status": "string",
    "progress": {
      "current": "number",
      "total": "number"
    },
    "currentSubtask": {
      "id": "string",
      "type": "string",
      "status": "string"
    }
  }
  ```

## Subtask APIs

### Get Current Subtask
- **Endpoint**: `GET /tasks/{taskId}/subtasks/current`
- **Description**: 獲取當前執行中的子任務信息
- **Response**:
  ```json
  {
    "subtaskId": "string",
    "type": "string",
    "status": "string",
    "chatId": "string",
    "requiresApproval": "boolean"
  }
  ```

### Approve Subtask
- **Endpoint**: `POST /tasks/{taskId}/subtasks/{subtaskId}/approve`
- **Description**: 批准子任務完成
- **Response**:
  ```json
  {
    "subtaskId": "string",
    "status": "completed",
    "nextSubtaskId": "string"
  }
  ```
- **Events Generated**:
  - UserApprovedWork
  - SubtaskCompleted
  - NextSubtaskTriggered

## Chat APIs

### Create Chat
- **Endpoint**: `POST /chats`
- **Description**: 創建新的對話
- **Request Body**:
  ```json
  {
    "taskId": "string",
    "subtaskId": "string"
  }
  ```
- **Response**:
  ```json
  {
    "chatId": "string",
    "status": "initialized",
    "firstPrompt": "string"
  }
  ```
- **Events Generated**:
  - ChatFileCreated
  - ChatCreated
  - AgentInitialized
  - FirstPromptInitialized

### Get Chat
- **Endpoint**: `GET /chats/{chatId}`
- **Description**: 獲取對話內容
- **Response**:
  ```json
  {
    "chatId": "string",
    "messages": [
      {
        "id": "string",
        "role": "user|agent",
        "content": "string",
        "timestamp": "string"
      }
    ]
  }
  ```
- **Events Generated**:
  - ChatFileLoaded
  - ChatReady

### Send Message
- **Endpoint**: `POST /chats/{chatId}/messages`
- **Description**: 發送新消息
- **Request Body**:
  ```json
  {
    "content": "string",
    "metadata": {
      "approveWork": "boolean",  // optional, for approval
      "feedback": "string"       // optional, for rejection
    }
  }
  ```
- **Response**:
  ```json
  {
    "messageId": "string",
    "status": "received"
  }
  ```
- **Events Generated**:
  - MessageReceived
  - MessageSavedToFile
  - ChatUpdated
  - AgentProcessedMessage (if not approval)
  - UserApprovedWork (if approval)

## WebSocket Events

### Connection
- **Endpoint**: `ws://[base-url]/ws`
- **Description**: 用於實時接收事件更新

### Event Types
1. Task Events:
   ```json
   {
     "type": "task",
     "event": "TaskCreated|TaskCompleted|...",
     "taskId": "string",
     "data": {}
   }
   ```

2. Subtask Events:
   ```json
   {
     "type": "subtask",
     "event": "SubtaskInitialized|SubtaskCompleted|...",
     "taskId": "string",
     "subtaskId": "string",
     "data": {}
   }
   ```

3. Chat Events:
   ```json
   {
     "type": "chat",
     "event": "MessageReceived|ChatUpdated|...",
     "chatId": "string",
     "data": {}
   }
   ```

## 前端狀態管理建議

### Task Store
```typescript
interface TaskStore {
  currentTask: {
    id: string;
    status: string;
    currentSubtask?: SubTask;
  };
  loading: boolean;
  error?: string;
}
```

### Chat Store
```typescript
interface ChatStore {
  currentChat: {
    id: string;
    messages: Message[];
    status: string;
  };
  loading: boolean;
  error?: string;
}
```

### WebSocket 連接管理
```typescript
class WebSocketManager {
  connect(taskId: string) {
    // 建立 WebSocket 連接
  }
  
  subscribe(eventType: string, callback: (event: any) => void) {
    // 訂閱特定類型的事件
  }
  
  unsubscribe(eventType: string) {
    // 取消訂閱
  }
}
```
