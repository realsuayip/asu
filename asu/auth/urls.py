from django.urls import include, path

from rest_framework.routers import SimpleRouter

from asu.auth.views import FollowRequestViewSet, UserViewSet

app_name = "auth"

router = SimpleRouter(use_regex_path=False)
router.register("follow-requests", FollowRequestViewSet, basename="follow-request")
router.register("", UserViewSet, basename="user")
urlpatterns = [
    path("users/", include(router.urls)),
]
