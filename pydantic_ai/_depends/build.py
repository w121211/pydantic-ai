import inspect
from collections.abc import Awaitable
from typing import (
    Annotated,
    Any,
    Callable,
    TypeVar,
    Union,
)

from typing_extensions import (
    ParamSpec,
    get_args,
    get_origin,
)

from .models import CallModel, Depends as DependsType
from .utils import (
    get_evaluated_signature,
    is_async_gen_callable,
    is_coroutine_callable,
    is_gen_callable,
)

P = ParamSpec('P')
T = TypeVar('T')


def build_call_model(  # noqa C901
    call: Union[
        Callable[P, T],
        Callable[P, Awaitable[T]],
    ],
    *,
    use_cache: bool = True,
    is_sync: bool | None = None,
) -> CallModel[P, T]:
    name = getattr(call, '__name__', type(call).__name__)

    is_call_async = is_coroutine_callable(call) or is_async_gen_callable(call)
    if is_sync is None:
        is_sync = not is_call_async
    else:
        assert not (is_sync and is_call_async), f'You cannot use async dependency `{name}` at sync main'
    is_call_generator = is_gen_callable(call)

    signature = get_evaluated_signature(call)

    class_fields: dict[str, tuple[Any, Any]] = {}
    dependencies: dict[str, CallModel[..., Any]] = {}
    positional_args: list[str] = []
    keyword_args: list[str] = []
    var_positional_arg: str | None = None
    var_keyword_arg: str | None = None

    for param_name, param in signature.parameters.items():
        dep: DependsType | None = None

        if param.annotation is inspect.Parameter.empty:
            annotation = Any
        else:
            annotation = param.annotation

        if get_origin(param.annotation) is Annotated:
            annotated_args = get_args(param.annotation)
            for arg in annotated_args[1:]:
                if isinstance(arg, DependsType):
                    if dep:
                        raise ValueError(f'Cannot specify multiple `Depends` arguments for `{param_name}`!')
                    dep = arg

        default: Any
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            default = ()
            var_positional_arg = param_name
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            default = {}
            var_keyword_arg = param_name
        elif param.default is inspect.Parameter.empty:
            default = inspect.Parameter.empty
        else:
            default = param.default

        if isinstance(default, DependsType):
            if dep:
                raise ValueError(f'Cannot use `Depends` with `Annotated` and a default value for `{param_name}`!')
            dep, default = default, inspect.Parameter.empty

        else:
            class_fields[param_name] = (annotation, default)

        if dep:
            dependencies[param_name] = build_call_model(
                dep.dependency,
                use_cache=dep.use_cache,
                is_sync=is_sync,
            )

            keyword_args.append(param_name)

        else:
            if param.kind is param.KEYWORD_ONLY:
                keyword_args.append(param_name)
            elif param.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                positional_args.append(param_name)

    return CallModel(
        call=call,
        params=class_fields,
        use_cache=use_cache,
        is_async=is_call_async,
        is_generator=is_call_generator,
        dependencies=dependencies,
        positional_args=positional_args,
        keyword_args=keyword_args,
        var_positional_arg=var_positional_arg,
        var_keyword_arg=var_keyword_arg,
    )
