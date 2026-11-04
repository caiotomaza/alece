# SPDX-License-Identifier: GPL-3.0-only
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("core", "0004_systemlog")]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE FUNCTION core_guard_systemlog() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'System log history is append-only';
            END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER core_systemlog_append_only
            BEFORE UPDATE OR DELETE ON core_systemlog
            FOR EACH ROW EXECUTE FUNCTION core_guard_systemlog();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS core_systemlog_append_only ON core_systemlog;
            DROP FUNCTION IF EXISTS core_guard_systemlog();
            """,
        ),
    ]
