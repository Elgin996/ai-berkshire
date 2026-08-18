#!/usr/bin/env python3
"""Ticker normalization and cache freshness (no pandas)."""

import os
import sys
import unittest
from datetime import date, datetime

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools',
                 'technical-analysis', 'scripts'),
)

from symbols import cache_is_usable, normalize_symbol_info  # noqa: E402


class TestNormalizeSymbol(unittest.TestCase):

    def test_00700_is_hk_not_us(self):
        info = normalize_symbol_info('00700')
        self.assertEqual(info['market'], 'HK')
        self.assertEqual(info['canonical'], '0700.HK')
        self.assertEqual(info['tencent_symbol'], 'hk00700')
        self.assertEqual(info['yahoo_symbol'], '0700.HK')

    def test_0700_bare_is_hk(self):
        info = normalize_symbol_info('0700')
        self.assertEqual(info['market'], 'HK')
        self.assertEqual(info['yahoo_symbol'], '0700.HK')

    def test_0700_hk_suffix(self):
        info = normalize_symbol_info('0700.HK')
        self.assertEqual(info['market'], 'HK')
        self.assertEqual(info['tencent_symbol'], 'hk00700')

    def test_bj_yahoo_not_sz(self):
        info = normalize_symbol_info('835185.BJ')
        self.assertEqual(info['market'], 'CN')
        self.assertEqual(info['yahoo_symbol'], '835185.BJ')
        self.assertEqual(info['tencent_symbol'], 'bj835185')

    def test_nvda_is_us(self):
        self.assertEqual(normalize_symbol_info('NVDA')['market'], 'US_GLOBAL')


class TestCacheFreshness(unittest.TestCase):

    def test_today_respects_ttl(self):
        today = date(2026, 8, 18)
        mtime = datetime(2026, 8, 18, 12, 0).timestamp()
        now = datetime(2026, 8, 18, 12, 5).timestamp()
        self.assertTrue(cache_is_usable(today, today, mtime, today, now_ts=now, ttl_seconds=900))
        now_stale = datetime(2026, 8, 18, 13, 0).timestamp()
        self.assertFalse(cache_is_usable(today, today, mtime, today, now_ts=now_stale, ttl_seconds=900))

    def test_historical_rejects_same_day_write(self):
        as_of = date(2026, 8, 17)
        today = date(2026, 8, 18)
        mtime = datetime(2026, 8, 17, 10, 0).timestamp()
        self.assertFalse(cache_is_usable(as_of, today, mtime, as_of))

    def test_historical_accepts_next_day_write(self):
        as_of = date(2026, 8, 17)
        today = date(2026, 8, 18)
        mtime = datetime(2026, 8, 18, 9, 0).timestamp()
        self.assertTrue(cache_is_usable(as_of, today, mtime, as_of))


if __name__ == '__main__':
    unittest.main(verbosity=2)
