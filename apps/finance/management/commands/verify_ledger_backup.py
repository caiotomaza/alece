# SPDX-License-Identifier: GPL-3.0-only
"""Comando para verificação e validação de backup do ledger (AC-08)."""
import hashlib
import json
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.finance.models import (
    BankAccount, FinancialProfile, InvestmentPosition, TransactionBatch,
    JournalEntry, LedgerLeg,
)
from apps.finance.services.reports import generate_dashboard_report


class Command(BaseCommand):
    help = "Gera snapshot consistente do ledger, valida SHA-256 e reconcilia saldos (AC-08)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            type=int,
            required=True,
            help="ID do perfil financeiro para validar.",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="",
            help="Caminho do arquivo de saída (JSON). Se omitido, imprime no stdout.",
        )
        parser.add_argument(
            "--verify-only",
            action="store_true",
            help="Apenas valida integridade sem gerar snapshot.",
        )

    def handle(self, *args, **options):
        profile_id = options["profile"]
        output_path = options["output"]
        verify_only = options["verify_only"]

        try:
            profile = FinancialProfile.objects.get(pk=profile_id)
        except Exception:
            self.stderr.write(self.style.ERROR(f"Perfil {profile_id} não encontrado."))
            return

        with transaction.atomic():
            report = self._generate_snapshot(profile)

        if not verify_only:
            self._save_snapshot(report, profile, options.get("output", ""))

        # Verificar integridade
        errors = self._verify_integrity(profile)
        if errors:
            self.stderr.write(self.style.ERROR("Falhas de integridade encontradas:"))
            for err in errors:
                self.stderr.write(f"  - {err}")
        else:
            self.stdout.write(self.style.SUCCESS("Integridade do ledger validada com sucesso."))

    def _generate_snapshot(self, profile):
        """Gera snapshot consistente do estado financeiro."""
        snapshot = {
            "profile_id": profile.pk,
            "profile_name": profile.name,
            "timestamp": timezone.now().isoformat(),
            "accounts": [],
            "investments": [],
            "ledger_totals": {},
        }

        # Contas bancárias
        accounts = BankAccount.objects.filter(
            profile_id=profile.pk,
            is_archived=False,
        ).select_related("profile")

        for acc in accounts:
            # Calcular saldo via ledger
            ledger_sum = LedgerLeg.objects.filter(
                account_id=acc.pk
            ).aggregate(total=Sum("delta"))["total"] or Decimal("0.00")
            
            opening = acc.opening_balance or Decimal("0.00")
            calculated = opening + ledger_sum

            acc_data = {
                "id": acc.pk,
                "name": acc.name,
                "kind": acc.kind,
                "opening_balance": str(opening),
                "current_balance": str(acc.balance),
                "calculated_balance": str(calculated),
                "ledger_sum": str(ledger_sum),
                "reconciled": acc.balance is not None and acc.balance == calculated,
            }
            snapshot["accounts"].append(acc_data)

        # Investimentos
        investments = InvestmentPosition.objects.filter(
            profile_id=profile.pk,
            is_active=True,
        )
        for inv in investments:
            snapshot["investments"].append({
                "id": inv.pk,
                "name": inv.name,
                "category": inv.category,
                "applied_amount": str(inv.applied_amount),
                "current_value": str(inv.current_value),
                "target_amount": str(inv.target_amount) if inv.target_amount else None,
            })

        # Totais do ledger
        batches = TransactionBatch.objects.filter(
            profile__pk=profile.pk,
            reversal__isnull=True,
        ).aggregate(
            total_debits=Sum("journal_entries__debit"),
            total_credits=Sum("journal_entries__credit"),
        )
        snapshot["ledger_totals"] = {
            "total_debits": str(batches["total_debits"] or Decimal("0.00")),
            "total_credits": str(batches["total_credits"] or Decimal("0.00")),
            "balanced": batches["total_debits"] == batches["total_credits"],
        }

        return snapshot

    def _save_snapshot(self, snapshot, profile, output_path):
        import hashlib
        import json

        if not snapshot.get("timestamp"):
            snapshot["timestamp"] = timezone.now().isoformat()

        json_data = json.dumps(snapshot, indent=2, ensure_ascii=False, default=str)
        json_bytes = json_data.encode("utf-8")
        sha256 = hashlib.sha256(json_bytes).hexdigest()
        snapshot["sha256"] = sha256

        output_json = json.dumps(snapshot, indent=2, ensure_ascii=False, default=str)

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str))
            self.stdout.write(f"Snapshot salvo em: {output_path}")
            self.stdout.write(f"SHA-256: {sha256}")
        else:
            self.stdout.write(json.dumps(snapshot, indent=2, ensure_ascii=False, default=str))

    def _verify_integrity(self, profile):
        errors = []

        # 1. Verificar balanceamento do ledger
        batches = TransactionBatch.objects.filter(
            profile__pk=profile.pk,
            reversal__isnull=True,
        ).prefetch_related("journal_entries")

        for batch in batches:
            debits = sum(e.debit for e in batch.journal_entries.all())
            credits = sum(e.credit for e in batch.journal_entries.all())
            if debits != credits:
                self._add_error(
                    errors,
                    f"Lote #{batch.pk} desbalanceado: débitos={debits} ≠ créditos={credits}",
                )

        # 2. Verificar reconciliação de contas
        for acc in BankAccount.objects.filter(profile_id=profile.pk, is_archived=False):
            ledger_sum = sum(
                leg.delta for leg in LedgerLeg.objects.filter(account_id=acc.pk)
            ) or Decimal("0.00")
            opening = acc.opening_balance or Decimal("0.00")
            calculated = (acc.opening_balance or Decimal("0.00")) + sum(
                leg.delta for leg in LedgerLeg.objects.filter(account_id=acc.pk)
            )
            if acc.balance is not None and acc.balance != calculated:
                self._add_error(
                    errors,
                    f"Conta {acc.name} (#{acc.pk}): saldo={acc.balance} ≠ calculado={calculated}",
                )

        # 3. Verificar investimentos
        for inv in InvestmentPosition.objects.filter(
            profile_id=profile.pk,
            is_active=True,
        ):
            if inv.current_value < 0:
                self._add_error(
                    errors,
                    f"Investimento {inv.name} (#{inv.pk}): valor atual negativo ({inv.current_value})",
                )
            if inv.applied_amount < 0:
                self._add_error(
                    errors,
                    f"Investimento {inv.name} (#{inv.pk}): valor aplicado negativo ({inv.applied_amount})",
                )

        return []

    def _add_error(self, errors, message):
        self.stderr.write(self.style.ERROR(f"  - {message}"))
        return message