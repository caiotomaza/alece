# SPDX-License-Identifier: GPL-3.0-only
"""Fail closed before running tests against a database that may contain user data."""
import os
import re


class UnsafeTestEnvironment(RuntimeError):
    """Test isolation has not been proven."""


def validate_test_environment(environ=None):
    env = os.environ if environ is None else environ
    if env.get("ALECE_TEST_ISOLATED") != "1":
        raise UnsafeTestEnvironment("ALECE_TEST_ISOLATED=1 is required for the QA suite")
    name = env.get("ALECE_DB_NAME", "").strip().lower()
    if not re.fullmatch(r"(?:test_[a-z0-9_]+|[a-z0-9_]+_test|alece_audit)", name):
        raise UnsafeTestEnvironment("Database must have an explicit test/audit name")
    # These names are explicit production indicators even if the name contains 'test'.
    host = env.get("ALECE_DB_HOST", "").strip().lower()
    if host not in ("db", "localhost", "127.0.0.1", "::1", "postgres"):
        raise UnsafeTestEnvironment("Database host is not a local or isolated CI endpoint")
    if env.get("ALECE_DEBUG", "false").lower() in ("", "false", "0", "no"):
        # Debug is not required. Avoid relying on it as proof of isolation.
        pass
    for key in ("ALECE_TEST_ALLOW_REAL_DATA", "ALECE_TEST_USE_PRODUCTION"):
        if env.get(key):
            raise UnsafeTestEnvironment(f"Dangerous test flag present: {key}")
    return True
