# Generated by Django 5.0.3 on 2024-12-10 08:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_erc20_is_denomination_asset_erc20_is_gov_asset_and_more'),
        ('curve', '0015_curvescores_benchmark_borrower_distribution_score_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='DebtCeiling',
            new_name='Top5Debt',
        ),
        migrations.RenameIndex(
            model_name='top5debt',
            new_name='top5debt_cmt_idx',
            old_name='debt_ceiling_cmt_idx',
        ),
    ]
