# Generated by Django 4.2.7 on 2023-12-16 12:07

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ProjectVariable",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.TextField(unique=True, verbose_name="name")),
                ("value", models.JSONField(verbose_name="value")),
                (
                    "date_modified",
                    models.DateTimeField(auto_now=True, verbose_name="date modified"),
                ),
                (
                    "date_created",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="date created"
                    ),
                ),
            ],
            options={
                "verbose_name": "project variable",
                "verbose_name_plural": "project variables",
            },
        ),
    ]
