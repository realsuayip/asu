from rest_framework.routers import SimpleRouter

from asu.auth.views import FollowRequestViewSet, UserViewSet

router = SimpleRouter()

router.register(
    "users/follow-requests",
    FollowRequestViewSet,
    basename="follow-request",
)
router.register("users", UserViewSet, basename="user")
