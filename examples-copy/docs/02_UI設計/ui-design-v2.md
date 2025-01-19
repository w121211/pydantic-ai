# UI 設計

Workflow 設計

- 我想像的「入口 flow」（其實就是一個 AI chat flow）：
  1. 使用者給一個簡單直覺的 prompt，例如「開發某某功能」、「寫一篇技術文章」、「我想知道這 app 該怎樣使用？」、「@task:task_name 我想要知道目前進度」、「今天天氣如何？（完全跟 MyAITeam 不相干）」
  2. （app 開啟一個 AI 聊天界面）
  3. AI 判定使用者的意圖，例如創建 task、project、FAQ 等等，或完全跟 MyAITeam 不相干的事，依據意圖挑選適合的 workflow，若沒有適合的 flow，就繼續在當前的 AI chat flow
     1. App 有內建基本的 workflow list，例如創建 task/project、task/project 等等，會與 user prompt 一起送給 AI，讓 AI 從中挑選適合的 flow
  4. （若有適合的 flow）AI 詢問使用者是否要執行這個 flow？例如創建 task，當 user 點擊確認按鈕後，就開始執行新的 flow
     1. ❓ 這個部分我不確定要怎樣處理較好，1. 重新開始一個新 flow，跟目前的 flow 沒有直接關係 2. 新 flow 接在當前的 flow，動態加入後續節點
        1. → 分離執行比較容易做，也清楚，但 chat 介面維持同一個（之前的對話訊息仍然保留，兩者用分隔線隔開）
     2. ❓ 如果遇到使用者想要重來的情況？
        1. → 先不處理，反正對使用者來說也只是開一個新 chat 就可以解決的事

```markdown
[當前對話] --> [意圖確認] --> [流程選擇]
├── 內嵌執行
│ └── 直接在當前對話中續接
└── 分離執行
├── 啟動新流程
└── 保持原對話存活
```

```markdown
# Main Chat Flow

1. [Trigger:UserInput] Receive user message
2. [AI:Intent] Analyze user intent

   - Input: user message
   - Context: previous messages
   - Output:
     - intent_type: "chat" | "task" | "project" | "faq"
     - confidence_score: 0-1
     - suggested_workflow: workflow_id

3. [Branch] Check intent confidence

   - If score > 0.8:
     1. [Action:UI] Show workflow suggestion
     2. [Branch] Wait for user confirmation
        - If confirmed:
          1. [Action:Workflow] Start suggested workflow
          2. [Action:Context] Pass current context
        - If rejected:
          1. [Action:UI] Return to chat mode
   - If score <= 0.8:
     1. [AI:Chat] Continue chat mode
     2. [Action:UI] Show workflow suggestions as options

4. [Action:Context] Update conversation state
```

# Web App 介面設計 v3

## Workspace Page

```
┌─────── Sidebar (280px) ───────┐ ┌─────── Conversation (彈性) ──────┐ ┌─────── Workspace (360px) ───────┐
│                              │ │                                │ │                                  │
│ [常用連結]                    │ │ [任務資訊列]                    │ │ [工具列]                          │
│ 🏠 Home                      │ │ 首頁 UI 開發 #12                │ │ 📄 Files  📊 Version  👁️ Preview   │
│ 📈 Dashboard                 │ │ 進度: 3/5                      │ │                                  │
│ ⭐ Favorites                 │ │                                │ │                                  │
│                              │ │ [對話區]                       │ │ [內容/編輯區]                      │
│ [專案導航]                    │ │ [AI] 我已經分析完成需求...        │ │ 首頁設計稿 v1.2                    │
│ 📌 專案：AI App   [⋮] [➕]    │ │ [User] 這部分需要調整...        │ │                                  │
│  ├ #12 首頁 UI 開發 🏃       │ │ ~~~~ 新對話 ~~~~               │ │ [預覽區域]                        │
│  │  ├ ✓ 定義需求            │ │ [AI] 根據反饋，我建議...         │ │                                  │
│  │  ├ ✓ 分析 UI/UX         │ │ [User] 看起來不錯...           │ │                                  │
│  │  └ ➡ 設計稿 v1.2        │ │ [System] 自動保存完成...        │ │                                  │
│  ├ #13 後端 API 🕒          │ │                                │ │                                  │
│  └ #14 測試規劃 ⌛           │ │                                │ │                                  │
│                              │ │                                │ │                                  │
│ 📌 專案：Web Portal          │ │                                │ │ [操作按鈕]                        │
│  └ ...                      │ │                                │ │ ✏️ Edit  ⬇️ Download  📤 Share    │
│                              │ │                                │ │                                  │
│ [最近造訪]                    │ │ [輸入區]                       │ │ [版本控制]                        │
│ └ [最近開啟的項目列表]         │ │ ╭─────────────────────────╮   │ │ v1.2 (當前)                      │
│                              │ │ │Write a message...        │   │ │ v1.1 - 2024/12/09 15:30         │
│ [功能區]                      │ │ ╰─────────────────────────╯   │ │ v1.0 - 2024/12/09 10:15         │
│ 👤 Account                   │ │ [📎附件] [🎨插入] [發送 ➤]      │ │                                  │
│ ⚙️ Settings                  │ │                                │ │ [協作者]                          │
│ 🌙 Dark Mode                 │ │                                │ │ 👤 Alice (編輯中)                  │
│                              │ │                                │ │ 👤 Bob (瀏覽中)                    │
└──────────────────────────────┘ └────────────────────────────────┘ └──────────────────────────────────┘
```

