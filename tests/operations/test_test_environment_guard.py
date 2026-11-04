# SPDX-License-Identifier: GPL-3.0-only
"""Pure unit tests for the isolation gate (no database queries)."""
import pytest
from scripts.quality.test_environment import UnsafeTestEnvironment, validate_test_environment


@pytest.mark.parametrize("env", [
    {},
    {"ALECE_TEST_ISOLATED": "1", "ALECE_DB_NAME": "alece", "ALECE_DB_HOST": "db"},
    {"ALECE_TEST_ISOLATED": "1", "ALECE_DB_NAME": "test_alece", "ALECE_DB_HOST": "example.com"},
    {"ALECE_TEST_ISOLATED": "1", "ALECE_DB_NAME": "prod_test", "ALECE_DB_HOST": "production.internal"},
    {"ALECE_TEST_ISOLATED": "1", "ALECE_DB_NAME": "test_alece", "ALECE_DB_HOST": "db", "ALECE_TEST_USE_PRODUCTION": "1"},
])
def test_rejects_unsafe_environment(env):
    with pytest.raises(UnsafeTestEnvironment):
        validate_test_environment(env)


@pytest.mark.parametrize("name,host", [( "alece_test", "127.0.0.1"), ("alece_audit", "db"), ("test_alece", "postgres")])
def test_accepts_explicit_isolation(name, host):
    assert validate_test_environment({"ALECE_TEST_ISOLATED": "1", "ALECE_DB_NAME": name, "ALECE_DB_HOST": host})
