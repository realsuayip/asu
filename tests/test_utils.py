import types
import unittest
from unittest.mock import Mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions
from rest_framework.exceptions import ErrorDetail

from asu.utils import mailing
from asu.utils.cache import cached_context
from asu.utils.file import FileSizeValidator, MimeTypeValidator
from asu.utils.rest import exception_handler


class TestFileUtils(TestCase):
    @classmethod
    def setUpClass(cls):
        file_path = settings.BASE_DIR.parent / "tests/files/asli.jpeg"
        cls.image = open(file_path, "rb")  # noqa: SIM115

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
        with self.assertRaisesRegex(
            ValueError, "no parameter named `unknown` was found."
        ):

            @cached_context(key="asu.test.fun3", vary="unknown")
            def fun3(param) -> int:
                return 257 + param

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
        with self.assertRaisesRegex(
            ValueError, "parameter type VAR_KEYWORD is not supported."
        ):

            @cached_context(key="asu.test.fun5", vary="kwargs")
            def fun5(*args, **kwargs) -> int:
                return 258

    def test_cached_context_unsupported_var_positional(self):
        with self.assertRaisesRegex(
            ValueError, "parameter type VAR_POSITIONAL is not supported."
        ):

            @cached_context(key="asu.test.fun6", vary="args")
            def fun6(*args, **kwargs) -> int:
                return 258

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


class TestRestUtils(unittest.TestCase):
    def test_exception_handler(self):
        mapping = {
            exceptions.NotAuthenticated(): {
                "status": 401,
                "code": "not_authenticated",
                "message": exceptions.NotAuthenticated.default_detail,
            },
            exceptions.MethodNotAllowed("GET"): {
                "status": 405,
                "code": "method_not_allowed",
                "message": exceptions.MethodNotAllowed.default_detail.format(
                    method="GET"
                ),
            },
            exceptions.NotFound(): {
                "status": 404,
                "code": "not_found",
                "message": exceptions.NotFound.default_detail,
            },
            exceptions.PermissionDenied(): {
                "status": 403,
                "code": "permission_denied",
                "message": exceptions.PermissionDenied.default_detail,
            },
            exceptions.PermissionDenied(code="otp_required"): {
                "status": 403,
                "code": "otp_required",
                "message": exceptions.PermissionDenied.default_detail,
            },
            exceptions.ValidationError("some message"): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "non_field_errors": [
                        {"message": "some message", "code": "invalid"},
                    ]
                },
            },
            exceptions.ValidationError("some message", code="custom"): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "non_field_errors": [
                        {"message": "some message", "code": "custom"},
                    ]
                },
            },
            exceptions.ValidationError(["multi", "messages"]): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "non_field_errors": [
                        {"message": "multi", "code": "invalid"},
                        {"message": "messages", "code": "invalid"},
                    ]
                },
            },
            exceptions.ValidationError({"key": "value"}): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "key": [{"message": "value", "code": "invalid"}],
                },
            },
            exceptions.ValidationError({"key": "value"}, code="custom"): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "key": [{"message": "value", "code": "custom"}],
                },
            },
            exceptions.ValidationError(
                {"key": "value", "key2": ["value1", "value2"]}
            ): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "key": [
                        {"message": "value", "code": "invalid"},
                    ],
                    "key2": [
                        {"message": "value1", "code": "invalid"},
                        {"message": "value2", "code": "invalid"},
                    ],
                },
            },
            exceptions.ValidationError({"non_field_errors": ["hey you"]}): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "non_field_errors": [{"message": "hey you", "code": "invalid"}]
                },
            },
            exceptions.ValidationError(
                {
                    "key": {"value": "heyy"},
                }
            ): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "key": {
                        "value": [
                            {
                                "message": "heyy",
                                "code": "invalid",
                            }
                        ]
                    }
                },
            },
            exceptions.ValidationError(
                [
                    ErrorDetail("msg1", code="code1"),
                    ErrorDetail("msg2", code="code2"),
                ]
            ): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "non_field_errors": [
                        {"message": "msg1", "code": "code1"},
                        {"message": "msg2", "code": "code2"},
                    ]
                },
            },
            exceptions.ValidationError(
                {"key1": ErrorDetail("msg1", code="code1")},
            ): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "key1": [
                        {"message": "msg1", "code": "code1"},
                    ]
                },
            },
            exceptions.ValidationError(
                {
                    "key1": ErrorDetail("msg1", code="code1"),
                    "key2": [
                        ErrorDetail("msg2", code="code2"),
                        ErrorDetail("msg3", code="code3"),
                    ],
                },
            ): {
                "status": 400,
                "code": "invalid",
                "message": "One or more parameters to your request was invalid.",
                "errors": {
                    "key1": [
                        {"message": "msg1", "code": "code1"},
                    ],
                    "key2": [
                        {"message": "msg2", "code": "code2"},
                        {"message": "msg3", "code": "code3"},
                    ],
                },
            },
        }

        for exception, result in mapping.items():
            response = exception_handler(exception, {})
            self.assertEqual(result, response.data)


class TestMailingUtils(TestCase):
    def test_send_mail(self):
        mailing.send(
            "empty",
            title="Hello World",
            content="Howdy?",
            recipients=["someone@example.com"],
        )

        email = mail.outbox[0]

        self.assertEqual(1, len(mail.outbox))
        self.assertEqual("Hello World", email.subject)
        self.assertEqual("Howdy?", email.body.strip())
        self.assertEqual(["someone@example.com"], email.recipients())
        self.assertEqual("html", email.content_subtype)

    def test_send_mail_respects_language(self):
        mailing.send(
            "empty",
            title=_("German"),
            content=_("Swedish"),
            recipients=["someone@example.com"],
            language="tr",
        )

        email = mail.outbox[0]
        self.assertEqual("Almanca", email.subject)
        self.assertEqual("İsveççe", email.body.strip())
