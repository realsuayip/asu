import functools
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from django.core.cache import cache

P = ParamSpec("P")
RT = TypeVar("RT")


def cached_context(
    *, key: str, timeout: float | None = None
) -> Callable[[Callable[P, RT]], Callable[P, RT]]:
    """
    Cache the return value of a function using the primary
    cache backend (e.g., Redis).
    """

    def decorator(f: Callable[P, RT]) -> Callable[P, RT]:
        @functools.wraps(f)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> RT:
            from_cache: RT = cache.get(key)
            if from_cache is not None:
                return from_cache

            retval = f(*args, **kwargs)
            cache.set(key, retval, timeout=timeout)
            return retval

        return wrapper

    return decorator
