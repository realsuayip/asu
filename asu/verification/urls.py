from django.urls import include, path

from rest_framework.routers import SimpleRouter

from asu.verification.email.views import EmailViewSet
from asu.verification.password.views import PasswordResetViewSet
from asu.verification.registration.views import RegistrationViewSet

app_name = "verification"

router = SimpleRouter()
router.register("registration", RegistrationViewSet, basename="registration")
router.register("email", EmailViewSet, basename="email-change")
router.register("password-reset", PasswordResetViewSet, basename="password-reset")
urlpatterns = [
    path("verifications/", include(router.urls)),
]
