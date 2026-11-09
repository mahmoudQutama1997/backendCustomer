from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("core", "0012_merchant_commission_cash_breakdown"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="SettlementEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("captain_collected", "Captain recorded collection"), ("merchant_confirmed", "Merchant confirmed proceeds"), ("admin_resolved", "Administrator resolved discrepancy")], max_length=24)),
                ("collected_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="settlement_events", to=settings.AUTH_USER_MODEL)),
                ("settlement", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="events", to="core.cashsettlement")),
            ],
            options={"ordering": ["created_at", "id"]},
        ),
    ]
