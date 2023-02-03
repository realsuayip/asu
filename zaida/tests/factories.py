import factory.fuzzy
from factory import Faker
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = "zaida_auth.User"

    display_name = Faker("name")
    username = factory.fuzzy.FuzzyText(length=10)
    password = "hello"
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = Faker("email")
    birth_date = Faker("date")
