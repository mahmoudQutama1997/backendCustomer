from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0013_settlement_event_audit")]
    operations = [
        migrations.AddField(
            model_name="order",
            name="estimated_duration_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="distance_source",
            field=models.CharField(default="unknown", max_length=32),
        ),
    ]
