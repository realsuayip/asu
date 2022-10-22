# Generated by Django 4.0.1 on 2022-07-13 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("zaida_auth", "0005_userfollowrequest_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="allows_all_messages",
            field=models.BooleanField(
                default=True,
                help_text="Users that are not followed by this user can send message requests to them.",
                verbose_name="allows all incoming messages",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="allows_receipts",
            field=models.BooleanField(
                default=True, verbose_name="allows message receipts"
            ),
        ),
    ]