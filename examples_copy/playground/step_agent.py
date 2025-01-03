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


Example Plan:

Step 1: ...
- Team: @assistant
- User review?: No
- Expect input: ...
- Output: ...

Step 2: ....
- Team: @function_executor
- User review?: No
- Expect input:
- Output:


Space:

[Project_Name]
- task_21_hello_world
    - works
        - work-hello_world_20241023_0921.py
    - step_3_...
    - step_2_...
    - step_1_...
        - 20241023_0921
            - conversation.txt
            - work-hello_world_20241023_0921.py
            - work-hello_world_20241023_0928.py
        - 20241023_0835
            - conversation.txt
            - work-hello_world_20241023_0921.py
            - work-hello_world_20241023_0928.py
        - 20241023_0833
            - conversation.txt
            - work-hello_world_20241023_0921.py
            - work-hello_world_20241023_0928.py
- task_20_hello_world
    - ...

Prompt 使用者快捷引用、快速輸入:
- 方向鍵上、下，切換先前 prompt
- '@': Get frequent prompts, e.g. "@revise"
- '#': Include the file, e.g. "#hello-world.py(/works)"
- 轉換：Normal token <hot>@revise</hot>
"""

import os
from typing import cast

import logfire
from pydantic import BaseModel
from rich.prompt import Prompt

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import KnownModelName
from pydantic_ai.usage import Usage

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')


class Step(BaseModel):
    city: str
    country: str


class StepOutput(BaseModel):
    pass


model = cast(KnownModelName, os.getenv('PYDANTIC_AI_MODEL', 'openai:gpt-4o'))
print(f'Using model: {model}')


step_agent = Agent(model)
# parse_and_run_tool_agent = Agent(model)


steps: list[Step] = []


class Conversation(BaseModel):
    parent_id: str
    messages: list[ModelMessage]


class TaskStep(BaseModel):
    id: str
    kind: 'a' | 'b'
    conversations: list[Conversation] | None
    require_user_review: bool
    description: str
    team: list[str]
    output: Any


async def start_conversation(from_conversation: Conversation):
    pass


async def step_conversation(
    parent_conversation: Conversation, usage: Usage
) -> SeatPreference:
    # Prepare context
    # 抓出快捷鍵 ＆ 導入

    # Start the conversation
    message_history: list[ModelMessage] | None = None
    while True:
        answer = Prompt.ask('What seat would you like?')
        result = await step_agent.run(
            answer,
            message_history=message_history,
            usage=usage,
            usage_limits=usage_limits,
        )
        if isinstance(result.data, SeatPreference):
            return result.data
        else:
            print('Could not understand seat preference. Please try again.')
            message_history = result.all_messages()


# async def run_step(step: Step) -> StepOutput:
#     # Setup context


#     message_history: list[ModelMessage] | None = None

#     # Start conversation
#     while True:
#         prompt = Prompt.ask('Prompt:')

#         result = await step_agent.run(
#             prompt,
#             message_history=message_history,
#             usage=usage,
#             usage_limits=usage_limits,
#         )
#         # if isinstance(result.data, SeatPreference):
#         #     return result.data
#         # else:
#         # print('Could not understand seat preference. Please try again.')

#         message_history = result.all_messages()

#     result.data


async def run_steps(steps: list[Step]):
    for step in steps:
        run_step(step)


if __name__ == '__main__':
    result = agent.run_sync('The windy city in the US of A.')
    print(result.data)
    print(result.usage())
