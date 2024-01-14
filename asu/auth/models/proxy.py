from django.contrib import auth


class Group(auth.models.Group):
    class Meta:
        proxy = True


class Permission(auth.models.Permission):
    class Meta:
        proxy = True
