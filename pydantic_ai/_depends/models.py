from collections.abc import Awaitable, Generator, Iterable, Sequence
from contextlib import AsyncExitStack, ExitStack
from dataclasses import dataclass
from inspect import Parameter, unwrap
from typing import (
    Any,
    Callable,
    Generic,
    TypeVar,
    Union,
)

from typing_extensions import ParamSpec

from .utils import (
    is_async_gen_callable,
    is_coroutine_callable,
    is_gen_callable,
    run_async,
    solve_generator_async,
    solve_generator_sync,
)

P = ParamSpec('P')
T = TypeVar('T')


@dataclass
class Depends:
    dependency: Callable[..., Any]
    use_cache: bool = True


class CallModel(Generic[P, T]):
    call: Union[
        Callable[P, T],
        Callable[P, Awaitable[T]],
    ]
    is_async: bool
    is_generator: bool

    params: dict[str, tuple[Any, Any]]

    dependencies: dict[str, 'CallModel[..., Any]']
    sorted_dependencies: tuple[tuple['CallModel[..., Any]', int], ...]
    keyword_args: tuple[str, ...]
    positional_args: tuple[str, ...]
    var_positional_arg: str | None
    var_keyword_arg: str | None

    use_cache: bool

    __slots__ = (
        'call',
        'is_async',
        'is_generator',
        'params',
        'dependencies',
        'sorted_dependencies',
        'keyword_args',
        'positional_args',
        'var_positional_arg',
        'var_keyword_arg',
        'use_cache',
    )

    @property
    def call_name(self) -> str:
        call = unwrap(self.call)
        return getattr(call, '__name__', type(call).__name__)

    @property
    def flat_params(self) -> dict[str, tuple[Any, Any]]:
        params = self.params
        for d in self.dependencies.values():
            params.update(d.flat_params)
        return params

    @property
    def flat_dependencies(
        self,
    ) -> dict[
        Callable[..., Any],
        tuple[
            'CallModel[..., Any]',
            tuple[Callable[..., Any], ...],
        ],
    ]:
        flat: dict[
            Callable[..., Any],
            tuple[
                CallModel[..., Any],
                tuple[Callable[..., Any], ...],
            ],
        ] = {}

        for i in self.dependencies.values():
            flat.update(
                {
                    i.call: (
                        i,
                        tuple(j.call for j in i.dependencies.values()),
                    )
                }
            )

            flat.update(i.flat_dependencies)

        return flat

    def __init__(
        self,
        *,
        call: Union[
            Callable[P, T],
            Callable[P, Awaitable[T]],
        ],
        params: dict[str, tuple[Any, Any]],
        use_cache: bool = True,
        is_async: bool = False,
        is_generator: bool = False,
        dependencies: dict[str, 'CallModel[..., Any]'] | None = None,
        keyword_args: list[str] | None = None,
        positional_args: list[str] | None = None,
        var_positional_arg: str | None = None,
        var_keyword_arg: str | None = None,
    ):
        self.call = call

        self.keyword_args = tuple(keyword_args or ())
        self.positional_args = tuple(positional_args or ())
        self.var_positional_arg = var_positional_arg
        self.var_keyword_arg = var_keyword_arg
        self.use_cache = use_cache
        self.is_async = is_async or is_coroutine_callable(call) or is_async_gen_callable(call)
        self.is_generator = is_generator or is_gen_callable(call) or is_async_gen_callable(call)

        self.dependencies = dependencies or {}

        sorted_dep: list[CallModel[..., Any]] = []
        flat = self.flat_dependencies
        for calls in flat.values():
            _sort_dep(sorted_dep, calls, flat)

        for name in self.dependencies.keys():
            params.pop(name, None)
        self.params = params

    def _solve(  # noqa C901
        self,
        *,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        cache_dependencies: dict[
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
            T,
        ],
        dependency_overrides: dict[
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
        ]
        | None = None,
    ) -> Generator[
        tuple[
            tuple[Any, ...],
            dict[str, Any],
            Callable[..., Any],
        ],
        Any,
        T,
    ]:
        if dependency_overrides:
            call = dependency_overrides.get(self.call, self.call)
            assert self.is_async or not is_coroutine_callable(
                call
            ), f'You cannot use async dependency `{self.call_name}` at sync main'

        else:
            call = self.call

        if self.use_cache and call in cache_dependencies:
            return cache_dependencies[call]

        kw: dict[str, Any] = {}

        for arg in self.keyword_args:
            if (v := kwargs.pop(arg, Parameter.empty)) is not Parameter.empty:
                kw[arg] = v

        if self.var_keyword_arg is not None:
            kw[self.var_keyword_arg] = kwargs
        else:
            kw.update(kwargs)

        positional_arg_index = 0
        for arg in self.positional_args:
            if args:
                kw[arg], args = args[0], args[1:]
                positional_arg_index += 1
            else:
                break

        keyword_args: Iterable[str]
        if self.var_positional_arg is not None:
            kw[self.var_positional_arg] = args
            keyword_args = self.keyword_args
        else:
            if args:
                remaining_args = (self.positional_args + self.keyword_args)[positional_arg_index:]
                for name, arg in zip(remaining_args, args):
                    kw[name] = arg

            keyword_args = self.keyword_args + self.positional_args
            for arg in keyword_args:
                if arg in self.params:
                    default = self.params[arg][1]
                    if default is not Parameter.empty:
                        kw[arg] = self.params[arg][1]

                if not args:
                    break

                if arg not in self.dependencies:
                    kw[arg], args = args[0], args[1:]

        solved_kw: dict[str, Any]
        solved_kw = yield args, kw, call

        args_: Sequence[Any]

        kwargs_ = {arg: solved_kw[arg] for arg in keyword_args if arg in solved_kw}

        if self.var_positional_arg is not None:
            args_ = tuple(map(solved_kw.get, self.positional_args))
        else:
            args_ = ()

        response: T
        response = yield args_, kwargs_, call

        if self.use_cache:  # pragma: no branch
            cache_dependencies[call] = response

        return response

    def solve(
        self,
        *,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        stack: ExitStack,
        cache_dependencies: dict[
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
            T,
        ],
        dependency_overrides: dict[
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
        ]
        | None = None,
        nested: bool = False,
    ) -> T:
        cast_gen = self._solve(
            args=args,
            kwargs=kwargs,
            cache_dependencies=cache_dependencies,
            dependency_overrides=dependency_overrides,
        )
        try:
            args, kwargs, _ = next(cast_gen)
        except StopIteration as e:
            cached_value: T = e.value
            return cached_value

        for dep_arg, dep in self.dependencies.items():
            if not nested and dep_arg in kwargs:
                continue
            kwargs[dep_arg] = dep.solve(
                args=(),
                kwargs=kwargs,
                stack=stack,
                cache_dependencies=cache_dependencies,
                dependency_overrides=dependency_overrides,
                nested=True,
            )

        final_args, final_kwargs, call = cast_gen.send(kwargs)

        if self.is_generator and nested:
            response = solve_generator_sync(
                sub_args=final_args,
                sub_values=final_kwargs,
                call=call,
                stack=stack,
            )

        else:
            response = call(*final_args, **final_kwargs)

        try:
            cast_gen.send(response)
        except StopIteration as e:
            value: T = e.value
            return value

        raise AssertionError('unreachable')

    async def asolve(
        self,
        *,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        stack: AsyncExitStack,
        cache_dependencies: dict[
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
            T,
        ],
        dependency_overrides: dict[
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
            Union[
                Callable[P, T],
                Callable[P, Awaitable[T]],
            ],
        ]
        | None = None,
        nested: bool = False,
    ) -> T:
        cast_gen = self._solve(
            args=args,
            kwargs=kwargs,
            cache_dependencies=cache_dependencies,
            dependency_overrides=dependency_overrides,
        )
        try:
            args, kwargs, _ = next(cast_gen)
        except StopIteration as e:
            cached_value: T = e.value
            return cached_value

        for dep_arg, dep in self.dependencies.items():
            if not nested and dep_arg in kwargs:
                continue
            kwargs[dep_arg] = await dep.asolve(
                args=args,
                kwargs=kwargs,
                stack=stack,
                cache_dependencies=cache_dependencies,
                dependency_overrides=dependency_overrides,
                nested=True,
            )

        final_args, final_kwargs, call = cast_gen.send(kwargs)

        if self.is_generator and nested:
            response = await solve_generator_async(
                final_args,
                final_kwargs,
                call=call,
                stack=stack,
            )
        else:
            response = await run_async(call, *final_args, **final_kwargs)

        try:
            cast_gen.send(response)
        except StopIteration as e:
            value: T = e.value
            return value

        raise AssertionError('unreachable')


def _sort_dep(
    collector: list['CallModel[..., Any]'],
    items: tuple[
        'CallModel[..., Any]',
        tuple[Callable[..., Any], ...],
    ],
    flat: dict[
        Callable[..., Any],
        tuple[
            'CallModel[..., Any]',
            tuple[Callable[..., Any], ...],
        ],
    ],
) -> None:
    model, calls = items

    if model in collector:
        return

    if not calls:
        position = -1

    else:
        for i in calls:
            sub_model, _ = flat[i]
            if sub_model not in collector:  # pragma: no branch
                _sort_dep(collector, flat[i], flat)

        position = max(collector.index(flat[i][0]) for i in calls)

    collector.insert(position + 1, model)
