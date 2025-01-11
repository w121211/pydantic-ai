Agent Workflow(工作流)

- 初始 Task
  - 使用者給予 task → planner agent + user 合作制定 plan → plan {task description, steps, …}
  - Plan 儲存在 Space
- 開始 step
  - Initialize → run team chat → step output (ie, step works)
    - Initialize
      - Planner 基於當前的 step task 創建 team [agent, user, …]
      - 從工作區載入需要的 context
  - 結束 step 的幾個情況
    - 自動 terminate，例如 agent 自行判斷、一些無 agent 的 step （web search、user input works 等等）
    - user approve works
  - 特殊情況
    - user 在跑到一半時就先終止 step，可能是一開始的 step 指示不好，導致輸出成果不佳，想更新後重跑
      - 這種時候這個 flow 是該 1. 分支出來、2. 繼續在當前這個疊加（flow 還是同一個，只是這個 step 等於是被執行第 n 次，工作區是用最新的 version，但也同時保留過去的 version）？
    - 當前的對話太長，已經影響效能，想開一個新對話，但需要在當前的 works 上繼續
- step 結束後
  - step output works, user feedback, … → planner + user update plan
    - 一般情況：把當前的 step 標註為已完成，並更新 step works 的 path
    - 特殊情況：
      - user 指示重新規劃後續 steps：這時候就需要 planner + user 來討論後續 steps 該怎樣做
        - 為什麼要重新規劃？因為很多時候，計劃趕不上變化，有可能原先想的是這樣，但其實做到一半覺得要這樣做才對。例如：
          - 我叫 agent 寫一個 app ，但發現 agent 直接寫 app 漏掉太多東西，需要先從 design 開始，所以這時候就需要修改 plan，甚至完全重跑一個新的 flow。
          - 我改叫 agent 先設計 app，然後寫，結果發現還是有所不足，需要先定義好一些基本的 interfaces, types，我檢查沒問題後，才基於這些東西再來 implement
      - user 覺得要重跑，重新規劃 plan
        - 可以是將當前的 plan 當作 context，然後開一個新 task，這可以視為 1. revision、2. 全新 task，跟目前 task 毫無關聯（或是簡單的弱連結，例如原始 plan 來自哪個 task）？
        - 希望適度的重複利用當前 works
      - agent 判斷需重新規劃後續 steps（？）
      - 會不會有一種可能是一開始就只是做階段性的規劃，例如需要看成果才能繼續規劃後續 steps？
        - 但如果是這樣，為何不直接拆成兩個 task？
          - 例如，先是出一個 app 設計概念，再來是依照設計概念訂定 app 架構，完全可以算是兩個 task。
          - 但這就需要跨 task 的 works 共享，也可以是導入一個更大的概念，例如 project，在 project 底下有多個 tasks

### 概念 (主要採用 autogen AgentChat)

**Assistant**：同於 autogen AgentChat

**Team**：同於 autogen AgentChat，主要組成為 assistants（其中可包含 user，使用 user proxy）、chat type（不同類型的 chat）

**Project**：包含一堆 tasks，屬於最高層級

**Task**：...

**Plan**：...

- 嚴格來說是 task plan，但現階段不考慮 project plan，我個人也不覺得需要 project plan
- plan 包含 steps

**Step**：...

- 嚴格來說是 task step，但沒有所謂的 project step

**Work**: ...

- 主要就是在每個 step 產出的 work(s)，可以是由 user、assistant 或是純 function 產出
- 利用 space 保存 works

**Space（工作區）**: 有 project space、task space

- 一個 task 有一個對應的工作區，用於將 context（背景資料）、plan、works 放在這個工作區裡，方便 step task 間的共享、編輯
- 所有的 task works（文件） 都會被儲存起來，每個文件有一個對應的 unique path，所以可以實現跨 task 的呼叫

# 討論

**Step cases**

Step 有多種 cases

- 純粹執行 function，完全不需要 agent，例如 scrape a web page
- 純粹 user 的動作，例如某個文件只有 user 可以給予
- 純粹 agent 的動作，不需要 user approve，agent 完成 work 後即可執行下一步驟
- agent work 需要 user feedback、approve
  - agent 生成 work 後，需要 user feedback，user approve 後才可以繼續下個 step -> 似乎適合 RoundRobinChat
  - 有時候 agent 可能需要先跟 user 討論、確認一些事項才可以開始生成 -> 似乎還是適合 RoundRobinChat
  - 當 agent 在單一輸出時因為字數限制，沒有完成 work，需要接續生成，該如何處理？
  - 若 user 乾脆自己把 agent 生成的 work 修改完了，可不可以直接基於此 work 交差？

各個 cases 要分別如何對應？例如說 team 要有哪些 agent、用哪種 chat？

**Step team**：可能是 user、assistant（一個或多個）等等

