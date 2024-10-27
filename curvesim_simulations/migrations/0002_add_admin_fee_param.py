from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curvesim_simulations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="SimulationParameters",
            name="admin_fee",
            field=models.FloatField(default=0),
            preserve_default=False,
        ),
    ]
