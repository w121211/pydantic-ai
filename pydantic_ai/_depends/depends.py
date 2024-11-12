from collections.abc import AsyncIterator, Iterator
from contextlib import AsyncExitStack, ExitStack
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    TypeVar,
    cast,
    overload,
)

from typing_extensions import ParamSpec

from .build import build_call_model
from .models import CallModel, Depends as DependsType
from .provider import Provider, dependency_provider

P = ParamSpec('P')
T = TypeVar('T')


def Depends(
    dependency: Callable[P, T],
    *,
    use_cache: bool = True,
) -> T:
    result = DependsType(dependency=dependency, use_cache=use_cache)
    # We lie about the return type here to get better type-checking
    return result  # type: ignore


@overload
def inject(
    *,
    dependency_overrides_provider: Provider | None = dependency_provider,
) -> Callable[[Callable[P, T]], Callable[P, T]]: ...


@overload
def inject(
    func: Callable[P, T],
) -> Callable[P, T]: ...


def inject(
    func: Callable[P, T] | None = None,
    dependency_overrides_provider: Provider | None = dependency_provider,
) -> Callable[[Callable[P, T]], Callable[P, T]] | Callable[P, T]:
    if func is None:

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            return _inject_decorator(func, dependency_overrides_provider)

        return decorator

    return _inject_decorator(func, dependency_overrides_provider)


def _inject_decorator(
    func: Callable[P, T], dependency_overrides_provider: Provider | None = dependency_provider
) -> Callable[P, T]:
    overrides: dict[Callable[..., Any], Callable[..., Any]] | None = (
        dependency_overrides_provider.dependency_overrides if dependency_overrides_provider else None
    )

    def func_wrapper(func: Callable[P, T]) -> Callable[P, T]:
        call_model = build_call_model(call=func)

        if call_model.is_async:
            if call_model.is_generator:
                return partial(solve_async_gen, call_model, overrides)  # type: ignore[assignment]

            else:

                @wraps(func)
                async def async_injected_wrapper(*args: P.args, **kwargs: P.kwargs):
                    async with AsyncExitStack() as stack:
                        r = await call_model.asolve(
                            args=args,
                            kwargs=kwargs,
                            stack=stack,
                            dependency_overrides=overrides,
                            cache_dependencies={},
                            nested=False,
                        )
                        return r
                    raise AssertionError('unreachable')

                return async_injected_wrapper  # type: ignore  #

        else:
            if call_model.is_generator:
                return partial(solve_gen, call_model, overrides)  # type: ignore[assignment]

            else:

                @wraps(func)
                def sync_injected_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                    with ExitStack() as stack:
                        r = call_model.solve(
                            args=args,
                            kwargs=kwargs,
                            stack=stack,
                            dependency_overrides=overrides,
                            cache_dependencies={},
                            nested=False,
                        )
                        return r
                    raise AssertionError('unreachable')

                return sync_injected_wrapper

    return func_wrapper(func)


class solve_async_gen:
    _iter: AsyncIterator[Any] | None = None

    def __init__(
        self,
        model: 'CallModel[..., Any]',
        overrides: dict[Any, Any] | None,
        *args: Any,
        **kwargs: Any,
    ):
        self.call = model
        self.args = args
        self.kwargs = kwargs
        self.overrides = overrides

    def __aiter__(self) -> 'solve_async_gen':
        self._iter = None
        self.stack = AsyncExitStack()
        return self

    async def __anext__(self) -> Any:
        if self._iter is None:
            stack = self.stack = AsyncExitStack()
            await self.stack.__aenter__()
            self._iter = cast(
                AsyncIterator[Any],
                (
                    await self.call.asolve(
                        *self.args,
                        stack=stack,
                        dependency_overrides=self.overrides,
                        cache_dependencies={},
                        nested=False,
                        **self.kwargs,
                    )
                ).__aiter__(),
            )

        try:
            r = await self._iter.__anext__()
        except StopAsyncIteration as e:
            await self.stack.__aexit__(None, None, None)
            raise e
        else:
            return r


class solve_gen:
    _iter: Iterator[Any] | None = None

    def __init__(
        self,
        model: 'CallModel[..., Any]',
        overrides: dict[Any, Any] | None,
        *args: Any,
        **kwargs: Any,
    ):
        self.call = model
        self.args = args
        self.kwargs = kwargs
        self.overrides = overrides

    def __iter__(self) -> 'solve_gen':
        self._iter = None
        self.stack = ExitStack()
        return self

    def __next__(self) -> Any:
        if self._iter is None:
            stack = self.stack = ExitStack()
            self.stack.__enter__()
            self._iter = cast(
                Iterator[Any],
                iter(
                    self.call.solve(
                        args=self.args,
                        kwargs=self.kwargs,
                        stack=stack,
                        dependency_overrides=self.overrides,
                        cache_dependencies={},
                        nested=False,
                    )
                ),
            )

        try:
            r = next(self._iter)
        except StopIteration as e:
            self.stack.__exit__(None, None, None)
            raise e
        else:
            return r
