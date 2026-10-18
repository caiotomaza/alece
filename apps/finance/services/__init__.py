# SPDX-License-Identifier: GPL-3.0-only
"""Serviços transacionais do ALECE — fronteira exclusiva de escrita financeira."""
from apps.finance.services.accounts import create_bank_account
from apps.finance.services.categorization import (
    create_categorization_rule, update_categorization_rule, delete_categorization_rule,
    get_categorization_rules, apply_categorization_rules, apply_rules_to_transactions,
    get_rules_for_import, validate_regex_safety, compile_safe_regex,
    rollback_categorization_rule,
    CategorizationError, RegexSecurityError,
)
from apps.finance.services.grants import save_grant, GRANT_FIELDS
from apps.finance.services.ledger import (
    confirm_outflow, transfer, withdraw_investment,
    reverse_batch, reverse_item_payments, reconcile_account,
)
from apps.finance.services.metrics import profile_summary
from apps.finance.services.monthly import (
    monthly_items, recurring_due, paid_for_recurring,
    paid_for_unexpected, application_due, paid_for_application,
)
from apps.finance.services.profiles import (
    create_financial_profile, update_financial_profile,
)
from apps.finance.services.reports import (
    generate_dre_report, generate_equity_evolution_report,
    generate_investment_report, generate_goals_report, generate_dashboard_report,
    DREReport, EquityEvolutionReport, InvestmentReport, GoalsReport, DashboardReport,
)
from apps.finance.services.records import save_record, delete_record, update_income
from apps.finance.services.imports import (
    stage_import, commit_import, dry_run_import,
    generate_reconciliation_suggestions, generate_import_report,
    ImportParseError, ImportValidationError, ImportCommitError,
)
from apps.finance.services.importers import (
    ParsedStatement, ParsedTransaction, detect_format, get_parser,
    ImportParseError as ImporterParseError, ImportSecurityError,
)

__all__ = [
    # Accounts
    "create_bank_account",
    # Categorization (Sprint 05/06)
    "create_categorization_rule", "update_categorization_rule", "delete_categorization_rule",
    "get_categorization_rules", "apply_categorization_rules", "apply_rules_to_transactions",
    "get_rules_for_import", "validate_regex_safety", "compile_safe_regex",
    "rollback_categorization_rule",
    "CategorizationError", "RegexSecurityError",
    # Grants
    "save_grant", "GRANT_FIELDS",
    # Ledger
    "confirm_outflow", "transfer", "withdraw_investment",
    "reverse_batch", "reverse_item_payments", "reconcile_account",
    # Metrics
    "profile_summary",
    # Monthly
    "monthly_items", "recurring_due", "paid_for_recurring",
    "paid_for_unexpected", "application_due", "paid_for_application",
    # Profiles
    "create_financial_profile", "update_financial_profile",
    # Records
    "save_record", "delete_record", "update_income",
    # Reports (Sprint 05)
    "generate_dre_report", "generate_equity_evolution_report",
    "generate_investment_report", "generate_goals_report", "generate_dashboard_report",
    "DREReport", "EquityEvolutionReport", "InvestmentReport", "GoalsReport", "DashboardReport",
    # Imports
    "stage_import", "commit_import", "dry_run_import",
    "generate_reconciliation_suggestions", "generate_import_report",
    "ImportParseError", "ImportValidationError", "ImportCommitError",
    # Importers
    "ParsedStatement", "ParsedTransaction", "detect_format", "get_parser",
    "ImporterParseError", "ImportSecurityError",
]