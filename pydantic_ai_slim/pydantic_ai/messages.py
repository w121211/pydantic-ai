from __future__ import annotations as _annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Annotated, Any, Literal, Union, cast

import pydantic
import pydantic_core
from typing_extensions import Self, assert_never

from ._utils import now_utc as _now_utc


@dataclass
class SystemPromptPart:
    """A system prompt, generally written by the application developer.

    This gives the model context and guidance on how to respond.
    """

    content: str
    """The content of the prompt."""

    dynamic_ref: str | None = None
    """The ref of the dynamic system prompt function that generated this part.

    Only set if system prompt is dynamic, see [`system_prompt`][pydantic_ai.Agent.system_prompt] for more information.
    """

    part_kind: Literal['system-prompt'] = 'system-prompt'
    """Part type identifier, this is available on all parts as a discriminator."""


@dataclass
class UserPromptPart:
    """A user prompt, generally written by the end user.

    Content comes from the `user_prompt` parameter of [`Agent.run`][pydantic_ai.Agent.run],
    [`Agent.run_sync`][pydantic_ai.Agent.run_sync], and [`Agent.run_stream`][pydantic_ai.Agent.run_stream].
    """

    content: str
    """The content of the prompt."""

    timestamp: datetime = field(default_factory=_now_utc)
    """The timestamp of the prompt."""

    part_kind: Literal['user-prompt'] = 'user-prompt'
    """Part type identifier, this is available on all parts as a discriminator."""


tool_return_ta: pydantic.TypeAdapter[Any] = pydantic.TypeAdapter(Any, config=pydantic.ConfigDict(defer_build=True))


@dataclass
class ToolReturnPart:
    """A tool return message, this encodes the result of running a tool."""

    tool_name: str
    """The name of the "tool" was called."""

    content: Any
    """The return value."""

    tool_call_id: str | None = None
    """Optional tool call identifier, this is used by some models including OpenAI."""

    timestamp: datetime = field(default_factory=_now_utc)
    """The timestamp, when the tool returned."""

    part_kind: Literal['tool-return'] = 'tool-return'
    """Part type identifier, this is available on all parts as a discriminator."""

    def model_response_str(self) -> str:
        if isinstance(self.content, str):
            return self.content
        else:
            return tool_return_ta.dump_json(self.content).decode()

    def model_response_object(self) -> dict[str, Any]:
        # gemini supports JSON dict return values, but no other JSON types, hence we wrap anything else in a dict
        if isinstance(self.content, dict):
            return tool_return_ta.dump_python(self.content, mode='json')  # pyright: ignore[reportUnknownMemberType]
        else:
            return {'return_value': tool_return_ta.dump_python(self.content, mode='json')}


error_details_ta = pydantic.TypeAdapter(list[pydantic_core.ErrorDetails], config=pydantic.ConfigDict(defer_build=True))


@dataclass
class RetryPromptPart:
    """A message back to a model asking it to try again.

    This can be sent for a number of reasons:

    * Pydantic validation of tool arguments failed, here content is derived from a Pydantic
      [`ValidationError`][pydantic_core.ValidationError]
    * a tool raised a [`ModelRetry`][pydantic_ai.exceptions.ModelRetry] exception
    * no tool was found for the tool name
    * the model returned plain text when a structured response was expected
    * Pydantic validation of a structured response failed, here content is derived from a Pydantic
      [`ValidationError`][pydantic_core.ValidationError]
    * a result validator raised a [`ModelRetry`][pydantic_ai.exceptions.ModelRetry] exception
    """

    content: list[pydantic_core.ErrorDetails] | str
    """Details of why and how the model should retry.

    If the retry was triggered by a [`ValidationError`][pydantic_core.ValidationError], this will be a list of
    error details.
    """

    tool_name: str | None = None
    """The name of the tool that was called, if any."""

    tool_call_id: str | None = None
    """Optional tool call identifier, this is used by some models including OpenAI."""

    timestamp: datetime = field(default_factory=_now_utc)
    """The timestamp, when the retry was triggered."""

    part_kind: Literal['retry-prompt'] = 'retry-prompt'
    """Part type identifier, this is available on all parts as a discriminator."""

    def model_response(self) -> str:
        if isinstance(self.content, str):
            description = self.content
        else:
            json_errors = error_details_ta.dump_json(self.content, exclude={'__all__': {'ctx'}}, indent=2)
            description = f'{len(self.content)} validation errors: {json_errors.decode()}'
        return f'{description}\n\nFix the errors and try again.'


