"""Simple example of using PydanticAI to construct a Pydantic model from a text input.

Planner Agent:

* 要幫助用戶的 task 規劃 plan，plan 包含一系列的 steps。
* 這些 steps 將會透過被 agent 依序執行，每個 step 會由一個 agent 協助完成（其中可能會有用戶參與）。
* 若用戶提出來的 task 過於龐大，planner 會與用戶透過對話方式，釐清用戶的需求，調整成適合的 task
* Planner 提出 plan 後用戶會檢視並給予意見，只有當用戶 APPROVE 時才結束，並輸出 plan。
* 例如（這裡只是用來展示，實際要更為複雜）：
    * 初始 task：宣傳我的開源專案
    * 經過討論調整後的 task：每天瀏覽網上技術論壇，搜尋與我的開源專案相關的討論串，參與討論
    * Steps:
        * 在技術論壇A、B、C搜尋某技術的相關討論串
        * Agent 選擇適合的討論串
        * Agent 編寫回復文，用戶檢視並給予建議，直到檢視通過
        * 送出回復文

"""

import os
from typing import cast

import logfire
from pydantic import BaseModel

from pydantic_ai import Agent
from pydantic_ai.models import KnownModelName

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')


class Step(BaseModel):
    city: str
    country: str


model = cast(KnownModelName, os.getenv('PYDANTIC_AI_MODEL', 'openai:gpt-4o'))
print(f'Using model: {model}')

# 方案1: 使用 result_type 來指定輸出格式（背後 pydantic-ai 會利用 LLM tool call 功能來輸出指定格式）
agent_output_structured = Agent(model, result_type=list[Step])

# 方案2: 返回純 text。因為 LLM 若指定輸出格式的效果似乎比不上自由輸出，所以這個方案是先輸出文字，再用另一個 agent 做格式化輸出
#
# 的結構性資料的效果比起（不限制）的自由輸出較為
agent_output_text = Agent(model)

if __name__ == '__main__':
    # result = agent.run_sync('The windy city in the US of A.')
    # print(result.data)
    # print(result.usage())

    result = agent.run_sync('The windy city in the US of A.')
    # print(result.data)
    # print(result.usage())
