"""Balanced synthetic batches for report and import tests.

These tests inspect projections from historical rows; the fixture still obeys
the database's deferred double-entry constraint.
"""
from decimal import Decimal

from apps.finance.models import JournalEntry, TransactionBatch


def posted_test_batch(**fields):
    batch = TransactionBatch.objects.create(**fields)
    amount = Decimal(str(fields["amount"]))
    JournalEntry.objects.create(batch=batch, account_code="test:debit", debit=amount)
    JournalEntry.objects.create(batch=batch, account_code="test:credit", credit=amount)
    return batch
