# Generated by Django 5.0.3 on 2024-10-13 23:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ethena', '0026_buidlredemptionmetrics'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usdmmetrics',
            name='holders',
            field=models.TextField(),
        ),
    ]
