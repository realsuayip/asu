from rest_framework.routers import SimpleRouter

from rest_framework_nested.routers import NestedSimpleRouter

from asu.messaging.views import ConversationViewSet, MessageViewSet

app_name = "messaging"

router = SimpleRouter()
router.register("conversations", ConversationViewSet, basename="conversation")

nested = NestedSimpleRouter(router, "conversations", lookup="conversation")
nested.register("messages", MessageViewSet, basename="message")
urlpatterns = router.urls + nested.urls
