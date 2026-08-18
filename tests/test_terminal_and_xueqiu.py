#!/usr/bin/env python3
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))

import terminal_value as T  # noqa: E402
import xueqiu_scraper as X  # noqa: E402
from pathlib import Path


class TestTerminalValueGuards(unittest.TestCase):

    def test_roic_zero_does_not_divide(self):
        pe, retention, numerator, spread = T.exit_pe(0, 0.02, 0.06)
        self.assertIsNone(pe)
        self.assertIsNone(retention)
        self.assertAlmostEqual(spread, 0.04)

    def test_negative_terminal_raises(self):
        with self.assertRaises(ValueError):
            T.irr_from_terminal(-100, 1000, 10, years=10)


class TestXueqiuImports(unittest.TestCase):

    def test_path_is_imported(self):
        self.assertIs(X.Path, Path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
