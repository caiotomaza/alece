# SPDX-License-Identifier: GPL-3.0-only
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_remove_systemlog_core_systemlog_workspace_id_idx_and_more"),
        ("finance", "0010_importbatch_idempotency_key"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="AIProviderConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("endpoint", models.URLField(max_length=500)),
                ("model_name", models.CharField(max_length=120)),
                ("api_key_env", models.CharField(blank=True, max_length=80)),
                ("sections", models.JSONField(default=list)),
                ("enabled", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_providers", to="finance.workspace")),
            ],
            options={"ordering": ("name", "pk")},
        ),
        migrations.AddConstraint(model_name="aiproviderconfig", constraint=models.UniqueConstraint(fields=("workspace", "name"), name="uq_alece_ai_provider_name")),
        migrations.CreateModel(
            name="AIAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("section", models.CharField(choices=[("expenses", "Despesas"), ("investments", "Investimentos"), ("movements", "Movimentações")], max_length=12)),
                ("summary", models.TextField(max_length=4000)),
                ("data_hash", models.CharField(max_length=64)),
                ("record_count", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="finance.financialprofile")),
                ("provider", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="core.aiproviderconfig")),
                ("workspace", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="finance.workspace")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(model_name="aianalysis", index=models.Index(fields=("profile", "section", "-created_at"), name="alece_ai_analysis_idx")),
    ]
