from rest_framework import viewsets

import django_stubs_ext

from .reloader import *  # noqa: F403

django_stubs_ext.monkeypatch(extra_classes=[viewsets.GenericViewSet])