**Step assistant**

若這個 step 需要 assistant 產出 work，我覺得比較好的作法是:

- 這個 step assistant（負責生成 work）是一個基本 agent, Step task, context 等等都放在初始 prompt，然後開始 chat。Assistant 的 system instruction 則是一個更為普遍的東西，我想到的是類似 task guideline，但我覺得一開始可以完全忽略 system instruction。
- 這樣做的好處是，若 user 開始一個新對話（同一個 step ，user 可能希望 rerun step 或是當前對話過長想開一個新的），可由 user 去調整初始 prompt（包含 step task, context 等等）。

**Rerun step**

需求情境

- 當前的對話（chat）過長，想清空前面的討論，讓 agent 可以專注在主要任務 -> 我會希望新對話是延續當前的 work 繼續，但希望能自動寫 prompt 來延續這個對話（因為有很明確的目的，這可以是預設＆程式化）
- 一開始給的 prompt 不好，想調整 -> 可能不需要當前的 work
- 做到一半的 work，我覺得需要改很多（改一點點的話直接在原對話應該就可以），乾脆直接給當前的 work 修改意見，然後在新對話中叫 agent 依照 work 修改
- 新對話的 work 反而沒有前面對話的 work 更好 -> 要能快速的瀏覽前面的 works，然後從那個 work 開始

Approaches

- 簡單作法：因為負責生成 work 的 step assistant 的所有指示都是透過 prompt 來注入，所以最簡單的做法就是
  - 當 user 開啟一個新對話時，因為我們無法預知 user 是基於什麼理由開新對話，先載入前一個的初始 prompt（含 step task、context 等等），然後給予一些快捷按鈕或一些快捷 key（例如@、#）來讓 user 快速加入 context, works, 預設 prompt 等等，調整成他想要的 prompt
  - 當 user 是編輯 work，在 work 上給予意見等等，可以有快捷鍵來直接開啟一個新對話，並將這個 work 搭配預設 prompt，指示 assistant 依照 comment 做修改
  - 總之這個做法就是盡量讓 user 自主決定 prompt，但為了避免重複打同樣的 prompt，所以利用快捷鍵來自動載入，然後讓 user 去調整

新對話與前一個對話的連結？

- 因為都同在一個 step，簡單做法就是允許一個 step 下有多個對話。
- 但 works 可能要有一個比較好的整合，例如雖然聚焦在當前 work，但也要讓 user 可以快速瀏覽之前的 works -> 這可以做在 space 裡，我的想像是 space 就是一個 folder，可以掛在 local 端，然後每個 step 的 works 就放在/task/step_n/works/work_20241111_0931_OOOO、work_20241111_0947_OOOO、...（命名可以再討論，這只是個初步想法）

**Next step**：Next step 會基於先前的 step works（不一定是前一個 step，可能是前面多個 steps 的多個 works），設計是採用 space 來共享 work，在 step 結束時需要知道該 step work，然後當 next step 初始化時將需要的作為 context 導入

有可能靜態生成的 Step setup 嗎，也就是說，在 planning 的時候就生成類似 chain, graph workflow 的東西＆對每個節點做設定？

- 基於已經沒有 replan，plan 的每個 step 都是確定的，step setup 所需要的就是 step task、context（例如 works），我可以想像他可以用程式的方式串接起來，就像 chain, graph workflow
- 但 chain, graph workflow 會增加整體程式的複雜度，若動態生成 step setup 並不會很花成本，我不傾向採用這個作法
- => 很 naive 但也很 MVP 的做法，完全動態生成 step setup
  - 優化方向：有些 step setup 只需要前一個步驟的 work、step task，無需 agent ，這種時後就可以直接程式化生成

需要 agent 做 step setup 嗎？ （step setup cases、作法）

- step 是純 function：agent 作為 previous work parser？ -> 若是這樣乾脆就把這個 agent 寫成是 function executor assistant，prompt 設為 1. 執行特定的 tool 2. 給予 work 作為 tool 的輸入
- step 有包含 agent
  - system instruction 可以在 plan 階段決定，assistant 需要的資訊透過 pompt 注入
  - 採用哪種類型的 chat 也可以在 plan 階段設定
- step 是純 human -> 不需要 agent
- => 結論：暫時沒有想到（未來也許有）需要 agent 做 step setup

**New Task**：User 創建一個新 task，planner assistant 與 user 共同規劃這個 task 的 plan

這其實也可以當成是一個 step（step 0）？

- 我個人傾向是把他當成 step 0，這樣我們只要專注在 step、task 這兩個 component 的處理
- 當 user approve 了 plan 就會創建、自動執行

Planner assistant

- 完全可以套用 step assistant 的方式
  - system instruction 告訴他的工作是 planner，目標是與 user 共同規劃 task
  - user 用 prompt 說明自己的 task、給予 context、works（可以有快捷鍵方便導入）、previous plan（當想要 replan）