### 左欄

```
[常用連結]
🏠 Home
📈 Dashboard
⭐ Favorites

[專案導航]
📌 專案：AI App    [⋮] [➕]
 ├ #12 首頁 UI 開發 🏃
 │  ├ ✓ 定義需求
 │  ├ ✓ 分析 UI/UX
 │  └ ➡ 設計稿 v1.2
 ├ #13 後端 API 🕒
 └ #14 測試規劃 ⌛

📌 專案：Web Portal
 └ ...

[最近造訪]
└ [最近開啟的項目列表]

[功能區]
👤 Account
⚙️ Settings
🌙 Dark Mode
```

### 中欄

1. Humnan Agent Chat 類型

```
[任務資訊列]
首頁 UI 開發 #12
進度: 3/5
Prompt: 請按照<用戶需求>編寫一篇... [編輯]

[工具列]
[💬新對話] [⟳重新執行] 

[對話區]
[User] 請按照<用戶需求>編寫一篇... [編輯] [⋮]

[AI] 我已經分析完成需求... [複製] [⋮]

[User] 這部分需要調整... [編輯] [⋮]

[AI] 根據反饋，我建議... [複製] [⋮]

[User] APPROVE... [編輯] [⋮]

[System] 輸出成果：...
[System] 結束對話

~~~ 對話結束 ~~~

[輸入區]
╭──────────────────────────╮
│Write a message...        │
╰──────────────────────────╯
[📎附件] [🎨插入] [發送 ➤]
```


2. Agent only 類型（只有對話區內容稍顯不同）

```
# 
[對話區]
[User] ()  [編輯] [⋮]

[AI] 我已經分析完成需求...  [複製] [⋮]

[User] 這部分需要調整...  [編輯] [⋮]

[AI] 根據反饋，我建議...  [複製] [⋮]

[User] APPROVE...  [編輯] [⋮]

[System] 輸出成果：...
[System] 結束對話

~~~ 對話結束 ~~~
```



注意點：
- 當用戶「編輯」其中的 message ＆ 送出後，會直接從此對話分叉，創新對話（可以是在背景執行、也可以顯示出來讓用戶知道實際運作）
- 當對話結束時，輸入區轉成 distabled 狀態


### 右欄

```
[工具列]
📄 Files  📊 Version  👁️ Preview

[內容/編輯區]
首頁設計稿 v1.2

[預覽區域]





[操作按鈕]
✏️ Edit  ⬇️ Download  📤 Share

[版本控制]
v1.2 (當前)
v1.1 - 2024/12/09 15:30
v1.0 - 2024/12/09 10:15

[協作者]
👤 Alice (編輯中)
👤 Bob (瀏覽中)
```











# Home Page

### 過去的設計(Archive)

```
[Logo]
[Sidebar]

📅 Today 10/14
✓ 審核競品分析報告 /新功能
⚠️◽ 審核產品數據報告 /週報#42 (逾期1天)
  ↳ 👤 待使用者審核
◽ 確認訪談重點 /訪談
  ↳ 🤖 整理逐字稿

10/13
✓ 更新產品規格 /新功能
✓ 客戶訪談 /訪談

10/11
✓ 系統測試 /新功能

📋 未排程
◽ 更新使用手冊 /新功能
◽ 整理客戶回饋 /訪談
```

#### 當前的設計

```
📅 Today 12/15  [點擊任務可展開詳細資訊及工作介面]

[✨ 告訴我你想做什麼]

📂 時間管理 App  [+]
  🔴◽ 審核用戶反饋分類 /用戶回饋
    ↳ 🤖 已分類完成 (2 bugs, 1 feature) ➝ [👤 待審核]

  🔶◽ 確認本週更新說明 /產品發布
    ↳ 🤖 草稿已生成 ➝ [👤 待審核]

📂 技術部落格  [+]
  🔴◽ 撰寫技術文章 /內容#45 (⚠️逾期1天)
    ↳ 🤖 素材準備完成 ➝ [👤 待撰寫]

📂 開發者社群  [+]
  🔶◽ 進行客戶訪談 /訪談#12
    ↳ 🤖 訪談大綱已準備 ➝ [👤 待執行 🕐14:00]

  ⚪◽ Discord 社群維護 /社群經營
    ↳ 🤖 進度更新中 ➝ [⏳ 處理中]
```

新增任務的方式：

1. 快速輸入：

- 頂部的輸入框直接輸入任務描述
- 例如：「幫我寫一篇關於 AI 的技術文章」
- AI 會自動：
  - 判斷歸屬專案（技術部落格）
  - 建議任務細節
  - 規劃工作流程

2. 專案內新增：

- 點擊專案旁的 [+] 按鈕
- 直接在該專案下新增任務
- 系統會自動帶入專案相關資訊

3. 引導式新增：

- 點擊 [+ 新增任務] 後
- 系統引導填寫：
  - 選擇專案
  - 描述任務內容
  - 設定優先級和截止日期
  - AI 協助完善細節
