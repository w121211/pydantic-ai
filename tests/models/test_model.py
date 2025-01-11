from importlib import import_module

import pytest

from pydantic_ai import UserError
from pydantic_ai.models import infer_model

from ..conftest import TestEnv

TEST_CASES = [
    ('OPENAI_API_KEY', 'openai:gpt-3.5-turbo', 'openai:gpt-3.5-turbo', 'openai', 'OpenAIModel'),
    ('OPENAI_API_KEY', 'gpt-3.5-turbo', 'openai:gpt-3.5-turbo', 'openai', 'OpenAIModel'),
    ('OPENAI_API_KEY', 'o1', 'openai:o1', 'openai', 'OpenAIModel'),
    ('GEMINI_API_KEY', 'google-gla:gemini-1.5-flash', 'google-gla:gemini-1.5-flash', 'gemini', 'GeminiModel'),
    ('GEMINI_API_KEY', 'gemini-1.5-flash', 'google-gla:gemini-1.5-flash', 'gemini', 'GeminiModel'),
    (
        'GEMINI_API_KEY',
        'google-vertex:gemini-1.5-flash',
        'google-vertex:gemini-1.5-flash',
        'vertexai',
        'VertexAIModel',
    ),
    (
        'GEMINI_API_KEY',
        'vertexai:gemini-1.5-flash',
        'google-vertex:gemini-1.5-flash',
        'vertexai',
        'VertexAIModel',
    ),
    (
        'ANTHROPIC_API_KEY',
        'anthropic:claude-3-5-haiku-latest',
        'anthropic:claude-3-5-haiku-latest',
        'anthropic',
        'AnthropicModel',
    ),
    (
        'ANTHROPIC_API_KEY',
        'claude-3-5-haiku-latest',
        'anthropic:claude-3-5-haiku-latest',
        'anthropic',
        'AnthropicModel',
    ),
    (
        'GROQ_API_KEY',
        'groq:llama-3.3-70b-versatile',
        'groq:llama-3.3-70b-versatile',
        'groq',
        'GroqModel',
    ),
    ('OLLAMA_API_KEY', 'ollama:llama3', 'ollama:llama3', 'ollama', 'OllamaModel'),
    (
        'MISTRAL_API_KEY',
        'mistral:mistral-small-latest',
        'mistral:mistral-small-latest',
        'mistral',
        'MistralModel',
    ),
]


@pytest.mark.parametrize('mock_api_key, model_name, expected_model_name, module_name, model_class_name', TEST_CASES)
def test_infer_model(
    env: TestEnv, mock_api_key: str, model_name: str, expected_model_name: str, module_name: str, model_class_name: str
):
    try:
        model_module = import_module(f'pydantic_ai.models.{module_name}')
        expected_model = getattr(model_module, model_class_name)
    except ImportError:
        pytest.skip(f'{model_name} dependencies not installed')

    env.set(mock_api_key, 'via-env-var')

    m = infer_model(model_name)  # pyright: ignore[reportArgumentType]
    assert isinstance(m, expected_model)
    assert m.name() == expected_model_name

    m2 = infer_model(m)
    assert m2 is m


def test_infer_str_unknown():
    with pytest.raises(UserError, match='Unknown model: foobar'):
        infer_model('foobar')  # pyright: ignore[reportArgumentType]
