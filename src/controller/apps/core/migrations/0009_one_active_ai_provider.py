# SPDX-License-Identifier: GPL-3.0-only
"""Normaliza integrações previamente ativas e impõe exclusividade por workspace.

Nunca deleta chaves/integrações; retém a integração ativa mais recentemente alterada.
"""
from django.db import migrations, models


def normalize_active(apps, schema_editor):
    Provider = apps.get_model("core", "AIProviderConfig")
    workspace_ids = Provider.objects.filter(enabled=True).order_by().values_list("workspace_id", flat=True).distinct()
    for workspace_id in workspace_ids.iterator():
        active_ids = list(Provider.objects.filter(workspace_id=workspace_id, enabled=True)
                          .order_by("-updated_at", "-pk").values_list("pk", flat=True))
        if len(active_ids) > 1:
            Provider.objects.filter(pk__in=active_ids[1:]).update(enabled=False)


class Migration(migrations.Migration):
    dependencies = [("core", "0008_recovery_code_set")]
    operations = [
        migrations.RunPython(normalize_active, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="aiproviderconfig",
            constraint=models.UniqueConstraint(fields=("workspace",), condition=models.Q(enabled=True), name="uq_alece_ai_one_active_ws"),
        ),
    ]
