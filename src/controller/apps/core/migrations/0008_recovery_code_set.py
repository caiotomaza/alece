# SPDX-License-Identifier: GPL-3.0-only
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0007_ai_integrations"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(model_name="userprofile", name="recovery_acknowledged_at",
            field=models.DateTimeField(blank=True, null=True)),
        migrations.CreateModel(name="RecoveryCode", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("slot", models.PositiveSmallIntegerField()),
            ("code_hash", models.CharField(max_length=64)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("used_at", models.DateTimeField(blank=True, null=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                  related_name="recovery_codes", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="recoverycode", constraint=models.UniqueConstraint(
            fields=("user", "slot"), name="uq_recovery_slot_user")),
    ]
