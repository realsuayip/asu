from rest_framework.routers import SimpleRouter

from asu.auth.views import FollowRequestViewSet, RelationViewSet, UserViewSet

router = SimpleRouter()

router.register(
    "users/follow-requests",
    FollowRequestViewSet,
    basename="follow-request",
)
router.register("users/relations", RelationViewSet, basename="relation")
router.register("users", UserViewSet, basename="user")
urlpatterns = router.urls
