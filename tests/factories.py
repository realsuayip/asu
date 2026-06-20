import uuid

import factory.fuzzy
from factory.django import DjangoModelFactory, Password
from factory.faker import Faker

from asu.auth.models import User
from asu.verification.models import (
    EmailVerification,
    PasswordResetVerification,
    RegistrationVerification,
)
from asu.verification.models.base import Verification, get_code_hash


class UserFactory(DjangoModelFactory[User]):
    class Meta:
        model = "account.User"

    display_name = Faker("name")
    username = factory.fuzzy.FuzzyText(length=10)
    password = Password("hello")
    email = Faker("email")
    birth_date = Faker("date")


class VerificationFactory[T: Verification](DjangoModelFactory[T]):
    class Meta:
        abstract = True

    class Params:
        code = "000000"

    pk = factory.Faker("uuid7")
    code_hash = factory.LazyAttribute(
        lambda obj: get_code_hash(pk=uuid.UUID(obj.pk), code=obj.code)
    )
    email = factory.Faker("email")


class EmailVerificationFactory(VerificationFactory[EmailVerification]):
    class Meta:
        model = EmailVerification


class PasswordResetVerificationFactory(VerificationFactory[PasswordResetVerification]):
    class Meta:
        model = PasswordResetVerification


class RegistrationVerificationFactory(VerificationFactory[RegistrationVerification]):
    class Meta:
        model = RegistrationVerification
