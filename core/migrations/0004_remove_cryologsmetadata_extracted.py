# Generated by Django 5.0.3 on 2024-04-07 13:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_rename_hash_transaction_transaction_hash_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cryologsmetadata',
            name='extracted',
        ),
    ]
