from rest_framework.routers import SimpleRouter

from zeynep.auth.views import UserViewSet

router = SimpleRouter()

router.register("users", UserViewSet, basename="user")
