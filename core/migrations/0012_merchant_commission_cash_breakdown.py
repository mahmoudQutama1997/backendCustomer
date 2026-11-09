from decimal import Decimal, ROUND_HALF_UP
from django.db import migrations, models


def backfill_settlements(apps, schema_editor):
    Settlement = apps.get_model("core", "CashSettlement")
    for row in Settlement.objects.select_related("order", "merchant").all().iterator():
        order = row.order
        merchant = row.merchant
        kind = getattr(merchant, "commission_type", "percent") or "percent"
        value = getattr(merchant, "commission_value", Decimal("0.00")) or Decimal("0.00")
        base = order.subtotal or Decimal("0.00")
        fee = base * value / Decimal("100") if kind == "percent" else value
        fee = min(base, fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        row.amount = order.total
        row.goods_amount = base
        row.delivery_fee = order.delivery_fee
        row.checkpoint_fee = order.checkpoint_fee
        row.commission_type = kind
        row.commission_value = value
        row.platform_commission = fee
        row.merchant_net = base - fee
        row.captain_earnings = order.delivery_fee + order.checkpoint_fee
        row.save(update_fields=["amount", "goods_amount", "delivery_fee", "checkpoint_fee", "commission_type", "commission_value", "platform_commission", "merchant_net", "captain_earnings"])


class Migration(migrations.Migration):
    dependencies = [("core", "0011_captain_location_timestamp")]
    operations = [
        migrations.AddField(model_name="merchantprofile", name="commission_type", field=models.CharField(choices=[("percent", "Percentage"), ("fixed", "Fixed amount per order")], default="percent", max_length=10)),
        migrations.AddField(model_name="merchantprofile", name="commission_value", field=models.DecimalField(decimal_places=2, default=0, max_digits=8)),
        migrations.AddField(model_name="cashsettlement", name="goods_amount", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="cashsettlement", name="delivery_fee", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="cashsettlement", name="checkpoint_fee", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="cashsettlement", name="commission_type", field=models.CharField(choices=[("percent", "Percentage"), ("fixed", "Fixed amount per order")], default="percent", max_length=10)),
        migrations.AddField(model_name="cashsettlement", name="commission_value", field=models.DecimalField(decimal_places=2, default=0, max_digits=8)),
        migrations.AddField(model_name="cashsettlement", name="platform_commission", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="cashsettlement", name="merchant_net", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="cashsettlement", name="captain_earnings", field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name="cashsettlement", name="collected_amount", field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
        migrations.AddField(model_name="cashsettlement", name="admin_resolution_note", field=models.TextField(blank=True)),
        migrations.RunPython(backfill_settlements, migrations.RunPython.noop),
    ]
