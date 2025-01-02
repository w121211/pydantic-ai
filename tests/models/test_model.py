from typing import Callable

import pytest

from pydantic_ai import UserError
from pydantic_ai.models import Model, infer_model
from pydantic_ai.models.gemini import GeminiModel

from ..conftest import TestEnv, try_import

with try_import() as openai_imports_successful:
    from pydantic_ai.models.openai import OpenAIModel

with try_import() as vertexai_imports_successful:
    from pydantic_ai.models.vertexai import VertexAIModel

with try_import() as anthropic_imports_successful:
    from pydantic_ai.models.anthropic import AnthropicModel

with try_import() as groq_imports_successful:
    from pydantic_ai.models.groq import GroqModel

with try_import() as ollama_imports_successful:
    from pydantic_ai.models.ollama import OllamaModel

with try_import() as mistral_imports_successful:
    from pydantic_ai.models.mistral import MistralModel


TEST_CASES = [
    ('OPENAI_API_KEY', 'openai:gpt-3.5-turbo', 'openai:gpt-3.5-turbo', OpenAIModel, openai_imports_successful),
    ('OPENAI_API_KEY', 'gpt-3.5-turbo', 'openai:gpt-3.5-turbo', OpenAIModel, openai_imports_successful),
    ('OPENAI_API_KEY', 'o1', 'openai:o1', OpenAIModel, openai_imports_successful),
    ('GEMINI_API_KEY', 'google-gla:gemini-1.5-flash', 'google-gla:gemini-1.5-flash', GeminiModel, lambda: True),
    ('GEMINI_API_KEY', 'gemini-1.5-flash', 'google-gla:gemini-1.5-flash', GeminiModel, lambda: True),
    (
        'GEMINI_API_KEY',
        'google-vertex:gemini-1.5-flash',
        'google-vertex:gemini-1.5-flash',
        VertexAIModel,
        vertexai_imports_successful,
    ),
    (
        'GEMINI_API_KEY',
        'vertexai:gemini-1.5-flash',
        'google-vertex:gemini-1.5-flash',
        VertexAIModel,
        vertexai_imports_successful,
    ),
    (
        'ANTHROPIC_API_KEY',
        'anthropic:claude-3-5-haiku-latest',
        'anthropic:claude-3-5-haiku-latest',
        AnthropicModel,
        anthropic_imports_successful,
    ),
    (
        'ANTHROPIC_API_KEY',
        'claude-3-5-haiku-latest',
        'anthropic:claude-3-5-haiku-latest',
        AnthropicModel,
        anthropic_imports_successful,
    ),
    (
        'GROQ_API_KEY',
        'groq:llama-3.3-70b-versatile',
        'groq:llama-3.3-70b-versatile',
        GroqModel,
        groq_imports_successful,
    ),
    ('OLLAMA_API_KEY', 'ollama:llama3', 'ollama:llama3', OllamaModel, ollama_imports_successful),
    (
        'MISTRAL_API_KEY',
        'mistral:mistral-small-latest',
        'mistral:mistral-small-latest',
        MistralModel,
        mistral_imports_successful,
    ),
]


@pytest.mark.parametrize('mock_api_key, model_name, expected_model_name, expected_model, deps_available', TEST_CASES)
def test_infer_model(
    env: TestEnv,
    mock_api_key: str,
    model_name: str,
    expected_model_name: str,
    expected_model: type[Model],
    deps_available: Callable[[], bool],
):
    if not deps_available():
        pytest.skip(f'{expected_model.__name__} not installed')

    env.set(mock_api_key, 'via-env-var')

    m = infer_model(model_name)  # pyright: ignore[reportArgumentType]
    assert isinstance(m, expected_model)
    assert m.name() == expected_model_name

    m2 = infer_model(m)
    assert m2 is m


def test_infer_str_unknown():
    with pytest.raises(UserError, match='Unknown model: foobar'):
        infer_model('foobar')  # pyright: ignore[reportArgumentType]
