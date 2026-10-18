# SPDX-License-Identifier: GPL-3.0-only
"""Read-only migration preflight; never prints names or financial values."""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Conta posições legadas da Reserva e saldos sem base conciliada, sem modificar dados."

    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true", help="Falha se houver bloqueadores.")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("Preflight exige PostgreSQL.")
        with transaction.atomic(), connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            tables = set(connection.introspection.table_names(cursor))
            if "finance_investmentposition" not in tables:
                raise CommandError("Tabela de investimentos ausente; aplique primeiro o schema inicial.")
            cursor.execute(
                "SELECT COUNT(*) FROM finance_investmentposition "
                "WHERE category = %s AND target_amount IS NOT NULL", ["reserve"],
            )
            reserve_targets = cursor.fetchone()[0]
            missing_opening = None
            if "finance_bankaccount" in tables:
                columns = {
                    column.name for column in connection.introspection.get_table_description(
                        cursor, "finance_bankaccount",
                    )
                }
                if "opening_balance" in columns:
                    cursor.execute(
                        "SELECT COUNT(*) FROM finance_bankaccount "
                        "WHERE balance IS NOT NULL AND opening_balance IS NULL"
                    )
                    missing_opening = cursor.fetchone()[0]
        result = {
            "reserve_manual_target_positions": reserve_targets,
            "accounts_without_reconciled_opening": missing_opening,
            "safe_to_apply_reserve_constraint": reserve_targets == 0,
            "modified_rows": 0,
        }
        self.stdout.write(json.dumps(result, sort_keys=True))
        if options["strict"] and (reserve_targets or (missing_opening or 0)):
            raise CommandError("Preflight encontrou dados que exigem plano de migração aprovado.")
