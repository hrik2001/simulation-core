# Generated by Django 5.0.3 on 2024-12-10 08:14

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_erc20_is_denomination_asset_erc20_is_gov_asset_and_more'),
        ('curve', '0014_curvescores_prob_drop1_score_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='curvescores',
            name='benchmark_borrower_distribution_score',
            field=models.TextField(default='0'),
        ),
        migrations.AddField(
            model_name='curvescores',
            name='debt_ceiling_score',
            field=models.TextField(default='0'),
        ),
        migrations.AddField(
            model_name='curvescores',
            name='relative_borrower_distribution_score',
            field=models.TextField(default='0'),
        ),
        migrations.CreateModel(
            name='CurveDebtCeilingScore',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('controller', models.TextField()),
                ('created_at', models.DateTimeField()),
                ('debt_ceiling_score', models.TextField()),
                ('chain', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.chain')),
            ],
        ),
    ]
