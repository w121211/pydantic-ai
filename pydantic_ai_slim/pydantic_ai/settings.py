from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from httpx import Timeout
from typing_extensions import TypedDict

from .exceptions import UnexpectedModelBehavior

if TYPE_CHECKING:
    from .result import Cost


class ModelSettings(TypedDict, total=False):
    """Settings to configure an LLM.

    Here we include only settings which apply to multiple models / model providers.
    """

    max_tokens: int
    """The maximum number of tokens to generate before stopping.

    Supported by:
    * Gemini
    * Anthropic
    * OpenAI
    * Groq
    """

    temperature: float
    """Amount of randomness injected into the response.

    Use `temperature` closer to `0.0` for analytical / multiple choice, and closer to a model's
    maximum `temperature` for creative and generative tasks.

    Note that even with `temperature` of `0.0`, the results will not be fully deterministic.

    Supported by:
    * Gemini
    * Anthropic
    * OpenAI
    * Groq
    """

    top_p: float
    """An alternative to sampling with temperature, called nucleus sampling, where the model considers the results of the tokens with top_p probability mass.

    So 0.1 means only the tokens comprising the top 10% probability mass are considered.

    You should either alter `temperature` or `top_p`, but not both.

    Supported by:
    * Gemini
    * Anthropic
    * OpenAI
    * Groq
    """

    timeout: float | Timeout
    """Override the client-level default timeout for a request, in seconds.

    Supported by:
    * Gemini
    * Anthropic
    * OpenAI
    * Groq
    """


def merge_model_settings(base: ModelSettings | None, overrides: ModelSettings | None) -> ModelSettings | None:
    """Merge two sets of model settings, preferring the overrides.

    A common use case is: merge_model_settings(<agent settings>, <run settings>)
    """
    # Note: we may want merge recursively if/when we add non-primitive values
    if base and overrides:
        return base | overrides
    else:
        return base or overrides


@dataclass
class ExecutionLimitSettings:
    """Settings to configure an agent run."""

    request_limit: int | None = None
    request_tokens_limit: int | None = None
    response_tokens_limit: int | None = None
    total_tokens_limit: int | None = None

    _request_count: int = 0
    _request_tokens_count: int = 0
    _response_tokens_count: int = 0
    _total_tokens_count: int = 0

    def increment(self, cost: Cost) -> None:
        self._request_count += 1
        self._check_limit(self.request_limit, self._request_count, 'request count')

        self._request_tokens_count += cost.request_tokens or 0
        self._check_limit(self.request_tokens_limit, self._request_tokens_count, 'request tokens count')

        self._response_tokens_count += cost.response_tokens or 0
        self._check_limit(self.response_tokens_limit, self._response_tokens_count, 'response tokens count')

        self._total_tokens_count += cost.total_tokens or 0
        self._check_limit(self.total_tokens_limit, self._total_tokens_count, 'total tokens count')

    def _check_limit(self, limit: int | None, count: int, limit_name: str) -> None:
        if limit and limit < count:
            raise UnexpectedModelBehavior(f'Exceeded {limit_name} limit of {limit} by {count - limit}')
