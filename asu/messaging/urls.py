from rest_framework_nested import routers

from asu.messaging.views import ConversationViewSet, MessageViewSet

router = routers.SimpleRouter()
router.register("conversations", ConversationViewSet, basename="conversation")

conversation_router = routers.NestedSimpleRouter(
    router, "conversations", lookup="conversation"
)
conversation_router.register("messages", MessageViewSet, basename="message")
api_urlpatterns = conversation_router.urls
