from collections.abc import Callable

from django.http import HttpRequest, HttpResponse


class UserActivityMiddleware:
    def __init__(self, get_response: Callable[..., HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = request.user

        if user.is_authenticated and user.is_frozen:
            user.reactivate()

        response = self.get_response(request)
        return response
