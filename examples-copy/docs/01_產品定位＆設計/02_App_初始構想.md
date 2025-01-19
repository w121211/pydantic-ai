# App 初始構想

### 我希望他是一個…

- 類似一個每日工作管理工具，讓我瀏覽目前各項工作的進展、新增工作、哪些需要我審核的（審核過後就可以繼續執行後續的步驟），我就像是一個管理者的角色，管理一個專案 team，只是裡面的成員大部分都是 AI agents
- 一個每天早上開始工作就會打開的東西，我從工作管理表中就可以知道，今天有哪些工作、要做哪些、哪些需要我審核、哪些工作需要新增、調整、或是暫停等等
- AI 會幫忙我管理、監督專案、各項工作進度，例如
  - 自動增加例行性的 tasks
  - 當一個 task 有延誤時，自動排程、提醒優先順序、暫緩後續的 tasks 等等
  - 若當目前的 task 規劃時間過長、過短，會按照實際執行狀況來給予調整
- 開一個新工作、新專案時，我只要給予一個簡單的指示（例如做一個影片、頻道），AI 會幫我規劃具體的工作步驟、細節，自動執行，我在過程中檢視、給予意見或直接參與編輯製作
- 有些工作會需要由我自己做，AI 因為能力受限無法做到，例如編輯影片、寫 code 等等，需要人工完成，檢視審核工作成果也需要我，當然 AI 可以一起參與檢視
- 單純的工作啟動器：有些不一定是要專案性質，就只是一次性的工作，例如寫一個 email，我只要給與簡單命命，就會自動適配 flow & 執行（當然其實較為簡單的工作可能直接用 ChatGPT 的聊天網頁就好了）
- 用這個來管理工作有個好處是，他會記錄每項工作的執行情況＆進展，幫我寫工作日誌、git commit message，做成專案進度管理報告等等
- 他就是在告訴我說今天工作有哪些、哪些 AI 可以去執行、哪些

### 基本想法、設計

- 專注在 MVP，快速迭代、開發產品，管理、監督、執行 tasks
- 盡量 agnostic，因為每個人都有自己慣用的專案管理工具（像我是用 notion），若能直接與各種管理工具接軌是最好的
- 基本上就是儲存 tasks、workflows、agents（task members），配上 flow runner、 scheduler 等等，可以參考 https://github.com/cline/cline、https://github.com/n8n-io/n8n

### 幾個 Unit 概念

- Flow：
  - 工作流，搭配一個 flow runner 來執行，中間可以設 check point 來進行人工檢視
  - Flow 中的節點叫做 Block（或是 Step…）
  - Flow 可以有循環的情況，例如像「撰寫 → 檢視 → （依據檢視意見、前作）撰寫 → 檢視…」
- Task：
  - 包含工作說明、期間、人員、workspace、working files、flow、排程、優先度等等
  - 簡單的 task 基本就是一個 flow 就搞定，執行完就完了
  - 複雜的 task 可能會拆成多個子 tasks，子 tasks 也可能繼續在分成孫 tasks，形成 task tree
  - task create：由 AI 協助完成，可以有一些預設範本（例如建立一個新專案、MVP、…）等等來幫忙將一個 task 規劃的完整一點，這個本質上也是一個 flow
    - New task → 給予指示 → 尋找適當的 flow、套用 flow、執行 flow → 生成 task → 檢視 to finalize
  - task update：當 task 需要更新時，由 AI 協助更新（跟 create 有點像，一樣是一個 flow）
  - task complete、drop、pause：總之就是 task 的狀態管理，可能需要加入一些理由等等的，還是一樣可以由 AI 協助 → AI everywhere (almost)
  - （思考）Task 跟 Flow 是不是可以合併成一個？感覺這兩者性質很接近
    - 微妙… 有時候不一定簡單就是好，從概念上來說這兩者仍然有點不同
- Project
  - 包含多個 Task，這主要是為了更好的管理不同的 tasks，方便瀏覽同一個專案底下的工作進展
  - 盡量去做到自動化，例如在新增工作時，系統可以依據工作內容，判斷是否隸屬於某個 project，建議納至 project 中
  - project create
- Launcher
  - New task → 給予指示 → 尋找適當的 flow、套用 flow、執行 flow → 生成 task → 檢視 to finalize
- Views
  - Task
    - 包含 flow 執行進度，目前需要人工參與的地方（審核、commit 等等）
  - Todos
    - 可能包含：新增的 tasks (例如例行性 tasks）、我當前在做的 task（可能是某個 block）
- 語法: 用於快速 launch task
  - task：
    - 繼續原本的 task？快速呼叫某些已建立的 task
    - 新 task：[] （checkbox）?
  - agent、member：@me @ai @ai-claude-3_5…（基本上都是自動判斷建議，應該不用人工去指示）
  - flow：？ （基本上都是自動判斷建議，應該不用人工去指示）

### 延伸思考

- …你看，我給了設計的想法了，接下來呢？人總是會在完成一個工作後停下，但現在應該是任務派發後，就由 AI 幫忙推動任務執行、規劃，總之就是「不要停」
- 如何商業化？
  - 開源，可自行搭建，也提供線上平台版，隨開即用，省去自行搭建的麻煩
    - 線上版一定使用量免費（例如每日多少個 task），超過要訂閱
  - 基本核心開源，進階功能付費，收費功能像是：更強大的專案管理、更多的服務整合（？若套用 n8n 好像不太有意義）、專案分析、報表生成

# App 基本概念

### 概念關係圖

```
Project (1) ─── contains ─── (n) Task
Task    (1) ─── has ────── (1) Workflow
Workflow(1) ─── contains ─── (n) Step
Step     (1) ─── is ────── (1) Operation | Workflow
```

### Project（專案）

- 定義：一個完整的工作目標集合
- 特點：包含多個 tasks 來實現目標

### Task（任務）

- 定義：需要完成的具體項目
- 特點：
  - 一個 task 綁定一個 workflow
  - 使用 tags（標籤）進行分類，而不是層級式的子任務
  - 如果後續真的需要子任務，可以用標籤來模擬：
    - 例如 #12 首頁開發可以拆分為：
      ```
      #12 首頁開發        標籤：UI, Frontend, Epic
      #13 導航欄元件      標籤：UI, Frontend, Parent:#12
      #14 狀態卡片元件    標籤：UI, Frontend, Parent:#12
      ```
  - 可以有狀態（待辦、進行中、完成等）
- 英文選項：
  - Issue（如 GitHub 使用的術語）

### Workflow（工作流程）

- 定義：完成 task 的執行步驟圖（DAG）
- 特點：
  - 由多個 steps 組成
  - 是一個有向無環圖（DAG）
  - 定義了 steps 之間的依賴關係

### Step（工作）

- 定義：workflow 中的執行單位
- 特點：
  - 可以是原子性操作 Operation（如 API 調用）
  - 也可以是另一個 workflow（子流程）
  - 有明確的執行者（AI/Human/System）
- Step 的執行者類型

````
Step
└── Executor（執行者）
├── Human（人工）
│ 例：審核報告、確認設計
├── AI（智能體）
│ 例：生成內容、分析數據
└── System（系統）
例：API調用、資料轉換、觸發通知

    相關屬性：

    - executor_type: “human” | “ai” | “system”
    - executor_id: 指定的執行者（可選）
    - input: 輸入參數
    - output: 輸出結果
    - status: “pending” | “running” | “completed” | “failed”
    ```
````
