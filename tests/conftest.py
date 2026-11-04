# SPDX-License-Identifier: GPL-3.0-only
"""Always isolate tests from operator databases and avoid real-user fixtures."""

from scripts.quality.test_environment import validate_test_environment


def pytest_sessionstart(session):
    validate_test_environment()
