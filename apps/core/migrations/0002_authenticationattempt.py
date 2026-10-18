# SPDX-License-Identifier: GPL-3.0-only
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="recovery_code_version",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="AuthenticationAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=64, unique=True)),
                ("window_started", models.DateTimeField(db_index=True)),
                ("attempts", models.PositiveIntegerField(default=0)),
            ],
        ),
    ]
