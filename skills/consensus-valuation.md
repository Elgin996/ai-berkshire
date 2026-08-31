---
name: consensus-valuation
description: >-
  Multi-Source Valuation & Consensus Fair-Value Analysis across 6 major financial platforms
  (Morningstar, Seeking Alpha, StockAnalysis, Yahoo Finance, MarketBeat, TipRanks).
  Aggregates quantitative fair values, analyst consensus ratings, price target bands (low/median/avg/high),
  valuation multiples (forward P/E, PEG, EV/EBITDA vs. 5-year history), and calculates cross-source statistical
  consensus and margin of safety.
---

# 多源公允价值与估值共识调研 (Multi-Source Consensus Valuation)

对 `$ARGUMENTS` 指定的美股/全球标的（如 `META`, `AAPL`, `GOOGL`, `MSFT`, `NVDA`, `AMZN`, `TSLA` 等）执行跨六大权威金融平台的自动化估值与共识目标价调研。

**核心定位**：解决“当前股票价格是否被低估、低估幅度几何、安全边际多大、下行底价在哪里”的关键定价问题。通过聚合独立评级机构（Morningstar）、专业投研社区（Seeking Alpha）、卖方数据聚合器（StockAnalysis / Yahoo Finance / MarketBeat）与顶尖分析师追踪引擎（TipRanks），消除单一信源偏差与主观幻觉。

---

## 适用场景

- 评估个股最新股价是否低估（如 “META 现在低估了吗？”, "看看苹果 AAPL 的六大平台估值共识"）
- 提取晨星分析师公允价值（Analyst Fair Value）与量化公允价值（Quant FV）及护城河评级
- 查询华尔街共识目标价区间（最高、中位数、均价、最低悲观底价）
- 检查前瞻估值乘数（FWD P/E, FWD PEG, EV/EBITDA）相对于历史 5 年均值的折溢价幅度
- 提取机构评级分布（买入/持有/卖出数量）与近期 90 天升级/降级异动动量

---

## 执行流程与工具调用

直接调用仓库内置的确定性数据采集与验算工具：

```bash
# 1. 对指定标的执行全量六源估值调研（输出标准 Markdown 研报）
python3 tools/multi_source_valuation.py META

# 2. 输出纯结构化 JSON（供多 Agent 下游投研流水线自动解析）
python3 tools/multi_source_valuation.py META --format json

# 3. 配合 financial_rigor.py 进行加权中位数与极值交叉核验
python3 tools/financial_rigor.py cross-validate --field target_price --values '{"Morningstar": 850, "StockAnalysis": 754.77, "Yahoo": 754.77, "MarketBeat": 785.22, "TipRanks": 751.78}' --unit USD
```

---

## 六大权威数据源覆盖维度

1. **Morningstar (晨星)**:
   - 分析师公允价值 (Analyst Fair Value Estimate)
   - 量化公允价值 (Quantitative Fair Value)
   - 经济护城河评级 (Wide / Narrow / None Moat)
   - 估值不确定性评级 (Low / Medium / High / Very High Uncertainty)
   - 晨星星级 (1★ - 5★) 与市价/公允价值比率 (P/FV)

2. **Seeking Alpha**:
   - 华尔街卖方共识得分 (1.00 - 5.00) 与评级分布
   - SA 独立分析师作者情绪分布 (Bullish / Neutral / Bearish)
   - 前瞻 Non-GAAP P/E 与较 5 年历史均值折溢价 (%)
   - 前瞻 PEG 比率（衡量成长与估值性价比，`< 1.0` 为典型低估）
   - 前瞻 EV / EBITDA 与较 5 年均值折价幅度

3. **StockAnalysis**:
   - S&P Global 覆盖分析师总数与共识评级 (Strong Buy / Buy / Hold / Sell)
   - 1 年期目标价统计：平均值、中位数、最高目标价、最低悲观目标价
   - 本财年与下财年营收及 EPS 一致预期增长率

4. **Yahoo Finance**:
   - 盘中实时与前收盘基准价、52 周高低波动区间
   - 1 年期分析师平均目标预测 (1y Target Est)
   - 滚动 TTM P/E 与前瞻 FWD P/E
   - 5 年预期 PEG 比率与 EV/EBITDA
   - 盘中市值 (Market Cap) 与企业价值 (Enterprise Value)

5. **MarketBeat**:
   - 华尔街综合共识得分 (1.00 - 3.00) 与评级定性 (Moderate Buy / Strong Buy)
   - 12 个月目标价预测极值与平均值
   - 过去 90 天内分析师评级升级 (Upgrades) 与降级 (Downgrades) 动量统计
   - 行业内相对评级优劣势对比

6. **TipRanks**:
   - 华尔街分析师共识与评级覆盖分布（买入/持有/卖出）
   - 12 个月平均预测目标价 (ptConsensus)
   - 独家 Smart Score 量化得分 (1 - 10 分)

---

## 估值定性与决策判定准则

在生成研报时，严格基于统计中位数与基本面乘数判定：

- **显著低估 (Significantly Undervalued)**：共识目标中位数潜在涨幅 $\ge +25\%$，且前瞻 PEG $< 1.0$ 或前瞻 P/E 较历史 5 年均值折价 $> 15\%$。
- **适度低估 (Moderately Undervalued)**：共识目标中位数潜在涨幅在 $+10\% \sim +25\%$ 之间。
- **估值合理 (Fairly Valued)**：共识目标中位数潜在波动在 $-10\% \sim +10\%$ 之间。
- **估值偏高 / 高估 (Overvalued)**：共识目标中位数潜在跌幅 $> 10\%$。
- **安全垫底线 (Downside Floor)**：以各大平台统计的最低悲观目标价为下行防守支撑线。
