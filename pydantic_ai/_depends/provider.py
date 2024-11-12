from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, cast

_sentinel = object()


@dataclass
class Provider:
    dependency_overrides: dict[Callable[..., Any], Callable[..., Any]] = field(default_factory=dict)

    def clear(self) -> None:
        self.dependency_overrides = {}

    def override(
        self,
        original: Callable[..., Any],
        override: Callable[..., Any],
    ) -> None:
        self.dependency_overrides[original] = override

    @contextmanager
    def scope(
        self,
        original: Callable[..., Any],
        override: Callable[..., Any],
    ) -> Iterator[None]:
        before_scope = self.dependency_overrides.pop(original, _sentinel)
        self.dependency_overrides[original] = override
        try:
            yield
        finally:
            if before_scope is _sentinel:
                self.dependency_overrides.pop(original, None)
            else:
                self.dependency_overrides[original] = cast(Callable[..., Any], before_scope)


dependency_provider = Provider()  # default provider
