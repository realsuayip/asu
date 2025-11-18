from rest_framework import viewsets

import django_stubs_ext

django_stubs_ext.monkeypatch(extra_classes=[viewsets.GenericViewSet])
