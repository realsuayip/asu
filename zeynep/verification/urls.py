from rest_framework.routers import SimpleRouter

from zeynep.verification.registration.views import RegistrationViewSet

router = SimpleRouter()
router.register(
    "verifications/registration",
    RegistrationViewSet,
    basename="registration-verification",
)
