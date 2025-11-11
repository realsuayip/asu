import types

from django.core.cache import cache

import pytest
from pytest_mock import MockerFixture

from asu.core.utils.cache import cached_context


def test_cached_context_simple(mocker: MockerFixture) -> None:
    mock = mocker.Mock()

    @cached_context(key="asu.test.my_func")
    def my_func() -> int:
        """Some function."""
        mock.compute()
        return 256

    assert my_func() == 256
    assert my_func() == 256
    mock.compute.assert_called_once()
    assert cache.get(key="asu.test.my_func") == 256
    assert my_func.__doc__ == "Some function."


def test_cached_context_pos_arg(mocker: MockerFixture) -> None:
    mock = mocker.Mock()

    @cached_context(key="asu.test.fun", vary="param")
    def fun(param, /) -> int:
        if param == 2:
            mock.compute()
        return 256 + param

    assert fun(2) == 256 + 2
    assert fun(2) == 256 + 2
    mock.compute.assert_called_once()
    assert fun(3) == 256 + 3
    assert cache.get("asu.test.fun.vary(param=2)") == 256 + 2
    assert cache.get("asu.test.fun.vary(param=3)") == 256 + 3


def test_cached_context_keyword_arg(mocker: MockerFixture) -> None:
    mock = mocker.Mock()

    @cached_context(key="asu.test.fun1", vary="param")
    def fun1(*, param) -> int:
        if param == 2:
            mock.compute()
        return 257 + param

    assert fun1(param=2) == 257 + 2
    assert fun1(param=2) == 257 + 2
    mock.compute.assert_called_once()
    assert fun1(param=3) == 257 + 3
    assert cache.get("asu.test.fun1.vary(param=2)") == 257 + 2
    assert cache.get("asu.test.fun1.vary(param=3)") == 257 + 3


def test_cached_context_keyword_or_pos_arg(mocker: MockerFixture) -> None:
    mock = mocker.Mock()

    @cached_context(key="asu.test.fun2", vary="param")
    def fun2(param) -> int:
        if param == 2:
            mock.compute()
        return 257 + param

    assert fun2(2) == 257 + 2
    assert fun2(param=2) == 257 + 2
    mock.compute.assert_called_once()
    assert fun2(param=3) == 257 + 3
    assert cache.get("asu.test.fun2.vary(param=2)") == 257 + 2
    assert cache.get("asu.test.fun2.vary(param=3)") == 257 + 3


def test_cached_context_with_attr(mocker: MockerFixture) -> None:
    mock = mocker.Mock()

    @cached_context(key="asu.test.fun4", vary="param.attr")
    def fun4(param) -> int:
        if param.attr == 2:
            mock.compute()
        return 257 + param.attr

    arg2 = types.SimpleNamespace(attr=2)
    arg3 = types.SimpleNamespace(attr=3)

    assert fun4(arg2) == 257 + 2
    assert fun4(param=arg2) == 257 + 2
    mock.compute.assert_called_once()
    assert fun4(arg3) == 257 + 3
    assert cache.get("asu.test.fun4.vary(param.attr=2)") == 257 + 2
    assert cache.get("asu.test.fun4.vary(param.attr=3)") == 257 + 3


def test_cached_context_captures_default_argument(mocker: MockerFixture) -> None:
    mock = mocker.Mock()

    @cached_context(key="asu.test.fun7", vary="param")
    def fun7(param=2) -> int:
        if param == 2:
            mock.compute()
        return 257 + param

    assert fun7() == 257 + 2
    assert fun7() == 257 + 2
    mock.compute.assert_called_once()
    assert fun7(3) == 257 + 3
    assert cache.get("asu.test.fun7.vary(param=2)") == 257 + 2
    assert cache.get("asu.test.fun7.vary(param=3)") == 257 + 3


def test_cached_context_unknown_arg() -> None:
    with pytest.raises(ValueError, match=r"no parameter named `unknown` was found."):

        @cached_context(key="asu.test.fun3", vary="unknown")
        def fun3(param) -> int:
            return 257 + param


def test_cached_context_unsupported_var_keyword() -> None:
    with pytest.raises(
        ValueError, match=r"parameter type VAR_KEYWORD is not supported."
    ):

        @cached_context(key="asu.test.fun5", vary="kwargs")
        def fun5(*args, **kwargs) -> int:
            return 258


def test_cached_context_unsupported_var_positional() -> None:
    with pytest.raises(
        ValueError, match=r"parameter type VAR_POSITIONAL is not supported."
    ):

        @cached_context(key="asu.test.fun6", vary="args")
        def fun6(*args, **kwargs) -> int:
            return 258
