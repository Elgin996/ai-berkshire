---
name: technical-analysis
description: >-
  Quantitative technical analysis skill for China A-shares, Hong Kong stocks, Index ETFs, and Global Equities.
  Fetches front-rehabilitated (QFQ) OHLCV data, calculates 8+ quant indicators (10 EMA, 20/50/200 SMA, MACD, RSI,
  Bollinger Bands, ATR, VWMA, ETF IOPV/discount rate, shares outstanding), and generates structured institutional-grade
  technical analysis reports with support, resistance, and risk-control levels.
---

## Codex adapter note

This skill is generated from `skills/technical-analysis.md` so Claude Code and Codex users share one canonical workflow.

- Treat `$ARGUMENTS` as the user's request in the current Codex thread.
- When the source mentions Claude-only surfaces such as Task, Agent, WebSearch, Bash, Read, or Write, use the closest Codex capability available in this session: subagents when available, web search when needed, shell commands for local tools, and normal file edits for workspace files.
- Use shared project tools from `tools/` in this repository. Prefer running commands from the repository root with paths like `python3 tools/financial_rigor.py ...`; if the current thread starts outside the repo, locate the actual checkout path first instead of assuming a fixed home-directory path.
- Before starting research, run the `date` command to confirm today's date; treat it as the baseline for "latest" data and state the data cutoff date in the report header. Never assume the current date from training data.
- Preserve the research quality rules from `AGENTS.md`: cross-check financial data, use exact arithmetic tools for valuation/math, and clearly label uncertainty and source gaps.

# 技术分析：A股/港股/ETF/美股 量化技术指标与量价形态分析

对 $ARGUMENTS 执行确定性、零幻觉的量化技术分析与量价形态评估。

**核心定位**：基本面研究（四大师框架）解决"买什么（Good Business & Moat）与什么价格买（Fair Valuation）"，技术分析解决"何时买入、如何建仓（Entry Timing）与风控止损（Dynamic Risk Management）"。

---

## 适用场景

- 针对个股或 ETF 的技术面诊断（如 "分析 600519.SS", "看看腾讯 0700.HK 技术面", "563360 ETF 怎么看？"）
- 均线多空排列、MACD 金叉/死叉、RSI 超买超卖、布林通道突破等量价形态扫描
- 寻找精准建仓区间、分批加仓点位、支撑/阻力位核算以及 2*ATR 动态跟踪止损位
- 指数 ETF 实时折溢价率套利与份额申赎异动分析

---

## 执行流程与工具调用

直接调用仓库内置的量化分析脚本工具：

```bash
# 1. A股分析（支持标准代码如 600519.SS, 300394.SZ, 688012.SH，也支持6位纯数字）
python3 tools/technical-analysis/scripts/run_analysis.py 600519.SS

# 2. 港股分析（支持 0700.HK, 9988.HK, 3690.HK 等）
python3 tools/technical-analysis/scripts/run_analysis.py 0700.HK

# 3. 宽基 / 行业指数 ETF 分析（包含实时 IOPV、折溢价率与总份额监控）
python3 tools/technical-analysis/scripts/run_analysis.py 563360

# 4. 指定历史基准日期分析（用于回测与防未来函数验证）
python3 tools/technical-analysis/scripts/run_analysis.py 300394.SZ --date 2026-08-14

# 5. 结构化 JSON 模式（供多 Agent 下游流水线解析）
python3 tools/technical-analysis/scripts/run_analysis.py 600519.SS --format json
```

---

## 参数支持

| 参数 | 类型 | 是否必填 | 默认值 | 说明 |
| :--- | :---: | :---: | :---: | :--- |
| `symbol` | `string` | **是** | - | 股票/ETF代码（如 `600519.SS`, `300394.SZ`, `0700.HK`, `563360`, `NVDA`） |
| `--date` | `string` | 否 | `today` | 指定基准日期（`YYYY-MM-DD` 格式），自动截断未来数据 |
| `--format` | `string` | 否 | `markdown` | 输出格式：`markdown`（格式化报告）或 `json`（原始量化指标字典） |
| `--no-quote` | `flag` | 否 | `False` | 关闭实时盘中行情快照抓取 |

---

## 八大量化维度说明

1. **真实量价基准表 (Ground-Truth OHLCV)**：抓取前复权 (QFQ) 真实开高低收成交量，防止模型产生幻觉。
2. **移动平均线系统 (Moving Averages)**：
   - `10 EMA`：短期动量中轴
   - `20 SMA`：月度多空分水岭
   - `50 SMA`：中期牛熊分界线
   - `200 SMA`：长期机构牛熊中轴
3. **MACD 动量震荡**：DIF (12, 26)、DEA (9)、MACD 柱状图，实时识别零轴上下金叉/死叉与背离状态。
4. **RSI 强弱指标**：RSI(6) 与 RSI(14)，评估极端超买 (>75)、极端超卖 (<25) 及多空动量区。
5. **布林通道 (Bollinger Bands 20, 2)**：计算上轨、中轨、下轨及通道带宽百分比，识别缩量震荡突破与通道位置。
6. **真实波幅与动态风控 (ATR 14)**：衡量日均真实波动幅度，提供 `2*ATR` 动态移动止损位。
7. **ETF 特征指标**：实时 IOPV（参考净值）、折溢价率（%）、场内流通总份额与换手率。
8. **关键点位矩阵**：算法自动推算上方临近 3 档压力位与下方临近 3 档支撑位。

---

## 价值投资与技术分析融合建议

在撰写分析报告时，保持以下纪律：
- **买入点位**：当价值投资框架给出"低估/合理"结论时，技术面寻找"回踩均线支撑"或"底背离金叉"作为分批介入时机。
- **持股纪律**：趋势向上（多头排列）时让利润奔跑；趋势破位（跌破 200 SMA 或跌破 2*ATR 防守位）时警惕基本面发生未被察觉的恶化。
- **ETF 折溢价**：溢价过高（>0.5%）避免盲目追高，折价较大且指数成份基本面扎实时可择机低吸套利。
