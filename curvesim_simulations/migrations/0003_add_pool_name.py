from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curvesim_simulations", "0002_add_admin_fee_param"),
    ]

    operations = [
        migrations.AddField(
            model_name="SimulationRun",
            name="pool_name",
            field=models.CharField(max_length=100, null=True),
        ),
    ]
