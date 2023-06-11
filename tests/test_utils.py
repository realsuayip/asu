import types
from unittest.mock import Mock

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from asu.utils.cache import cached_context
from asu.utils.file import FileSizeValidator, MimeTypeValidator


class TestFileUtils(TestCase):
    @classmethod
    def setUpClass(cls):
        file_path = settings.BASE_DIR.parent / "tests/files/asli.jpeg"
        cls.image = open(file_path, "rb")

    @classmethod
    def tearDownClass(cls):
        cls.image.close()

    def test_mimetype_validator(self):
        validate = MimeTypeValidator(allowed_types=["image/jpeg"])
        validate(self.image)

        validate.allowed_types = ["image/png"]
        with self.assertRaises(ValidationError):
            validate(self.image)

        invalid_image = SimpleUploadedFile("test.png", b"test", "image/png")
        with self.assertRaises(ValidationError):
            validate(invalid_image)

    def test_filesize_validator(self):
        validate = FileSizeValidator(max_size=16400)
        image = SimpleUploadedFile(
            self.image.name,
            self.image.read(),
            content_type="image/jpeg",
        )
        validate(image)

        validate.max_size = 11200
        with self.assertRaises(ValidationError):
            validate(image)


class TestCacheUtils(TestCase):
    def test_cached_context_simple(self):
        mock = Mock()

        @cached_context(key="asu.test.my_func")
        def my_func() -> int:
            """Some function."""
            mock.compute()
            return 256

        self.assertEqual(256, my_func())
        self.assertEqual(256, my_func())
        mock.compute.assert_called_once()
        self.assertEqual(256, cache.get("asu.test.my_func"))
        self.assertEqual("Some function.", my_func.__doc__)

    def test_cached_context_pos_arg(self):
        mock = Mock()

        @cached_context(key="asu.test.fun", vary="param")
        def fun(param, /) -> int:
            if param == 2:
                mock.compute()
            return 256 + param

        self.assertEqual(256 + 2, fun(2))
        self.assertEqual(256 + 2, fun(2))
        mock.compute.assert_called_once()
        self.assertEqual(256 + 3, fun(3))

        self.assertEqual(256 + 2, cache.get("asu.test.fun.vary(param=2)"))
        self.assertEqual(256 + 3, cache.get("asu.test.fun.vary(param=3)"))

    def test_cached_context_keyword_arg(self):
        mock = Mock()

        @cached_context(key="asu.test.fun1", vary="param")
        def fun1(*, param) -> int:
            if param == 2:
                mock.compute()
            return 257 + param

        self.assertEqual(257 + 2, fun1(param=2))
        self.assertEqual(257 + 2, fun1(param=2))
        mock.compute.assert_called_once()
        self.assertEqual(257 + 3, fun1(param=3))

        self.assertEqual(257 + 2, cache.get("asu.test.fun1.vary(param=2)"))
        self.assertEqual(257 + 3, cache.get("asu.test.fun1.vary(param=3)"))

    def test_cached_context_keyword_or_pos_arg(self):
        mock = Mock()

        @cached_context(key="asu.test.fun2", vary="param")
        def fun2(param) -> int:
            if param == 2:
                mock.compute()
            return 257 + param

        self.assertEqual(257 + 2, fun2(2))
        self.assertEqual(257 + 2, fun2(param=2))
        mock.compute.assert_called_once()
        self.assertEqual(257 + 3, fun2(param=3))

        self.assertEqual(257 + 2, cache.get("asu.test.fun2.vary(param=2)"))
        self.assertEqual(257 + 3, cache.get("asu.test.fun2.vary(param=3)"))

    def test_cached_context_unknown_arg(self):
        try:

            @cached_context(key="asu.test.fun3", vary="unknown")
            def fun3(param) -> int:
                return 257 + param

        except ValueError as exc:
            self.assertEqual("no parameter named `unknown` was found.", str(exc))
        else:
            self.fail("missing exception for unknown parameter")

    def test_cached_context_with_attr(self):
        mock = Mock()

        @cached_context(key="asu.test.fun4", vary="param.attr")
        def fun4(param) -> int:
            if param.attr == 2:
                mock.compute()
            return 257 + param.attr

        arg2 = types.SimpleNamespace(attr=2)
        arg3 = types.SimpleNamespace(attr=3)

        self.assertEqual(257 + 2, fun4(arg2))
        self.assertEqual(257 + 2, fun4(param=arg2))
        mock.compute.assert_called_once()
        self.assertEqual(257 + 3, fun4(param=arg3))

        self.assertEqual(257 + 2, cache.get("asu.test.fun4.vary(param.attr=2)"))
        self.assertEqual(257 + 3, cache.get("asu.test.fun4.vary(param.attr=3)"))

    def test_cached_context_unsupported_var_keyword(self):
        try:

            @cached_context(key="asu.test.fun5", vary="kwargs")
            def fun5(*args, **kwargs) -> int:
                return 258

        except ValueError as exc:
            self.assertEqual("parameter type VAR_KEYWORD is not supported.", str(exc))
        else:
            self.fail("missing exception for unsupported parameter")

    def test_cached_context_unsupported_var_positional(self):
        try:

            @cached_context(key="asu.test.fun6", vary="args")
            def fun6(*args, **kwargs) -> int:
                return 258

        except ValueError as exc:
            self.assertEqual(
                "parameter type VAR_POSITIONAL is not supported.", str(exc)
            )
        else:
            self.fail("missing exception for unsupported parameter")

    def test_cached_context_captures_default_argument(self):
        mock = Mock()

        @cached_context(key="asu.test.fun7", vary="param")
        def fun7(param=2) -> int:
            if param == 2:
                mock.compute()
            return 257 + param

        self.assertEqual(257 + 2, fun7())
        self.assertEqual(257 + 2, fun7())
        mock.compute.assert_called_once()
        self.assertEqual(257 + 3, fun7(3))

        self.assertEqual(257 + 2, cache.get("asu.test.fun7.vary(param=2)"))
        self.assertEqual(257 + 3, cache.get("asu.test.fun7.vary(param=3)"))
