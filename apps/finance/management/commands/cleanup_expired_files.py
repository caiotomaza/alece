# SPDX-License-Identifier: GPL-3.0-only
"""Comando para limpeza de arquivos temporários e exportações expiradas."""
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.finance.models import ReportExport, ImportBatch


class Command(BaseCommand):
    help = "Remove arquivos temporários e exportações expiradas com mais de N horas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Arquivos mais antigos que N horas serão removidos (padrão: 24h).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas lista o que seria removido, sem excluir.",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        dry_run = options["dry_run"]
        cutoff = timezone.now() - timedelta(hours=hours)

        # Exportações expiradas (status ready/failed/pending antigas)
        expired_exports = ReportExport.objects.filter(
            requested_at__lt=cutoff,
            status__in=["ready", "failed", "pending"],
        ).exclude(file="")

        # Lotes de importação em staging/validated antigos sem commit
        stale_batches = ImportBatch.objects.filter(
            created_at__lt=cutoff,
            status__in=["staged", "validated"],
        ).exclude(file_hash="")

        total_files = expired_exports.count() + stale_batches.count()

        if total_files == 0:
            self.stdout.write(self.style.SUCCESS("Nenhum arquivo expirado encontrado."))
            return

        self.stdout.write(f"Encontrados {expired_exports.count()} exportações e {stale_batches.count()} lotes de importação para limpeza.")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN: Nenhum arquivo foi removido."))
            for exp in expired_exports:
                self.stdout.write(f"  Exportação #{exp.pk}: {exp.file.name} ({exp.requested_at})")
            for batch in stale_batches:
                self.stdout.write(f"  Lote #{batch.pk}: {batch.filename} ({batch.created_at})")
            return

        # Remover arquivos físicos e atualizar status
        removed = 0
        for exp in expired_exports:
            try:
                if exp.file:
                    exp.file.delete(save=False)
                exp.status = "failed"
                exp.error_message = "Arquivo expirado e removido automaticamente"
                exp.save(update_fields=["status", "error_message"])
                removed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao remover exportação #{exp.pk}: {e}"))

        for batch in stale_batches:
            try:
                # ImportBatch não tem arquivo físico, apenas file_hash/filename
                batch.status = "failed"
                batch.save(update_fields=["status"])
                removed += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro ao remover lote #{batch.pk}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Limpeza concluída: {removed} arquivo(s) removido(s)."))