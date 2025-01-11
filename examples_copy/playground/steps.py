import os
from typing import Literal, cast

import logfire
from pydantic import BaseModel

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import KnownModelName

# 'if-token-present' means nothing will be sent (and the example will work) if you don't have logfire configured
logfire.configure(send_to_logfire='if-token-present')


class TaskStepOutput(BaseModel):
    id: str
    kind: 'a' | 'b'
    conversations: list[Conversation] | None
    require_user_review: bool
    description: str
    team: list[str]
    output: Any


model = cast(KnownModelName, os.getenv('PYDANTIC_AI_MODEL', 'openai:gpt-4o'))
print(f'Using model: {model}')


assistant_agent = Agent(model)
# parse_and_run_tool_agent = Agent(model)


class Conversation(BaseModel):
    parent_id: str
    message_history: list[ModelMessage]
    agent: Agent

    def __init__(self, parent_id: str, messages: list[ModelMessage]):
        pass

    def load_from_dict(self, data: dict):
        pass

    async def run_on_console(self):
        while True:
            prompt = Prompt.ask('Prompt:')
            self.step(prompt)

    async def step(self, prompt: str, require_user_review: bool = False):
        if require_user_review and 'APPROVE' in prompt:
            return {
                'result': result,
                'user_review': 'APPROVED',
            }

        result = await self.agent.run(
            prompt,
            message_history=self.message_history,
            usage=usage,
            usage_limits=usage_limits,
        )

        if isinstance(result.data, SeatPreference):
            return result.data
        else:
            print('Could not understand seat preference. Please try again.')
            self.message_history = result.all_messages()


class TaskStep(BaseModel):
    id: str
    step_number: int
    step_name: str
    kind: 'human-agent' | 'agent-only' | 'fnuction'
    conversations: list[Conversation] | None
    require_user_review: bool
    # team: list[str]
    # output: Any

    async def run(self):
        # if self.conversations is None:
        #     return
        if self.kind == 'agent-human':
            for conversation in self.conversations:
                result = await conversation.run_on_console()

        elif self.kind == 'b':
            pass


class TaskRunResult(BaseModel):
    run_status: Literal[
        'running',
        # 'paused',
        'completed',
        'error',
        'wait-external-input',
        'wait-user-review',
    ]
    task_id: str
    task_step_id: str
    task_step_output: TaskStepOutput


class Task(BaseModel):
    id: str
    steps: list[TaskStep]
    current_step: int
    status: (
        'running'
        | 'paused'
        | 'completed'
        | 'error'
        | 'wait-for-external-input'
        | 'wait-for-user-review'
    )

    def __init__(self, id: str, steps: list[TaskStep]):
        pass

    def load_from_dict(self, data: dict):
        pass

    async def load(self, task_diretory: str):
        """讀取存放 Task 的資料夾，載入 task 的所有資訊，包括 steps 等"""
        # Load the task.json.lock，原則上這個不應該被修改
        pass
    
    async def run(self, conversation: Conversation, result: dict) -> TaskRunResult:
        # Load the task



        while self.current_step < len(self.steps):
            current_step = self.steps[self.current_step]
            await current_step.run()
            self.current_step += 1

            if current_step.require_user_review:
            return TaskRunResult(
                run_status='wait-user-review',
                task_id=self.id,
                task_step_id=current_step.id,
                task_step_output=current_step.output,
            )

        return TaskRunResult(
            run_status='completed',
            task_id=self.id,
            task_step_id=current_step.id,
            task_step_output=current_step.output,
        )
        if result['user_review'] == 'APPROVED':
            return

        # Get the next step
        next_step = self.steps[self.current_step + 1]
        await next_step.run()


async def run_step(
    step: Step,
) -> StepOutput:
    # Setup context
    conversation = Conversation(parent_id='123', messages=[])
    conversation.load_from_dict({'id': '123', 'messages': []})

    message, final_output = conversation.step()

    if final_output is not None:
        return final_output

    # Start conversation
    await conversation.run()
    return StepOutput()


async def api_chat(
    conversation_id: str, user_prompt: str, attached_file_paths: list[str]
) -> Conversation:
    """/api/chat?conversation_id={conversation_id}"""
    # Get conversation
    chat = get_chat(conversation_id)
    result = chat.step(user_prompt, attached_file_paths)

    if result['is_final_output']:
        # The chat is done and output the work
        # Process the chat output, save it to the database, update the task status, etc.
        # ...
        task = get_task(chat.task_id)

        # Continue to run the task
        task.run_until_pause(chat, result)


### API Endpoints ###
async def api_create_conversation(parent_conversation_id: str) -> Conversation:
    conversation = Conversation(parent_id=parent_conversation_id, messages=[])
    conversation.load_from_dict({'id': parent_conversation_id, 'messages': []})
    return conversation


async def api_create_task(task_id: str, task_steps: list[TaskStep]) -> Task:
    task = Task(id=task_id, steps=task_steps)
    task.load_from_dict({'id': task_id, 'steps': task_steps})
    return task


async def api_run_step(step: TaskStep) -> TaskStepOutput:
    """Run the step until it pauses"""
    return await step.run()


async def api_run_task(task_id: str) -> TaskStepOutput:
    """Run the task until it pauses"""
    pass


async def api_run_task(task_id: str, external_input: str | None) -> TaskStepOutput:
    """/api/task/{task_id}"""
    # Get or create task
    task = get_task(task_id)

    # Get task steps
    task_steps = get_task_steps(task_id)

    # Run each step
    for step in task_steps:
        output = await run_step(step)
        if output is not None:
            return output


# async def step_conversation(
#     parent_conversation: Conversation, usage: Usage
# ) -> SeatPreference:
#     # Prepare context
#     # 抓出快捷鍵 ＆ 導入

#     # Start the conversation
#     message_history: list[ModelMessage] | None = None
#     while True:
#         answer = Prompt.ask('What seat would you like?')
#         result = await step_agent.run(
#             answer,
#             message_history=message_history,
#             usage=usage,
#             usage_limits=usage_limits,
#         )
#         if isinstance(result.data, SeatPreference):
#             return result.data
#         else:
#             print('Could not understand seat preference. Please try again.')
#             message_history = result.all_messages()


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
