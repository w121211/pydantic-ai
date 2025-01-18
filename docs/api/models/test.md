# `pydantic_ai.models.test`

Utility model for quickly testing apps built with PydanticAI.

Here's a minimal example:

```py {title="test_model_usage.py" call_name="test_my_agent" noqa="I001"}
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel

my_agent = Agent('openai:gpt-4o', system_prompt='...')


async def test_my_agent():
    """Unit test for my_agent, to be run by pytest."""
    m = TestModel()
    with my_agent.override(model=m):
        result = await my_agent.run('Testing my agent...')
        assert result.data == 'success (no tool calls)'
    assert m.agent_model_function_tools == []
```

See [Unit testing with `TestModel`](../../testing-evals.md#unit-testing-with-testmodel) for detailed documentation.

::: pydantic_ai.models.test
