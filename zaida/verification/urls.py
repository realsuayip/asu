from rest_framework.routers import SimpleRouter

from zaida.verification.email.views import EmailViewSet
from zaida.verification.password.views import PasswordResetViewSet
from zaida.verification.registration.views import RegistrationViewSet

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