ModelRequestPart = Annotated[
    Union[SystemPromptPart, UserPromptPart, ToolReturnPart, RetryPromptPart], pydantic.Discriminator('part_kind')
]
"""A message part sent by PydanticAI to a model."""


@dataclass
class ModelRequest:
    """A request generated by PydanticAI and sent to a model, e.g. a message from the PydanticAI app to the model."""

    parts: list[ModelRequestPart]
    """The parts of the user message."""

    kind: Literal['request'] = 'request'
    """Message type identifier, this is available on all parts as a discriminator."""


@dataclass
class TextPart:
    """A plain text response from a model."""

    content: str
    """The text content of the response."""

    part_kind: Literal['text'] = 'text'
    """Part type identifier, this is available on all parts as a discriminator."""


@dataclass
class ArgsJson:
    """Tool arguments as a JSON string."""

    args_json: str
    """A JSON string of arguments."""


@dataclass
class ArgsDict:
    """Tool arguments as a Python dictionary."""

    args_dict: dict[str, Any]
    """A python dictionary of arguments."""


@dataclass
class ToolCallPart:
    """A tool call from a model."""

    tool_name: str
    """The name of the tool to call."""

    args: ArgsJson | ArgsDict
    """The arguments to pass to the tool.

    Either as JSON or a Python dictionary depending on how data was returned.
    """

    tool_call_id: str | None = None
    """Optional tool call identifier, this is used by some models including OpenAI."""

    part_kind: Literal['tool-call'] = 'tool-call'
    """Part type identifier, this is available on all parts as a discriminator."""

    @classmethod
    def from_raw_args(cls, tool_name: str, args: str | dict[str, Any], tool_call_id: str | None = None) -> Self:
        """Create a `ToolCallPart` from raw arguments."""
        if isinstance(args, str):
            return cls(tool_name, ArgsJson(args), tool_call_id)
        elif isinstance(args, dict):
            return cls(tool_name, ArgsDict(args), tool_call_id)
        else:
            assert_never(args)

    def args_as_dict(self) -> dict[str, Any]:
        """Return the arguments as a Python dictionary.

        This is just for convenience with models that require dicts as input.
        """
        if isinstance(self.args, ArgsDict):
            return self.args.args_dict
        args = pydantic_core.from_json(self.args.args_json)
        assert isinstance(args, dict), 'args should be a dict'
        return cast(dict[str, Any], args)

    def args_as_json_str(self) -> str:
        """Return the arguments as a JSON string.

        This is just for convenience with models that require JSON strings as input.
        """
        if isinstance(self.args, ArgsJson):
            return self.args.args_json
        return pydantic_core.to_json(self.args.args_dict).decode()

    def has_content(self) -> bool:
        if isinstance(self.args, ArgsDict):
            return any(self.args.args_dict.values())
        else:
            return bool(self.args.args_json)


ModelResponsePart = Annotated[Union[TextPart, ToolCallPart], pydantic.Discriminator('part_kind')]
"""A message part returned by a model."""


@dataclass
class ModelResponse:
    """A response from a model, e.g. a message from the model to the PydanticAI app."""

    parts: list[ModelResponsePart]
    """The parts of the model message."""

    timestamp: datetime = field(default_factory=_now_utc)
    """The timestamp of the response.

    If the model provides a timestamp in the response (as OpenAI does) that will be used.
    """

    kind: Literal['response'] = 'response'
    """Message type identifier, this is available on all parts as a discriminator."""

    @classmethod
    def from_text(cls, content: str, timestamp: datetime | None = None) -> Self:
        return cls([TextPart(content)], timestamp=timestamp or _now_utc())

    @classmethod
    def from_tool_call(cls, tool_call: ToolCallPart) -> Self:
        return cls([tool_call])


ModelMessage = Union[ModelRequest, ModelResponse]
"""Any message send to or returned by a model."""

ModelMessagesTypeAdapter = pydantic.TypeAdapter(
    list[Annotated[ModelMessage, pydantic.Discriminator('kind')]], config=pydantic.ConfigDict(defer_build=True)
)
"""Pydantic [`TypeAdapter`][pydantic.type_adapter.TypeAdapter] for (de)serializing messages."""
