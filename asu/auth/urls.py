from rest_framework.routers import SimpleRouter

from asu.auth.views import FollowRequestViewSet, UserViewSet

app_name = "auth"

router = SimpleRouter()

router.register(
    "users/follow-requests",
    FollowRequestViewSet,
    basename="follow-request",
)
router.register("users", UserViewSet, basename="user")
urlpatterns = router.urls
