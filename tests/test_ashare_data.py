#!/usr/bin/env python3
"""ashare_data.py — independent market-cap check and BJ routing."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))

import ashare_data as A  # noqa: E402


class TestBoardRouting(unittest.TestCase):

    def test_maotai_is_sh(self):
        self.assertEqual(A._board_prefix('600519'), 'sh')
        self.assertEqual(A._listing_exchange('600519'), 'SH')

    def test_star_is_sh_not_bj(self):
        self.assertEqual(A._board_prefix('688012'), 'sh')

    def test_beijing_is_bj_not_sz(self):
        self.assertEqual(A._board_prefix('835185'), 'bj')
        self.assertEqual(A._listing_exchange('835185'), 'BJ')
        self.assertEqual(A._qq_code('835185'), 'bj835185')

    def test_bj_920_not_sh(self):
        self.assertEqual(A._board_prefix('920001'), 'bj')


class TestIndependentMarketCap(unittest.TestCase):

    def test_mismatch_is_not_zero(self):
        out = A.verify_price_times_shares(10, 100, 2000)
        self.assertIsNotNone(out)
        self.assertFalse(out['ok'])
        self.assertGreater(out['deviation_pct'], 5)

    def test_true_match_passes(self):
        out = A.verify_price_times_shares(10, 200, 2000)
        self.assertTrue(out['ok'])
        self.assertLess(out['deviation_pct'], 0.01)

    def test_missing_shares_returns_none(self):
        self.assertIsNone(A.verify_price_times_shares(10, None, 2000))

    def test_does_not_back_out_shares_from_cap(self):
        # If someone passed shares derived from cap, deviation would be 0.
        # Independent wrong shares must still fail.
        derived = 2000 / 10
        out = A.verify_price_times_shares(10, 50, 2000)
        self.assertNotEqual(50, derived)
        self.assertFalse(out['ok'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
