from __future__ import annotations as _annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import (
    Any,
)

from .dependencies import CallContext

_CALL_CONTEXT_VAR: ContextVar[CallContext[Any]] = ContextVar('AgentCallContext')


def get_call_context() -> CallContext[Any]:
    """A helper to get the current agent call context. Can be used with Depends(...)."""
    return _CALL_CONTEXT_VAR.get()


@contextmanager
def call_context(ctx: CallContext[Any]):
    """Temporarily set the agent call context for the duration of the context manager."""
    token = _CALL_CONTEXT_VAR.set(ctx)
    try:
        yield
    finally:
        _CALL_CONTEXT_VAR.reset(token)
