#!/usr/bin/env python3
"""Tests for technical-analysis indicators and reporting."""

import os
import sys
import unittest
import pandas as pd
import numpy as np

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools',
                 'technical-analysis', 'scripts'),
)

from calculate_indicators import compute_all_indicators, compute_volume_profile
from run_analysis import format_markdown_report


class TestCalculateIndicators(unittest.TestCase):

    def setUp(self):
        dates = pd.date_range(start='2025-01-01', periods=250, freq='B')
        np.random.seed(42)
        base_price = 100.0
        prices = [base_price]
        for _ in range(1, 250):
            prices.append(prices[-1] * (1 + np.random.normal(0, 0.015)))

        self.df = pd.DataFrame({
            'Date': dates,
            'Open': [p * 0.99 for p in prices],
            'High': [p * 1.02 for p in prices],
            'Low': [p * 0.98 for p in prices],
            'Close': prices,
            'Volume': [np.random.randint(10000, 50000) for _ in range(250)],
        })

    def test_compute_all_indicators_has_keys(self):
        res_df, summary = compute_all_indicators(self.df)
        self.assertIn('price', summary)
        self.assertIn('moving_averages', summary)
        self.assertIn('macd', summary)
        self.assertIn('rsi', summary)
        self.assertIn('bollinger', summary)
        self.assertIn('volatility', summary)
        self.assertIn('volume_dynamics', summary)
        self.assertIn('volume_profile', summary)
        self.assertIsNotNone(summary['moving_averages']['sma50'])
        self.assertIsNotNone(summary['moving_averages']['sma200'])
        self.assertIsNotNone(summary['rsi']['rsi14'])
        self.assertIsNotNone(summary['bollinger']['bandwidth_pct'])
        self.assertIsNotNone(summary['volatility']['atr14'])

    def test_compute_volume_profile(self):
        vp = compute_volume_profile(self.df, n_bars=90, n_bins=25)
        self.assertIn('poc', vp)
        self.assertIn('overhead_supply', vp)
        self.assertIn('support_shelf', vp)
        self.assertGreater(vp['poc']['vol_pct'], 0)


class TestReportFormatting(unittest.TestCase):

    def test_minimalist_markdown_report(self):
        sym_info = {
            'canonical': '600519.SS',
            'market': 'CN',
            'is_etf': False,
        }
        summary = {
            'date': '2026-08-19',
            'price': {'open': 1300.0, 'close': 1307.88, 'high': 1308.88, 'low': 1290.5, 'volume': 37548},
            'moving_averages': {'ema10': 1319.79, 'sma20': 1323.92, 'sma50': 1262.67, 'sma200': 1348.39},
            'macd': {'dif': 13.2, 'dea': 20.0, 'hist': -6.8, 'signal': '绿柱整理'},
            'rsi': {'rsi6': 42.3, 'rsi14': 50.58, 'state': '中性平衡'},
            'bollinger': {'mid': 1323.92, 'upper': 1373.69, 'lower': 1274.15, 'bandwidth_pct': 7.52, 'position': '偏弱通道'},
            'volatility': {'atr14': 28.63, 'atr_pct': 2.19, 'vwma20': 1322.97},
            'volume_dynamics': {'vma5': 43381.0, 'vma20': 42626.0, 'vol_ratio_5': 0.87, 'vol_ratio_20': 0.88, 'desc': '温和换手'},
            'volume_profile': {
                'window_bars': 90,
                'poc': {'range': '1294 ~ 1306', 'mid_price': 1300.2, 'vol_pct': 9.0},
                'overhead_supply': {'total_trapped_vol_pct': 34.8, 'peak_cluster': {'range': '1330 ~ 1341', 'vol_pct': 6.6}},
                'support_shelf': {'total_support_vol_pct': 59.9, 'peak_cluster': {'range': '1294 ~ 1306', 'vol_pct': 9.0}},
            },
            'key_levels': {'stop_loss_suggested_2atr': 1250.61},
        }
        quote_info = {
            'name': '贵州茅台',
            'turnover_amount_wanyuan': 487677.0,
            'turnover_rate': 0.3,
            'shares_outstanding': 1250081601.0,
            'market_cap_circ_yi': 16349.57,
        }
        report = format_markdown_report(sym_info, summary, quote_info, detailed=False)
        self.assertIn('技术分析简报: 600519.SS 贵州茅台', report)
        self.assertIn('50 SMA (中期牛熊分界)', report)
        self.assertIn('200 SMA (长期机构生命线)', report)
        self.assertIn('情绪过滤器 (RSI 14)', report)
        self.assertIn('筹码控制峰 (POC)', report)
        self.assertNotIn('## 附录：全量量化指标明细', report)

        # Test detailed flag
        detailed_report = format_markdown_report(sym_info, summary, quote_info, detailed=True)
        self.assertIn('## 附录：全量量化指标明细', detailed_report)


if __name__ == '__main__':
    unittest.main(verbosity=2)
