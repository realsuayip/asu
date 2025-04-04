from rest_framework.routers import SimpleRouter

from rest_framework_nested.routers import NestedSimpleRouter

from asu.messaging.views import ConversationViewSet, EventViewSet

app_name = "messaging"

router = SimpleRouter()
router.register("conversations", ConversationViewSet, basename="conversation")

nested = NestedSimpleRouter(router, "conversations", lookup="conversation")
nested.register("events", EventViewSet, basename="event")
urlpatterns = router.urls + nested.urls