**Run Task**

Task: {description, steps, ...}

如何執行 task？

- For each step, 依照 step 的設定，初始化 team、注入 inputs，然後 run team
  - Step: {id, step_task, team: {assistants, chat, ...}, reqiure_inputs, ...}
- 注入 inputs：主要就是前面的 works，naive 的話就是直接把上一個 step 當成下個 step 做注入

**Replan（結論：replan 等同於 new task）**

什麼時候會需要 replan？

- user 可能在做到一半時，覺得需要調整整個 task 的方向、plan。例如我一開始叫 agent 直接寫 code，但發現成品不好，需要先設計架構，我檢查ＯＫ後才依照架構寫 code

由誰發動 replan？

- 由 agent 發動的話，除非無需 user approve new plan，不然 flow 就會被卡在此直到 user approved，但很多時候我們希望高度自動化，特別是在有多個 flows 同時在跑時
- 為求簡單，可以先設定成由 user 發動，例如是每完成一個 step 時，且這個 step output 是需要 user approved 的情況下，user 可以給予後續 steps 的修改建議（當然也可以不給建議）
- 更簡單也更 MVP 的做法：先不考慮動態 steps（但架構上允許動態 steps），假設 user 對於當前的 plan 有意見，他可以隨意的中斷這個 task，從這個 task flow 中分支一個新的 flow，新 flow 可以 replan -> 我個人覺得這個作法更好

Replan cases

- task 目標大幅調整，需要重新開始 task
  - => 這情況根本不需要 replan，只要開一個新 task 就好，需求可能是需要快速導入一些 resources, context, 這可以透過預設的 new task context, hints, 快捷鍵等等功能來實現
- 假設執行到 step 4，可能 step 1, 2 OK，但 step 3, 4 覺得偏離方向，希望調整 step 3 以後的方向
  - =>
    - 基於當前的 plan、context 等等（與 step agent 一樣使用 prompt 載入，所以 user 可以決定到底 planner 需要知道哪些 context），讓 user 與 planner 討論，user 可以講出自己想要調整的方向、或是指出問題等等，共同規劃新 plan（step 可以是從 1 開始規劃）、需要的 context、works，
    - 創新 task，導入規劃好的 plan, context, works，然後直接執行 step 1

**Task Rerun（結論：task rerun 等同於 new task）**：

如何處理原 task 跟新 task 的關係？

- 要先試想有什麼時候會需要原 task？
- 幾種做法：
  - 用 revision 的概念，task v1, v2, v3... or v_timestamp。等於是同一個 task 仍歸屬一起，新的取代舊的
    - 缺點是，有時候我就是想基於此開一個新 task（要修改的幅度已經大大超過原本的 task 範圍，可視為一個全新的），新的並不是舊的的替代品
  - 簡單也 MVP 的做法：不特別處理他，新的舊的通通當成 task
- => 結論，新舊兩者獨立，只是新的 task 可以記錄是源自於某個 task（但不一定需要，在 new task 規劃階段時由 user 決定）

Task 可以從哪種情況作分支，分支後怎樣處理？

- 如果是對當前的 step task 有所修改，可以直接透過 rerun step，好像不太需要創新 task（有例外嗎？）
- 似乎可以假設：只有在需要 replan 時才需要創新 task ？
- => 結論，Task 分支等同於 new task

從 Replan cases 分析，其實根本不需要 task rerun 這個概念，完全可以當成是創新 task

- 不管是從零開始的創新 task，還是基於當前 task 創新 task，都是與 planner 討論後創新，這兩者的差別只是在於 prompt 的設定，後者需要給予當前 task 的相關資訊（這個可以設定快捷方式導入）
- 所以本質上都是創新 task

**Tasks management**：

- 這功能在 agent 工作流中沒有寫到，但在 app 裡實際需要
- App 會用 dashsboard 來管理 tasks (by the project)，主要就是顯示正在執行的 tasks、當前的進度（執行中、完成、等待 user 、暫停、中斷、錯誤等等）

如果 task 是可以 revision，如何處理他？

- 暫時不考慮 revision，因為我覺得這相對複雜

若不考慮 revision，在 task 分支時，怎麼處理新舊 task？

- 新舊 task 都視為獨立的 task，兩者之間無特別關係
- 新的 task 會有一個源自哪個 task 的紀錄，用於追溯
- 舊 task 會終止執行，進度顯示為 user 中斷。有需要的話當然也可以註明分支的 task，但我覺得不一定需要
- 新 task 會開始執行

- 創新 task 是發生在需要 replan 的時候，他可能是因為當前的 goal

**儲存顆粒度**

每個 step 中的每個 message 都要即時保存，所以有辦法從特定的 message 接續開始、或是從該 message 做分支
