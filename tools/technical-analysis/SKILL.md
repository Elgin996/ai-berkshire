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
python skills/technical-analysis/scripts/run_analysis.py 600519.SS

# 2. Analyze Hong Kong stock (e.g. 0700.HK, 9988.HK, 3690.HK)
python skills/technical-analysis/scripts/run_analysis.py 0700.HK

# 3. Analyze Index ETF with real-time IOPV, discount rate & shares (e.g. 563360, 510300)
python skills/technical-analysis/scripts/run_analysis.py 563360

# 4. Analyze on a historical date (Backtesting / Anti-lookahead)
python skills/technical-analysis/scripts/run_analysis.py 300394.SZ --date 2026-08-14

# 5. Programmatic JSON output mode (for structured agent downstream parsing)
python skills/technical-analysis/scripts/run_analysis.py 600519.SS --format json
```

---

## Parameter Reference

| Parameter | Type | Required | Default | Description |
| :--- | :---: | :---: | :---: | :--- |
| `symbol` | `string` | **Yes** | - | Stock/ETF ticker (e.g. `600519.SS`, `300394.SZ`, `0700.HK`, `563360`, `NVDA`) |
| `--date` | `string` | No | `today` | Date in `YYYY-MM-DD` format. Future rows are truncated. |
| `--format` | `string` | No | `markdown` | Output format: `markdown` (formatted report) or `json` (raw metrics dict). |
| `--no-quote` | `flag` | No | `False` | Disables real-time quote snapshot fetch. |

---

## Core Technical Dimensions Covered

1. **Ground-Truth Price Table**: Real QFQ Open/High/Low/Close/Volume to prevent model hallucination.
2. **Moving Averages (EMA 10, SMA 20, SMA 50, SMA 200)**: Trend alignment classification (Strong Bullish, Bullish, Consolidating, Bearish, Strong Bearish).
3. **MACD**: DIF (12, 26), DEA (9), Histogram, and Golden/Death cross signal detection.
4. **RSI (6, 14)**: Overbought (>75), Oversold (<25), and momentum zones.
5. **Bollinger Bands (20, 2)**: Bandwidth % and channel position.
6. **Volatility (ATR 14)**: Daily volatility in points & %, 2*ATR dynamic trailing stop-loss level.
7. **ETF Metrics (if ETF)**: Real-time IOPV valuation, premium/discount rate %, total shares outstanding, and turnover rate.
8. **Key Price Levels**: Nearest 3 resistance levels, 3 support levels, and suggested stop-loss level.
