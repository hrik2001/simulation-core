# Generated by Django 5.0.3 on 2024-08-24 12:26

import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ethena', '0004_chainmetrics_dsr_rate_chainmetrics_sdai_price_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UniswapStats',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('data', models.JSONField()),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
