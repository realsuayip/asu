from django.core.cache import cache

import pytest
from pytest_django import DjangoAssertNumQueries

from asu.core.models import ProjectVariable
from asu.core.utils.cache import build_vary_key


def test_get_value_build() -> None:
    # No `django_db` marker, so no database access.
    value = ProjectVariable.objects.get_value(name="build.BRAND")
    assert value == "asu"


@pytest.mark.django_db
def test_get_value_db(django_assert_num_queries: DjangoAssertNumQueries) -> None:
    ProjectVariable.objects.create(name="HELLO_KITTY", value="im pink")
    with django_assert_num_queries(1):
        value = ProjectVariable.objects.get_value(name="db.HELLO_KITTY")
        cached_value_1 = ProjectVariable.objects.get_value(name="db.HELLO_KITTY")
    cached_value = cache.get(
        build_vary_key(
            "variable",
            "name",
            "HELLO_KITTY",
        )
    )
    assert value == cached_value == cached_value_1 == "im pink"


@pytest.mark.django_db
def test_get_value_db_cache_invalidates_on_save(
    django_assert_num_queries: DjangoAssertNumQueries,
) -> None:
    var = ProjectVariable.objects.create(name="HELLO_KITTY", value="im pink")
    value = ProjectVariable.objects.get_value(name="db.HELLO_KITTY")
    cache_key = build_vary_key(
        "variable",
        "name",
        "HELLO_KITTY",
    )
    cached_value = cache.get(cache_key)
    assert value == cached_value == "im pink"

    var.value = "im blue"
    var.save(update_fields=["value"])

    assert cache.get(cache_key) is None
    with django_assert_num_queries(1):
        new_value = ProjectVariable.objects.get_value(name="db.HELLO_KITTY")
    cached_value = cache.get(cache_key)
    assert new_value == cached_value == "im blue"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "name,exception_msg",
    (
        ("bad.GUY", "should contain a valid prefix"),
        ("badGUY", "should contain a valid prefix"),
        ("db.IM_NOT_HERE", "could not be found in the database"),
        ("build.IM_NOT_HERE", "IM_NOT_HERE"),
    ),
)
def test_get_value_exceptions(name: str, exception_msg: str) -> None:
    with pytest.raises(KeyError, match=exception_msg):
        ProjectVariable.objects.get_value(name=name)
