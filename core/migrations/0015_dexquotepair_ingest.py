# Generated by Django 5.0.3 on 2024-09-26 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_dexquotepair_dexquote_pair'),
    ]

    operations = [
        migrations.AddField(
            model_name='dexquotepair',
            name='ingest',
            field=models.BooleanField(default=True),
        ),
    ]
