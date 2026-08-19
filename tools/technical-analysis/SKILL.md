---
name: technical-analysis
description: >-
  Quantitative stock and ETF technical analysis skill for China A-shares, Hong Kong stocks, ETFs, and global equities.
  Fetches front-rehabilitated (QFQ) OHLCV data, calculates 8+ quant indicators (10 EMA, 20/50/200 SMA, MACD, RSI,
  Bollinger Bands, ATR, VWMA, ETF IOPV/discount rate, shares outstanding), and generates structured institutional-grade
  technical analysis reports with support and resistance levels. Works universally across Antigravity, Claude Code, and Codex.
---

# Technical Analysis Skill (A-Shares, HK Stocks, ETFs & Global Equities)

This skill provides deterministic, zero-hallucination quantitative technical analysis for Chinese A-Shares, Hong Kong Stocks, Index ETFs, and Global Equities.

## When to Activate This Skill
Activate this skill whenever the user:
- Asks for technical analysis of a stock or ETF (e.g. "分析一下 600519", "看看腾讯 0700.HK 的技术面", "中证A500 ETF 563360 怎么看？").
- Inquires about support/resistance levels, moving average trends, MACD golden/death crosses, RSI overbought/oversold states, or Bollinger Bands.
- Requests entry points, stop-loss calculations (ATR), or ETF premium/discount arbitrage signals.

---

## How to Execute the Skill

Execute the standalone script via your CLI/Bash execution tool:

```bash
# 1. Standard Markdown output for A-share (e.g. 600519.SS, 300394.SZ, 688012.SH)
python3 tools/technical-analysis/scripts/run_analysis.py 600519.SS

# 2. Analyze Hong Kong stock (e.g. 0700.HK, 9988.HK, 3690.HK)
python3 tools/technical-analysis/scripts/run_analysis.py 0700.HK

# 3. Analyze Index ETF with real-time IOPV, discount rate & shares (e.g. 563360, 510300)
python3 tools/technical-analysis/scripts/run_analysis.py 563360

# 4. Analyze on a historical date (Backtesting / Anti-lookahead)
python3 tools/technical-analysis/scripts/run_analysis.py 300394.SZ --date 2026-08-14

# 5. Programmatic JSON output mode (for structured agent downstream parsing)
python3 tools/technical-analysis/scripts/run_analysis.py 600519.SS --format json
```

Dependencies (once per environment):

```bash
pip install -r tools/technical-analysis/requirements.txt
```

---

## Parameter Reference

| Parameter | Type | Required | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `symbol` | `string` | **Yes** | - | Stock/ETF ticker (e.g. `600519.SS`, `300394.SZ`, `0700.HK`, `563360`, `NVDA`) |
| `--date` | `string` | No | `today` | Date in `YYYY-MM-DD` format. Future rows are truncated. |
| `--format` | `string` | No | `markdown` | Output format: `markdown` (formatted report) or `json` (raw metrics dict). |
| `--detailed` | `flag` | No | `False` | Include full detailed technical indicators in markdown appendix. |
| `--no-quote` | `flag` | No | `False` | Disables real-time quote snapshot fetch. |

---

## Core Technical Dimensions Covered (High Signal Minimalist Kit)

1. **Ground-Truth Price Table**: Real QFQ Open/High/Low/Close/Volume and live snapshot (turnover, turnover rate, float shares/market cap).
2. **Trend & Structural Lines (50 SMA & 200 SMA)**: Medium-term bull/bear anchor (50 SMA) and institutional long-term trendline (200 SMA).
3. **Volume Baseline Dynamics**: Volume vs 20-day average volume (VMA20) ratio and volume surge/contraction state.
4. **Volume Profile (VPVR - 90 Days)**: Point of Control (POC) price cluster, overhead trapped supply %, and support shelf %.
5. **Sentiment Filter (RSI 14)**: Objective FOMO prevention (>70) and panic-selling protection (<30).
6. **Volatility & Squeeze (ATR 14 & Bollinger Bandwidth)**: Daily ATR % and Bollinger bandwidth squeeze (pre-breakout consolidation).
7. **ETF Structure Facts**: Real-time IOPV valuation, premium/discount rate %, total shares, and turnover rate.
8. **Swing Risk Reference (2*ATR)**: Dynamic trailing reference for short-term swing trades (not mechanical stop for core value holdings).
