from rest_framework.routers import SimpleRouter

from asu.verification.email.views import EmailViewSet
from asu.verification.password.views import PasswordResetViewSet
from asu.verification.registration.views import RegistrationViewSet

router = SimpleRouter()
router.register(
    "verifications/registration",
    RegistrationViewSet,
    basename="registration-verification",
)
router.register(
    "verifications/email",
    EmailViewSet,
    basename="email-verification",
)
router.register(
    "verifications/password-reset",
    PasswordResetViewSet,
    basename="password-reset",
)
urlpatterns = router.urls
