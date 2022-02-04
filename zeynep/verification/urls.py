from rest_framework.routers import DefaultRouter

from zeynep.verification.registration.views import RegistrationViewSet

router = DefaultRouter()
router.register(
    "verifications/registration",
    RegistrationViewSet,
    basename="registration-verification",
)
