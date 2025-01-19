# Task

1. 創建新任務流程：

```
UserCreateTaskCommand
  → TaskCreated
  → TaskFolderCreated
  → TaskInitialized
  → StartTaskCommand (自動執行 task)
```

2. 執行 Task 流程，包含 resume：

```
StartTaskCommand
  → TaskLoaded （讀取 task folder）
  → TaskInitialized（還是 task resumed？）
  → StartSubtaskCommand
```

# Subtask

1. 執行 Subtask 流程：

```
StartSubtaskCommand

  (Subtask service)
  (如果尚未執行過 subtask，沒有subtask folder)
  → SubtaskInitialized
  → SubtaskFolderCreated

  (如果有 subtask folder)
  → SubtaskFolderLoaded
  → SubtaskInitialized

  → CreateChatCommand
```

2. Subtask 完成流程（需審批）：

```
UserSubmitMessageCommand
  → MessageReceived
  → MessageSavedToFile
  → ChatUpdated
  → UserApproveSubtaskCommand（ approve 放在 user message 當中）

UserApproveSubtaskCommand
  → FinishSubtaskCommand

on UserApprovedWork
→ CompleteSubtaskCommand

CompleteSubtaskCommand
→ SubtaskOutputGenerated
  (SubtaskService)
  → SubtaskCompleted
  → NextSubtaskTriggered
    （task service: 取得 next subtask, emit StartSubtaskCommand）
    → StartSubtaskCommand (觸發下一個 subtask 的流程)
```

- NextSubtaskTriggered vs NextSubtaskRequested
  - 如果下一個子任務是自動觸發且必定執行的，使用 Triggered 更合適 -> 確定的、自動的狀態轉換
  - 如果存在條件判斷或可能被拒絕的情況，使用 Requested 更合適 -> 請求或意圖
- 如果 User 拒絕 agent 結果，就直接送需要修改什麼的訊息（不批准），延續 chat

3. Subtask 完成流程（無需審批）：

```
SubtaskOutputGenerated
→ SubtaskCompleted
→ NextSubtaskTriggered
    → StartSubtaskCommand
```

# Chat

1. StartNewChatCommand

```
StartNewChatCommand
→ ChatFileCreated
→ ChatCreated (包含 initialize 等)
→ AgentInitialized （依照 subtask 的設定）
→ FirstPromptInitialized（依照 subtask 的設定（包含 input）自動產生第一個 prompt）
→ SubmitPromptCommand (或是 PromptMessageReceived)
  → MessageSavedToFile
  → ChatUpdated
  → AgentProcessedMessage
  → AgentResponseGenerated
  → MessageSavedToFile
  → ChatUpdated
```

2. UserOpenChatCommand

- 無須考慮離開原本 chat 的情況，因為 chat 都是即時被儲存的，即便離開也不會影響原本正在儲存中的 chat

```
UserOpenChatCommand
→ ChatFileLoaded
→ ChatReady
```

3. UserSubmitMessageCommand

```
UserSubmitMessageCommand
→ MessageReceived
→ MessageSavedToFile
→ ChatUpdated
(if user approved the work)
→ UserApprovedOutputWork
(if not, continue)
→ AgentProcessedMessage
→ AgentResponseGenerated
→ MessageSavedToFile
→ ChatUpdated
```

on UserApprovedOutputWork

```
UserApprovedOutputWork
→ CompleteSubtaskCOmmand
```
