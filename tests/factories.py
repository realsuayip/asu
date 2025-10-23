import factory.fuzzy
from factory.django import DjangoModelFactory
from factory.faker import Faker

from asu.auth.models import User


class UserFactory(DjangoModelFactory[User]):
    class Meta:
        model = "account.User"

    display_name = Faker("name")
    username = factory.fuzzy.FuzzyText(length=10)
    password = "hello"
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = Faker("email")
    birth_date = Faker("date")
