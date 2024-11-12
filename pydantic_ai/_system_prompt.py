from __future__ import annotations as _annotations

import inspect
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Callable, Generic, cast

from . import _utils
from .call_context import call_context
from .dependencies import AgentDeps, CallContext


@dataclass
class SystemPromptRunner(Generic[AgentDeps]):
    function: Callable[[], str | Awaitable[str]]
    _is_async: bool = field(init=False)

    def __post_init__(self):
        self._is_async = inspect.iscoroutinefunction(self.function)

    async def run(self, deps: AgentDeps) -> str:
        # TODO: Need to set the agent call context appropriately when running retries, etc.; not sure where that happens
        with call_context(CallContext(deps, 0, None)):
            # Thanks to dependency injection, we can assume self.function accepts zero arguments
            # If that's wrong, the user will get a pydantic error; we should eventually the error messages
            # though.
            if self._is_async:
                function = cast(Callable[[], Awaitable[str]], self.function)
                return await function()
            else:
                function = cast(Callable[[], str], self.function)
                return await _utils.run_in_executor(function)
