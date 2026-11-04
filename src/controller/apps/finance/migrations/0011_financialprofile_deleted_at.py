# Generated for ALECE's non-destructive financial profile deletion.
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("finance", "0010_importbatch_idempotency_key")]
    operations = [
        migrations.AddField(
            model_name="financialprofile",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
