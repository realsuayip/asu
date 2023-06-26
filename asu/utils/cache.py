import functools
import operator
from collections.abc import Callable
from inspect import Parameter, signature
from typing import Any, ParamSpec, TypeVar

from django.core.cache import cache

__all__ = ["cached_context", "build_vary_key"]


P = ParamSpec("P")
RT = TypeVar("RT")


def get_argument(
    parameter: Parameter,
    name: str,
    pos: int,
    /,
    *,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Any:
    """
    Get the argument passed to `args` and `kwargs` using
    parameter metadata (name, pos, kind).
    """

    if parameter.kind == Parameter.POSITIONAL_ONLY:
        return args[pos]

    if parameter.kind == Parameter.KEYWORD_ONLY:
        return kwargs[name]

    # Not sure if the argument is positional or keyword. We'll have to
    # check both, starting with keyword arguments.
    try:
        return kwargs[name]
    except KeyError:
        try:
            return args[pos]
        except IndexError:
            default = parameter.default
            assert default is not Parameter.empty, "could not resolve %s" % name
            return default


def build_vary_key(key: str, name: str, value: str) -> str:
    return "%s.vary(%s=%s)" % (key, name, value)


def get_vary_string(
    parameter: Parameter,
    name: str,
    pos: int,
    attr: str,
    key: str,
    /,
    *,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """
    Get argument value, and compose a cache key using it. The resulting
    key will look like this:

        `key.vary(parameter_name.attr=argument)`
    """

    arg = get_argument(parameter, name, pos, args=args, kwargs=kwargs)
    if not attr:
        value = arg
    else:
        value = operator.attrgetter(attr)(arg)
        name = name + "." + attr
    return build_vary_key(key, name, value)


def fallback(key: str, *args: Any, **kwargs: Any) -> str:
    """
    Returns `key` directly in case `vary` parameter is not specified.
    """
    return key


SUPPORTED_PARAM_TYPES = (
    Parameter.KEYWORD_ONLY,
    Parameter.POSITIONAL_ONLY,
    Parameter.POSITIONAL_OR_KEYWORD,
)


def get_key_resolver(
    f: Callable[..., Any],
    /,
    *,
    key: str,
    vary: str,
) -> Callable[..., str]:
    if not vary:
        return functools.partial(fallback, key)

    try:
        lookup, attr = vary.split(".", maxsplit=1)
    except ValueError:
        lookup, attr = vary, ""
    for pos, (name, parameter) in enumerate(signature(f).parameters.items()):
        if name == lookup:
            if parameter.kind not in SUPPORTED_PARAM_TYPES:
                raise ValueError("parameter type %s is not supported." % parameter.kind)
            return functools.partial(get_vary_string, parameter, name, pos, attr, key)
    raise ValueError("no parameter named `%s` was found." % lookup)


def cached_context(
    *,
    key: str,
    timeout: float | None = None,
    vary: str = "",
) -> Callable[[Callable[P, RT]], Callable[P, RT]]:
    """
    Cache the return value of a function using the primary
    cache backend (e.g., Redis).

    :param key: Cache key to use.
    :param timeout: Timeout for cache, set `None` to cache indefinitely.
    :param vary: Specify a parameter name to vary the *cache key*
    depending on the argument. You may also specify the attributes
    of the argument. Examples: `param`, `param.attr`, `param.attr.value`.
    The argument should have proper string representation since it is
    going to be used in the cache key.

    If `vary` is specified, the resulting cache key will look like this:
        `key.vary(parameter_name.attr=argument)`
    """

    def decorator(f: Callable[P, RT]) -> Callable[P, RT]:
        get_cache_key = get_key_resolver(f, key=key, vary=vary)

        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> RT:
            cache_key = get_cache_key(args=args, kwargs=kwargs)

            from_cache: RT = cache.get(cache_key)
            if from_cache is not None:
                return from_cache

            retval = f(*args, **kwargs)
            cache.set(cache_key, retval, timeout=timeout)
            return retval

        return wrapper

    return decorator
