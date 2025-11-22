from django.core.cache import cache
from django.test import override_settings
from django.test.client import Client
from django.urls import reverse

import pytest

from asu.auth.models import Session, User
from asu.auth.sessions.cached_db import KEY_PREFIX


@pytest.mark.django_db
def test_session_anonymous() -> None:
    client = Client()
    client.get(
        reverse("two_factor:login"),
        headers={"User-Agent": "TestAgent/1.0"},
    )
    session = Session.objects.get(session_key=client.session.session_key)
    assert session.user is None
    assert session.user_agent == "TestAgent/1.0"
    assert session.ip == "127.0.0.1"


@pytest.mark.django_db
def test_session_authenticated(user: User) -> None:
    client = Client()
    client.force_login(user)
    client.get(
        reverse("two_factor:login"),
        headers={"User-Agent": "TestAgent/2.0"},
    )
    session = Session.objects.get(session_key=client.session.session_key)
    assert session.user_id == user.pk
    assert session.user_agent == "TestAgent/2.0"
    assert session.ip == "127.0.0.1"


@pytest.mark.django_db
def test_user_revoke_all_sessions(user: User) -> None:
    keys = []
    for _ in range(3):
        client = Client()
        client.force_login(user)
        keys.append(client.session.session_key)

    sessions = Session.objects.filter(session_key__in=keys)
    assert sessions.count() == 3

    user.revoke_all_sessions()
    assert sessions.count() == 0


@pytest.mark.django_db
@override_settings(SESSION_ENGINE="asu.auth.sessions.cached_db")
def test_user_revoke_all_sessions_case_cached_db(user: User):
    keys = []
    for _ in range(3):
        client = Client()
        client.force_login(user)
        keys.append(client.session.session_key)

    sessions = Session.objects.filter(session_key__in=keys)
    assert sessions.count() == 3
    for key in keys:
        assert cache.get(KEY_PREFIX + key) is not None

    user.revoke_all_sessions()
    assert sessions.count() == 0
    for key in keys:
        assert cache.get(KEY_PREFIX + key) is None
