# Generated by Django 5.0.3 on 2024-10-11 18:35

import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ethena', '0023_alter_apymetrics_apy_alter_apymetrics_apy_base_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BuidlYieldMetrics',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('date', models.DateTimeField(unique=True)),
                ('amount', models.TextField()),
                ('apy_7d', models.TextField()),
                ('apy_30d', models.TextField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UstbYieldMetrics',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('date', models.DateTimeField(unique=True)),
                ('one_day', models.TextField()),
                ('seven_day', models.TextField()),
                ('thirty_day', models.TextField()),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
