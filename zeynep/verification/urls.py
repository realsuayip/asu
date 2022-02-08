from rest_framework.routers import SimpleRouter

from zeynep.verification.email.views import EmailViewSet
from zeynep.verification.registration.views import RegistrationViewSet

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
