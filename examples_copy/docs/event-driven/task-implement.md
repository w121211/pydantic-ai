

### Task

**Create**

- Run step 0 -> output task.json
- 按照 task.json 來建立資料夾，並將 step 0 移動至 task 資料夾中（或是先創建一個暫存 task 資料夾，等完成後再來更名？）

**Run**

- 載入 task.lock 
  - 如果沒有 task.lock，查看是否有 step 0 folder
    - 有的話，嘗試從 step 0 成果來生成 task.json
    - 沒有的話，run step 0 -> output task.json
- 確認當前的執行狀態：執行到哪個 subtask
  - 從執行中的 subtask 繼續 -> run subtask
  - 若 task 已經執行完畢，則從 step 1 重新執行一遍

**Duplicate**

- cases
  - 直接 copy paste task folder
    - 好像也沒啥不可以...除了名稱沒有一致性以外

### Subtask

**討論**
- 可以單純藉由 subtask folder 來 init subtask 嗎？
  - 如果要可以的話，那就需要有一個類似 subtask.lock，在已經有 task.lock 的情況下我覺得暫時沒有必要增加複雜度
  - 有必要在不知道 task 的情況下單獨 init subtask 嗎？好像也沒必要...
- task.lock 中要存法哪些 subtask 資訊？因為用戶可以更動 subtask folder 裡的檔案，若同時存放在 task.lock 與 folder 中則會有資料不一致的可能
  - 存在 subtask folder
    - chats：藉此載入 subtask 所有的 chats
    - works
    - output：似乎也只能放在這裡
  - 存放在 task.lock：
    - subtask prompt：用此來自動跑，用戶可以修改
    - subtask status：目前的執行狀態，等候外部資料、等候用戶、執行中、已完成、錯誤...。
- Rerun
  - 原則上所有 subtask 都是自動執行（因為上一步驟完成後就會執行下一步）
  - rerun 就是重新執行這個步驟，流程跟 run 一樣，當 rerun 完後也跟 run 一樣會依照「新的輸出」來繼續執行後續步驟
  - 如果當前此步驟還在執行當中？
    - 強制停止當前的 run

**Run 流程**
- 檢查 subtask folder 是否已存在
  - 若沒存在，創建新的 subtask
- 從 subtask folder 讀取當前的執行進度
  - 載入 chats，完全依照「檔名」判斷 1. 是否為 chat 2. 時間戳
  - 如果有 output（可能發生於重新執行這個 subtask 的情況）？
    - 無視 output，重新執行
- 確認 input <- 要從哪取得？
- 依照 subtask 類型執行
  - Pure agent：執行 agent -> 發送 agent message event
  - Pure function：執行 function -> 發送 function run event
  - Human agent chat
    - Setup agent
    - Setup first prompt、input context  <- 來自 subtask props？
    - Agent completeChat -> 發送 agent message 訊號
    - （從 api 收到 user message 訊號）-> 更新 chat 
      - 如果用戶結束此對話（例如
      -> Agent completeChat（循環）
- Events
  - Subtask run start event
  - Subtask run finish event
- Handle events
  - 
- 發送 subtask 完成訊號（假設採用 event stream）



**New chat**
- 發生情況
  1. 從 subtask menu 開新對話
  2. 從原本的 chat 分叉
    - 例如原本是 a -> b -> c，用戶修改 b prompt (假設是 d)，這會直接創建一個新的 chat: a -> d -> e
  3. 用戶修改 work 後（例如加上 comment），然後直接開新對話
    - => 用戶操作：開新對話 -> 在 prompt 中導入編輯好的 work（拖曳、@等方式）、引用 prompt template（例如 @prompt:my-comments） -> 
  4. （討論中）當前對話太長，用戶基於「當前對話」開新對話
    - 需要有專屬按鈕、特殊處理
    - 需要嗎？有沒有辦法透過：新對話 -> 預設 subtask prompt（自動載入之類的）、引用（@） work & prompt 來滿足？
      - 這個需求基本上都是想在「最後的成果上」
  5. (特殊情況)全局允許開新對話嗎？
- 處理流程
  - 新對話（非分叉）
    - prompt：自動載入 subtask 內容，使用者可以微調這個內容（不會影響到全局，若要在 subtask scope 上調整 subtask prompt 則會影響到全局）
    - 
  - 分叉對話

**特殊情況**
- 可以開啟先前的 chat 然後繼續對話嗎？
  - 可以，chat 可以按照修改日期排序，繼續對話沒有什麼問題
- 對執行完的 subtask 開啟其中的 chat 然後繼續對話，可以嗎？
  - 沒什麼特別的問題


### Subtask without human

**討論**
- 在使用 agent 的情況下，會產生對話，但是

**情況**
- Pure function
- Pure agent

**處理**
- 即便

### Chat

**討論**
- 對話會結束嗎？例如當用戶 "APPROVE"、或是 pure agent, pure function 之類的？
  - 簡單一點的做法當然就是結束這個對話，只是在結束後如果去編輯其中的 prompt，可以分叉＆創建新對話
- 收到 message 後的處理？
  - 即時寫入檔案，要有檔案寫入保護
- 對話結束後的處理？
  - 確認 output ＆ 寫入至檔案
  - 發送對話結束 event
  - （？）對應的 subtask 接收到此 event 後，發送 subtask 結束 event
    - 或是直接都由對話這裡發送 event
  - task 收到後，執行下一個 subtask
- 如果我 copy 了對話檔案，會發生什麼事？
  - 不特別考慮，反正對話就以檔案形式存在


