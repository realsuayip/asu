from types import SimpleNamespace

import factory.fuzzy
from factory import Faker
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    class Meta:
        model = "account.User"

    display_name = Faker("name")
    username = factory.fuzzy.FuzzyText(length=10)
    password = "hello"
    first_name = Faker("first_name")
    last_name = Faker("last_name")
    email = Faker("email")
    birth_date = Faker("date")


# Behaves as if first party oauth token in the context
# of 'client.force_authenticate'
first_party_token = SimpleNamespace(
    application=SimpleNamespace(is_first_party=True)
)
