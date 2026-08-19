---
name: technical-analysis
description: >-
  Quantitative technical analysis skill for China A-shares, Hong Kong stocks, Index ETFs, and Global Equities.
  Fetches front-rehabilitated (QFQ) OHLCV data, calculates 8+ quant indicators (10 EMA, 20/50/200 SMA, MACD, RSI,
  Bollinger Bands, ATR, VWMA, ETF IOPV/discount rate, shares outstanding), and generates structured institutional-grade
  technical analysis reports with support, resistance, and risk-control levels.
---

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

依赖（每个环境安装一次）：

```bash
pip install -r tools/technical-analysis/requirements.txt
```

---

## 参数支持

| 参数 | 类型 | 是否必填 | 默认值 | 说明 |
| :--- | :---: | :---: | :---: | :--- |
| `symbol` | `string` | **是** | - | 股票/ETF代码（如 `600519.SS`, `300394.SZ`, `0700.HK`, `563360`, `NVDA`） |
| `--date` | `string` | 否 | `today` | 指定基准日期（`YYYY-MM-DD` 格式），自动截断未来数据 |
| `--format` | `string` | 否 | `markdown` | 输出格式：`markdown`（格式化简报）或 `json`（全量量化指标字典） |
| `--detailed` | `flag` | 否 | `False` | 在 Markdown 简报附录中输出全量技术指标明细 |
| `--no-quote` | `flag` | 否 | `False` | 关闭实时盘中行情快照抓取 |

---

## 核心量化维度说明 (高信噪比极简工具箱)

1. **真实量价事实 (Ground-Truth OHLCV)**：抓取前复权 (QFQ) 真实开高低收成交量与实时快照，标准化成交量纲（手/万股/份），防止模型幻觉。
2. **趋势中轴体系 (50 & 200 SMA)**：
   - `50 SMA`：中期牛熊分水岭
   - `200 SMA`：长期机构核心生命线
3. **基准量能对比 (Volume vs VMA20)**：量比分析与放量/缩量状态定性。
4. **筹码分布地图 (Volume Profile / VPVR - 90日窗口)**：
   - `POC (Point of Control)`：价格密集控制峰
   - `Overhead Supply %`：上方高位套牢筹码占比
   - `Support Shelf %`：下方主要承接筹码平台占比
5. **情绪过滤器 (RSI 14)**：防 FOMO 追高（>70）与防恐慌杀跌（<30）的情绪过滤器。
6. **波动与变盘预警 (Bollinger Bandwidth & ATR 14)**：衡量日均真实波幅与通道带宽挤压（变盘蓄势期）。
7. **ETF 市场结构事实**：实时 IOPV、折溢价率（%）、场内流通总份额与换手率。
8. **波段风控参考 (2*ATR)**：仅作为短线波段交易的移动防守参考线，避免机械套用于价值投资核心底仓。

---

## 价值投资与技术分析融合建议

在撰写分析报告时，保持以下纪律：
- **基本面定战略**：以商业模式、护城河与公允估值确定“买不买、买多少”。
- **技术面定战术**：以 50/200 均线、筹码 POC 和 RSI 情绪过滤确定“何时分批建仓与挂单区间”。
- **风控差异化**：右侧短线交易严格参考 `2*ATR` 防守；左侧价值投资持仓依靠估值安全边际与基本面跟踪，切忌被 A 股日常波动震荡出局。
- **ETF 折溢价**：溢价过高（>0.5%）避免盲目追高，折价较大且成份股基本面扎实时可择机低吸套利。
