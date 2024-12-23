from __future__ import annotations as _annotations

import asyncio
from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Protocol

from typing_extensions import Self

from .result import ResultData
from .tools import AgentDeps, RunContext

if TYPE_CHECKING:
    from logfire import LogfireSpan as _LogfireSpan

    from .agent import Agent

__all__ = 'get_observer', 'AbstractAgentObserver', 'AbstractSpan'


# noinspection PyTypeChecker
def get_observer(
    agent: Agent[AgentDeps, ResultData], run_context: RunContext[AgentDeps]
) -> AbstractAgentObserver[AgentDeps, ResultData]:
    """Get an observer for the agent."""
    if _LogfireAgentObserver is not None:  # pyright: ignore[reportUnnecessaryComparison]
        return _LogfireAgentObserver(agent, run_context)
    else:
        return _NoOpAgentObserver(agent, run_context)


class AbstractSpan(Protocol):
    """Abstract definition of a span for tracing the progress of an agent run."""

    def __enter__(self) -> AbstractSpan: ...

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any
    ) -> None: ...

    def set_attribute(self, key: str, value: Any) -> None: ...

    @property
    def message(self) -> str: ...

    @message.setter
    def message(self, message: str) -> None: ...


@dataclass
class AbstractAgentObserver(ABC, Generic[AgentDeps, ResultData]):
    """Abstract bae class of an observer to monitor the progress of an agent run."""

    agent: Agent[AgentDeps, ResultData]
    run_context: RunContext[AgentDeps]

    def run(self, *, stream: bool) -> AbstractSpan:
        return NoOpSpan()

    def prepare_model(self) -> AbstractSpan:
        return NoOpSpan()

    def model_request(self) -> AbstractSpan:
        return NoOpSpan()

    def handle_model_response(self) -> AbstractSpan:
        return NoOpSpan()

    def run_tools(self, tasks: list[asyncio.Task[Any]]) -> AbstractSpan:
        return NoOpSpan()


@dataclass
class _CompoundSpan(AbstractSpan):
    _spans: list[AbstractSpan]

    def __enter__(self) -> Self:
        for span in self._spans:
            span.__enter__()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any) -> None:
        for span in reversed(self._spans):
            span.__exit__(exc_type, exc_value, traceback)

    def set_attribute(self, key: str, value: Any) -> None:
        for span in self._spans:
            span.set_attribute(key, value)

    # noinspection PyProtocol
    @property
    def message(self) -> str:
        return next((span.message for span in self._spans if span.message), '')

    @message.setter
    def message(self, message: str) -> None:
        for span in self._spans:
            span.message = message


@dataclass
class _CompoundAgentObserver(AbstractAgentObserver[AgentDeps, ResultData]):  # type: ignore
    _observers: list[AbstractAgentObserver[AgentDeps, ResultData]]

    def run(self, *, stream: bool) -> AbstractSpan:
        spans = [observer.run(stream=stream) for observer in self._observers]
        return _CompoundSpan(spans)

    def prepare_model(self) -> AbstractSpan:
        spans = [observer.prepare_model() for observer in self._observers]
        return _CompoundSpan(spans)

    def model_request(self) -> AbstractSpan:
        spans = [observer.model_request() for observer in self._observers]
        return _CompoundSpan(spans)

    def handle_model_response(self) -> AbstractSpan:
        spans = [observer.handle_model_response() for observer in self._observers]
        return _CompoundSpan(spans)

    def run_tools(self, tasks: list[asyncio.Task[Any]]) -> AbstractSpan:
        spans = [observer.run_tools(tasks) for observer in self._observers]
        return _CompoundSpan(spans)


class _NoOpAgentObserver(AbstractAgentObserver[AgentDeps, ResultData]):
    pass


try:
    # noinspection PyUnresolvedReferences
    from logfire import Logfire as _Logfire
except ImportError:
    _LogfireAgentObserver = None  # pyright: ignore[reportAssignmentType]
else:
    _logfire = _Logfire(otel_scope='pydantic-ai')

    class _LogfireAgentObserver(AbstractAgentObserver[AgentDeps, ResultData]):
        def run(self, *, stream: bool) -> _LogfireSpan:
            return _logfire.span(
                '{agent_name} run stream {prompt=}' if stream else '{agent_name} run {prompt=}',
                prompt=self.run_context.prompt,
                agent=self.agent,
                model_selection_mode=self.run_context.model_selection_mode,
                model_name=self.run_context.model.name(),
                agent_name=self.agent.name or 'agent',
                stream=stream,
            )

        def prepare_model(self) -> _LogfireSpan:
            return _logfire.span('preparing model and tools {run_step=}', run_step=self.run_context.run_step)

        def model_request(self) -> _LogfireSpan:
            return _logfire.span('model request')

        def handle_model_response(self) -> _LogfireSpan:
            return _logfire.span('handle model response')

        def run_tools(self, tasks: list[asyncio.Task[Any]]) -> _LogfireSpan:
            return _logfire.span('running {tools=}', tools=[t.get_name() for t in tasks])


class NoOpSpan(AbstractSpan):
    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: Any) -> None:
        pass

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    # noinspection PyProtocol
    @property
    def message(self) -> str:
        return ''

    @message.setter
    def message(self, message: str) -> None:
        pass
