# Generated by Django 4.0.1 on 2022-04-12 21:01

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zeynep_auth', '0003_alter_user_managers'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='description',
            field=models.TextField(blank=True, validators=[django.core.validators.MaxLengthValidator(140)], verbose_name='description'),
        ),
        migrations.AddField(
            model_name='user',
            name='website',
            field=models.URLField(blank=True, verbose_name='website'),
        ),
        migrations.AlterField(
            model_name='user',
            name='username',
            field=models.CharField(max_length=16, unique=True, validators=[django.core.validators.MinLengthValidator(3), django.core.validators.RegexValidator(message='Usernames can only contain latin letters, numerals and underscores. Trailing, leading or consecutive underscores are not allowed.', regex='^[a-z0-9]+(_[a-z0-9]+)*$')], verbose_name='username'),
        ),
    ]