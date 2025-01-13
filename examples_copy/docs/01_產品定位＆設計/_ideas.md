
# 實際開發時碰到的問題 & 方案

我在開發 event system 時，針對 event handler 是否要採 generic，經過多輪 ai 對話，決定是採一個替代方案。\
後來繼續去做別的東西，回過頭來要重寫 event system時就完全忘了這個方案（包含 code）存在哪了，要找有點困難\
=> 對策：
1. 將目前的一些問題、結論、成果給「紀錄、筆記」下來，免得到了後面忙別的，回來又找不到
2. 很多時候，紀錄「問題」歷程比「解法」更重要，因為問題是我當時的思緒
3. Search across multiple chats？（例如在這個 folder 下搜尋 chats）


我在開發時習慣就是不停開 chat。通常是針對一個問題，因為需要先「清空」前面的討論，或是基於當前成果繼續問其他方向的問題。\
而不停開新 chat 的問題就是因為 chats 與 chats 間沒有 grouping，所以要回顧那一堆 chats 時我也很難找我想要的資訊。\
這問題跟前一個很像，都是因為一堆 chats 在沒有整理的情況很難被回顧使用，一個好的紀錄點是一個值得的功能。但我也同意這不是什麼非必要的功能。
=>
1. 人很懶，我可能已經跳主題了，但我還是在同一個分類項目底下 -> 有沒有可能在當發覺這分類可以另開主題時，提醒用戶＆後續自動化？

# UI/UX 實用功能

### Chat

在 chat 中的 agent message，允許：
1. 用不同的 LLM 重跑
2. 把 prompt 翻成英文後重跑（基於一般的 LLM 對於英文發揮較好）

User inputbox
- 用戶可以選擇 "enter" or "shift + enter" to submit

Prompt congtext 快速注入
- Current file，除非有"select texted"，不然就是注入整個file
