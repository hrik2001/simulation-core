# Generated by Django 5.0.3 on 2024-07-03 06:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('arcadia', '0013_accountassets_liquidation_value_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountassets',
            name='healthy',
            field=models.BooleanField(null=True),
        ),
    ]
