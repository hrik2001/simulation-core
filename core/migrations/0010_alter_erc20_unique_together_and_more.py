# Generated by Django 5.0.3 on 2024-05-25 22:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_uniswaplpposition_token_id_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='erc20',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='uniswaplpposition',
            name='token0',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='erc_token0', to='core.erc20'),
        ),
        migrations.AlterField(
            model_name='uniswaplpposition',
            name='token1',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='erc_token1', to='core.erc20'),
        ),
        migrations.AddConstraint(
            model_name='erc20',
            constraint=models.UniqueConstraint(fields=('contract_address', 'chain'), name='erc20_unique_token_contract_chain'),
        ),
    ]
