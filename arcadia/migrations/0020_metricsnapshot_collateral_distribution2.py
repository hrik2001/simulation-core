# Generated by Django 5.0.3 on 2024-07-12 21:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arcadia', '0019_accountassets_position_distribution_usd'),
    ]

    operations = [
        migrations.AddField(
            model_name='metricsnapshot',
            name='collateral_distribution2',
            field=models.JSONField(null=True),
        ),
    ]
