from rest_framework.routers import DefaultRouter

from zeynep.verification.views.registration import RegistrationViewSet

router = DefaultRouter()
router.register(
    "verifications/registration",
    RegistrationViewSet,
    basename="registration-verification",
)
