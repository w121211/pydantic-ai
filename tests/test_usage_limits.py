import functools
import operator
import re
from datetime import timezone

import pytest
from inline_snapshot import snapshot

from pydantic_ai import Agent, RunContext, UsageLimitExceeded
from pydantic_ai.messages import (
    ArgsDict,
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import Usage, UsageLimits

from .conftest import IsNow

pytestmark = pytest.mark.anyio


def test_request_token_limit(set_event_loop: None) -> None:
    test_agent = Agent(TestModel())

    with pytest.raises(
        UsageLimitExceeded, match=re.escape('Exceeded the request_tokens_limit of 5 (request_tokens=59)')
    ):
        test_agent.run_sync(
            'Hello, this prompt exceeds the request tokens limit.', usage_limits=UsageLimits(request_tokens_limit=5)
        )


def test_response_token_limit(set_event_loop: None) -> None:
    test_agent = Agent(
        TestModel(custom_result_text='Unfortunately, this response exceeds the response tokens limit by a few!')
    )

    with pytest.raises(
        UsageLimitExceeded, match=re.escape('Exceeded the response_tokens_limit of 5 (response_tokens=11)')
    ):
        test_agent.run_sync('Hello', usage_limits=UsageLimits(response_tokens_limit=5))


def test_total_token_limit(set_event_loop: None) -> None:
    test_agent = Agent(TestModel(custom_result_text='This utilizes 4 tokens!'))

    with pytest.raises(UsageLimitExceeded, match=re.escape('Exceeded the total_tokens_limit of 50 (total_tokens=55)')):
        test_agent.run_sync('Hello', usage_limits=UsageLimits(total_tokens_limit=50))


def test_retry_limit(set_event_loop: None) -> None:
    test_agent = Agent(TestModel())

    @test_agent.tool_plain
    async def foo(x: str) -> str:
        return x

    @test_agent.tool_plain
    async def bar(y: str) -> str:
        return y

    with pytest.raises(UsageLimitExceeded, match=re.escape('The next request would exceed the request_limit of 1')):
        test_agent.run_sync('Hello', usage_limits=UsageLimits(request_limit=1))


async def test_streamed_text_limits() -> None:
    m = TestModel()

    test_agent = Agent(m)
    assert test_agent.name is None

    @test_agent.tool_plain
    async def ret_a(x: str) -> str:
        return f'{x}-apple'

    async with test_agent.run_stream('Hello', usage_limits=UsageLimits(response_tokens_limit=10)) as result:
        assert test_agent.name == 'test_agent'
        assert not result.is_complete
        assert result.all_messages() == snapshot(
            [
                ModelRequest(parts=[UserPromptPart(content='Hello', timestamp=IsNow(tz=timezone.utc))]),
                ModelResponse(
                    parts=[ToolCallPart(tool_name='ret_a', args=ArgsDict(args_dict={'x': 'a'}))],
                    timestamp=IsNow(tz=timezone.utc),
                ),
                ModelRequest(
                    parts=[ToolReturnPart(tool_name='ret_a', content='a-apple', timestamp=IsNow(tz=timezone.utc))]
                ),
            ]
        )
        assert result.usage() == snapshot(
            Usage(
                requests=2,
                request_tokens=103,
                response_tokens=5,
                total_tokens=108,
            )
        )
        with pytest.raises(
            UsageLimitExceeded, match=re.escape('Exceeded the response_tokens_limit of 10 (response_tokens=11)')
        ):
            await result.get_data()


def test_usage_so_far(set_event_loop: None) -> None:
    test_agent = Agent(TestModel())

    with pytest.raises(
        UsageLimitExceeded, match=re.escape('Exceeded the total_tokens_limit of 105 (total_tokens=163)')
    ):
        test_agent.run_sync(
            'Hello, this prompt exceeds the request tokens limit.',
            usage_limits=UsageLimits(total_tokens_limit=105),
            usage=Usage(total_tokens=100),
        )


async def test_multi_agent_usage_no_incr():
    delegate_agent = Agent(TestModel(), result_type=int)

    controller_agent1 = Agent(TestModel())
    run_1_usages: list[Usage] = []

    @controller_agent1.tool
    async def delegate_to_other_agent1(ctx: RunContext[None], sentence: str) -> int:
        delegate_result = await delegate_agent.run(sentence)
        delegate_usage = delegate_result.usage()
        run_1_usages.append(delegate_usage)
        assert delegate_usage == snapshot(Usage(requests=1, request_tokens=51, response_tokens=4, total_tokens=55))
        return delegate_result.data

    result1 = await controller_agent1.run('foobar')
    assert result1.data == snapshot('{"delegate_to_other_agent1":0}')
    run_1_usages.append(result1.usage())
    assert result1.usage() == snapshot(Usage(requests=2, request_tokens=103, response_tokens=13, total_tokens=116))

    controller_agent2 = Agent(TestModel())

    @controller_agent2.tool
    async def delegate_to_other_agent2(ctx: RunContext[None], sentence: str) -> int:
        delegate_result = await delegate_agent.run(sentence, usage=ctx.usage)
        delegate_usage = delegate_result.usage()
        assert delegate_usage == snapshot(Usage(requests=2, request_tokens=102, response_tokens=9, total_tokens=111))
        return delegate_result.data

    result2 = await controller_agent2.run('foobar')
    assert result2.data == snapshot('{"delegate_to_other_agent2":0}')
    assert result2.usage() == snapshot(Usage(requests=3, request_tokens=154, response_tokens=17, total_tokens=171))

    # confirm the usage from result2 is the sum of the usage from result1
    assert result2.usage() == functools.reduce(operator.add, run_1_usages)


async def test_multi_agent_usage_sync():
    """As in `test_multi_agent_usage_async`, with a sync tool."""
    controller_agent = Agent(TestModel())

    @controller_agent.tool
    def delegate_to_other_agent(ctx: RunContext[None], sentence: str) -> int:
        new_usage = Usage(requests=5, request_tokens=2, response_tokens=3, total_tokens=4)
        ctx.usage.incr(new_usage)
        return 0

    result = await controller_agent.run('foobar')
    assert result.data == snapshot('{"delegate_to_other_agent":0}')
    assert result.usage() == snapshot(Usage(requests=7, request_tokens=105, response_tokens=16, total_tokens=120))
