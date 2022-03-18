from rest_framework import exceptions
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler as default_exception_handler


def exception_handler(exc, context):
    response = default_exception_handler(exc, context)

    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        # ValidationError's raised in serializer methods like create() and
        # update() should behave as if they were raised in validate().
        non_field_errors = api_settings.NON_FIELD_ERRORS_KEY

        if isinstance(exc.detail, list):
            response.data = {non_field_errors: exc.detail}
        elif isinstance(exc.detail, dict):
            detail = {}
            for key, value in exc.detail.items():
                if isinstance(value, str):
                    value = [value]
                detail[key] = value
            response.data = detail

    return response
