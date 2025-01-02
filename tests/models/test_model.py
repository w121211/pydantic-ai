import pytest

from pydantic_ai import UserError
from pydantic_ai.models import infer_model
from pydantic_ai.models.gemini import GeminiModel

from ..conftest import TestEnv, try_import

with try_import() as openai_imports_successful:
    from pydantic_ai.models.openai import OpenAIModel

with try_import() as vertexai_imports_successful:
    from pydantic_ai.models.vertexai import VertexAIModel

with try_import() as anthropic_imports_successful:
    from pydantic_ai.models.anthropic import AnthropicModel


@pytest.mark.skipif(not openai_imports_successful(), reason='openai not installed')
def test_infer_str_openai(env: TestEnv):
    env.set('OPENAI_API_KEY', 'via-env-var')
    m = infer_model('openai:gpt-3.5-turbo')
    assert isinstance(m, OpenAIModel)
    assert m.name() == 'openai:gpt-3.5-turbo'

    m2 = infer_model(m)
    assert m2 is m


@pytest.mark.parametrize('model_name', ['gpt-3.5-turbo', 'o1'])
def test_infer_str_openai_without_provider(env: TestEnv, model_name: str):
    env.set('OPENAI_API_KEY', 'via-env-var')
    m = infer_model(model_name)  # pyright: ignore[reportArgumentType]
    assert isinstance(m, OpenAIModel)
    assert m.name() == f'openai:{model_name}'

    m2 = infer_model(m)
    assert m2 is m


def test_infer_str_gemini(env: TestEnv):
    env.set('GEMINI_API_KEY', 'via-env-var')
    m = infer_model('google-gla:gemini-1.5-flash')
    assert isinstance(m, GeminiModel)
    assert m.name() == 'google-gla:gemini-1.5-flash'


def test_infer_str_gemini_without_provider(env: TestEnv):
    env.set('GEMINI_API_KEY', 'via-env-var')
    m = infer_model('gemini-1.5-flash')  # pyright: ignore[reportArgumentType]
    assert isinstance(m, GeminiModel)
    assert m.name() == 'google-gla:gemini-1.5-flash'

    m2 = infer_model(m)
    assert m2 is m


@pytest.mark.skipif(not vertexai_imports_successful(), reason='google-auth not installed')
def test_infer_vertexai(env: TestEnv):
    m = infer_model('google-vertex:gemini-1.5-flash')
    assert isinstance(m, VertexAIModel)
    assert m.name() == 'google-vertex:gemini-1.5-flash'


@pytest.mark.skipif(not anthropic_imports_successful(), reason='anthropic not installed')
def test_infer_anthropic(env: TestEnv):
    env.set('ANTHROPIC_API_KEY', 'via-env-var')
    m = infer_model('anthropic:claude-3-5-haiku-latest')
    assert isinstance(m, AnthropicModel)
    assert m.name() == 'anthropic:claude-3-5-haiku-latest'

    m2 = infer_model(m)
    assert m2 is m


def test_infer_anthropic_no_provider(env: TestEnv):
    env.set('ANTHROPIC_API_KEY', 'via-env-var')
    m = infer_model('claude-3-5-haiku-latest')  # pyright: ignore[reportArgumentType]
    assert isinstance(m, AnthropicModel)
    assert m.name() == 'anthropic:claude-3-5-haiku-latest'

    m2 = infer_model(m)
    assert m2 is m


def test_infer_str_unknown():
    with pytest.raises(UserError, match='Unknown model: foobar'):
        infer_model('foobar')  # pyright: ignore[reportArgumentType]
