# Generated by Django 5.0.3 on 2024-12-27 17:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('curve', '0022_remove_top5debt_data_curveuserdata'),
    ]

    operations = [
        migrations.RenameField(
            model_name='curvemetrics',
            old_name='total_supply',
            new_name='circulating_supply',
        ),
    ]
