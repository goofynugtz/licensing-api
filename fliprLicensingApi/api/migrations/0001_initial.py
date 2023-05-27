# Generated by Django 4.2.1 on 2023-05-27 14:53

import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Policy',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=255, unique=True)),
                ('description', models.CharField(blank=True, max_length=1024, null=True)),
                ('validity', models.DurationField(blank=True, choices=[(datetime.timedelta(seconds=120), 'Minute'), (datetime.timedelta(days=1), 'Day'), (datetime.timedelta(days=7), 'Week'), (datetime.timedelta(days=28), 'Month')], null=True)),
                ('createdAt', models.DateTimeField(auto_now_add=True)),
                ('updatedAt', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name_plural': 'Policies',
            },
        ),
        migrations.CreateModel(
            name='License',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('key', models.CharField(editable=False, max_length=1024, unique=True)),
                ('public_key', models.CharField(editable=False, max_length=2048, null=True)),
                ('private_key', models.CharField(editable=False, max_length=2048, null=True)),
                ('status', models.CharField(choices=[('VALID', 'Valid'), ('SUSPENDED', 'Suspended'), ('EXPIRED', 'Expired')], default='VALID', max_length=255)),
                ('validUpto', models.DateTimeField(null=True)),
                ('updatedAt', models.DateTimeField(auto_now=True)),
                ('createdAt', models.DateTimeField(auto_now_add=True)),
                ('policy', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='api.policy')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]