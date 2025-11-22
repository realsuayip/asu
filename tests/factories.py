import factory.fuzzy
from factory.django import DjangoModelFactory, Password
from factory.faker import Faker

from asu.auth.models import User


class UserFactory(DjangoModelFactory[User]):
    class Meta:
        model = "account.User"

    display_name = Faker("name")
    username = factory.fuzzy.FuzzyText(length=10)
    password = Password("hello")
    email = Faker("email")
    birth_date = Faker("date")
