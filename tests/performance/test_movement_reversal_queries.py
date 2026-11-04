# SPDX-License-Identifier: GPL-3.0-only
"""Regressão do pré-carregamento de estorno do ledger; roda só em PostgreSQL isolado."""
import os
import pytest


@pytest.mark.django_db
@pytest.mark.integration
def test_movements_reverse_one_to_one_does_not_trigger_per_row_queries(django_assert_num_queries):
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from datetime import date
    from decimal import Decimal
    from apps.finance.models import BankAccount, FinancialProfile, LedgerLeg, TransactionBatch, Workspace

    assert os.getenv("ALECE_TEST_ISOLATED") == "1"
    assert settings.DATABASES["default"]["NAME"].startswith("test_") or settings.DATABASES["default"]["NAME"] == "alece_test"
    actor = get_user_model().objects.create_user(username="perf-ledger-test")
    workspace = Workspace.objects.create(name="Teste de pré-carregamento", created_by=actor)
    profile = FinancialProfile.objects.create(workspace=workspace, name="Perfil sintético")
    account = BankAccount.objects.create(profile=profile, name="Conta teste", kind="bank", balance=Decimal("0"))
    for _ in range(3):
        batch = TransactionBatch.objects.create(profile=profile, kind="income", amount=Decimal("10"),
                                                occurred_on=date(2026, 10, 1), created_by=actor)
        LedgerLeg.objects.create(batch=batch, account=account, delta=Decimal("10"))
    # Mesma relação select_related usada em workspace_page; comparação de contagem sem expor SQL.
    queryset = LedgerLeg.objects.filter(batch__profile=profile).select_related(
        "batch", "batch__created_by", "batch__reversal", "account"
    ).order_by("-batch__occurred_on", "-batch_id", "pk")
    with django_assert_num_queries(1):
        rows = list(queryset)
        assert len(rows) == 3
        assert all(getattr(row.batch, "reversal", None) is None for row in rows)
