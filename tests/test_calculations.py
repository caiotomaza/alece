# SPDX-License-Identifier: GPL-3.0-only
from decimal import Decimal as D
import unittest

from apps.finance.domain.calculations import allocate_monthly, reserve_goal


class FinanceCalculationsTest(unittest.TestCase):
    def test_reserve_nine_months(self):
        self.assertEqual(reserve_goal(D("536.39"), 9), D("4827.51"))

    def test_reserve_covered(self):
        result = allocate_monthly(
            D("2300.00"), D("536.39"), D("444.28"), D("500.00"),
            D("0"), D("4827.51"), D("4827.51"), (1, 1, 1),
        )
        self.assertEqual(result["reserve"], D("0.00"))
        self.assertEqual(result["development"], D("273.11"))
        self.assertEqual(result["patrimony"], D("273.11"))
        self.assertEqual(result["planned_consumption"], D("273.11"))

    def test_reserve_below_target_has_priority(self):
        result = allocate_monthly(
            D("2300.00"), D("536.39"), D("444.28"), D("500.00"),
            D("0"), D("3754.73"), D("4827.51"), (1, 1, 1),
        )
        self.assertEqual(result["reserve"], D("819.33"))
        self.assertEqual(result["development"], D("0.00"))

    def test_income_zero(self):
        result = allocate_monthly(D("0"), D("100"), D("0"), D("0"), D("0"), D("0"), D("600"))
        self.assertEqual(result["available_before_reserve"], D("0"))

    def test_split_cent_without_loss(self):
        result = allocate_monthly(D("1.01"), D("0"), D("0"), D("0"), D("0"), D("0"), D("0"))
        self.assertEqual(result["development"] + result["patrimony"] + result["planned_consumption"], D("1.01"))

    def test_invalid_months(self):
        with self.assertRaises(ValueError):
            reserve_goal(D("100"), 5)
