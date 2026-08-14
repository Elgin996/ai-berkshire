中文 | [English](README_EN.md) | [日本語](README_JA.md)

[![GitHub Trending](https://trendshift.io/api/badge/repositories/63696)](https://trendshift.io/repositories/63696)

# AI Berkshire - AI 时代的价值投资研究框架

> "Price is what you pay, value is what you get." — Warren Buffett

**AI Berkshire** 是一套同时兼容 **Claude Code** 与 **Codex** 的专业级投资研究 Skill 合集。框架将巴菲特、芒格、段永平、李录四位价值投资大师的方法论系统化、结构化，通过多 Agent 协作和严谨的数据校验工具，让个人投资者也能拥有机构级的投研能力。

---

## 核心特性

- **四大师多视角对抗**：融合段永平（商业模式本质）、巴菲特（护城河与估值）、芒格（逆向风险检验）、李录（长期确定性），多视角碰撞避免盲点。
- **多 Agent 并行投研**：调度 4 个独立 Agent 分别搜集一手信息并独立判断，由 Team Lead 综合决策，研究深度倍增。
- **结构化反偏见与硬核纪律**：内置信息丰富度评级（A/B/C）、芒格式逆向检验、快速否决清单及镜子测试，杜绝 AI 模棱两可。
- **严谨金融计算**：内置 Python `Decimal` 精确计算与多源交叉校验工具，杜绝 LLM 幻觉与计算偏差。
- **全流程覆盖**：涵盖个股深度研报、一手财报精读、行业漏斗筛选、持仓管理与股价异动归因。

---

## 整体架构

<p align="center">
  <img src="assets/architecture.svg" alt="AI Berkshire 整体架构" width="760" />
</p>

- **Skill 层**：提供 20 个开箱即用的投研入口（深度研究、财报精读、行业筛选、持仓管理、思维工具）。
- **Agent 层**：支持 Team Lead 并行调度四大师 Agent 进行独立调研、互相挑战与综合研判。
- **工具层**：提供精准财务计算、交叉验证、多数据源接入与报告质量抽检工具。

---

## Skills 清单（21个）

### 🔬 深度研究
| Skill | 用途 | 适用场景 |
|---|---|---|
| [`/investment-research`](skills/investment-research.md) | 四大师综合深度分析 | 上市公司全方位价值投资研究 |
| [`/investment-team`](skills/investment-team.md) | 多 Agent 并行投研团队 | 4 Agent 并行调研，快速且全面 |
| [`/management-deep-dive`](skills/management-deep-dive.md) | 管理层纵深研究 | 管理层为核心变量时的深度剖析 |
| [`/private-company-research`](skills/private-company-research.md) | 未上市公司深度研究 | 针对未上市标的（如 SpaceX、蚂蚁等）的多源拼凑与估值 |
| [`/deep-company-series`](skills/deep-company-series.md) | 深度长文系列拆解 | 公众号级多篇深度研究闭环 |

### 📊 财报与技术分析
| Skill | 用途 | 适用场景 |
|---|---|---|
| [`/earnings-review`](skills/earnings-review.md) | 财报精读（一手资料） | 聚焦原始财报数据与附注，不依赖二手研报 |
| [`/earnings-team`](skills/earnings-team.md) | 财报精读团队 + 发布 | 四大师解读财报 → 编辑润色 → 读者评审 |
| [`/technical-analysis`](skills/technical-analysis.md) | 量化技术面与量价分析 | 均线、MACD、RSI、布林带、ATR风控止损与ETF折溢价 |

### 🏭 行业与筛选
| Skill | 用途 | 适用场景 |
|---|---|---|
| [`/industry-research`](skills/industry-research.md) | 产业链全景扫描 | 行业全景剖析与产业链环节切片 |
| [`/industry-funnel`](skills/industry-funnel.md) | 行业漏斗筛选 | 全市场 → 粗筛 ≤10 家 → 终选 3 家并形成组合建议 |
| [`/quality-screen`](skills/quality-screen.md) | 去劣硬指标初筛 | 7 条硬指标快速剔除非一流公司 |
| [`/bottleneck-hunter`](skills/bottleneck-hunter.md) | 供应链瓶颈猎手 | 寻找超级趋势下的物理瓶颈与核心节点 |
| [`/investment-checklist`](skills/investment-checklist.md) | 买入前 Checklist | 六关快速筛选与镜子测试，10分钟定去留 |

### 📈 持仓与动态
| Skill | 用途 | 适用场景 |
|---|---|---|
| [`/income-investment`](skills/income-investment.md) | 收益型投资分析 | 识别高股息、可持续收益与收益率陷阱 |
| [`/portfolio-review`](skills/portfolio-review.md) | 组合管理与优化 | 仓位结构、集中度评估与再平衡建议 |
| [`/thesis-tracker`](skills/thesis-tracker.md) | 投资论文追踪 | 跟踪买入逻辑与可证伪指标 |
| [`/thesis-drift`](skills/thesis-drift.md) | 投资论文漂移检测 | 对比两期研报，识别基本面与估值变化 |
| [`/news-pulse`](skills/news-pulse.md) | 股价异动快速归因 | 10分钟快速定性异动原因（价值/情绪/资金/未知） |

### 🧠 思维与数据
| Skill | 用途 | 适用场景 |
|---|---|---|
| [`/dyp-ask`](skills/dyp-ask.md) | 段永平问答模拟 | 从商业常识与本分视角解答商业/投资问题 |
| [`/financial-data`](skills/financial-data.md) | 财务数据交叉验证 | 多源数据比对与防伪规范 |
| [`/wechat-article`](skills/wechat-article.md) | 投研文章撰写 | 自动生成结构严谨、可读性强的投研长文 |

---

## 快速开始

### 1. 安装 AI 客户端

**Claude Code**:
```bash
npm install -g @anthropic-ai/claude-code
```

**Codex**:
```bash
# macOS / Linux
curl -fsSL https://chatgpt.com/codex/install.sh | sh
# 或 Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

### 2. 克隆与安装 Skills

```bash
git clone https://github.com/Elgin996/ai-berkshire.git
cd ai-berkshire
```

- **Claude Code 用户**:
  - macOS / Linux: `./scripts/install-claude-commands.sh`
  - Windows: `.\scripts\install-claude-commands.bat`
- **Codex 用户**:
  - macOS / Linux: `./scripts/install-codex-skills.sh`
  - Windows: `.\scripts\install-codex-skills.bat`

### 3. 运行示例

在 **Claude Code** 中直接输入 Slash Command：
```bash
# 深度个股研究
/investment-research 腾讯

# 多 Agent 团队并行研究
/investment-team 美团

# 财报一手精读
/earnings-review 腾讯 2025Q4

# 量化技术面与关键点位分析
/technical-analysis 600519.SS

# 行业漏斗筛选
/industry-funnel AI算力

# 股价异动 10 分钟归因
/news-pulse 拼多多 跌10% 一周内
```

在 **Codex** 中使用对应 Skill：
```text
使用 investment-research 研究腾讯
使用 technical-analysis 分析 600519.SS
使用 earnings-review 分析 PDD 2025年报
使用 industry-funnel 筛选 AI算力
```

---

## 金融数据与严谨性工具

项目内置严谨性计算工具（`tools/financial_rigor.py`），采用 Python `decimal.Decimal` 规避浮点与心算误差：

| 工具功能 | 命令 | 用途 |
|---|---|---|
| 市值精确核算 | `verify-market-cap` | 结合股价与总股本精确核准市值与货币单位 |
| 估值指标复算 | `verify-valuation` | 精确计算 PE、PB、ROE、FCF Yield 等 |
| 多源交叉比对 | `cross-validate` | 比对多个独立数据源，超出误差容限时自动告警 |
| 三情景估值模型 | `three-scenario` | 乐观 / 中性 / 悲观三情景价格区间测算 |

### 数据源支持
- **A股/港美股数据源**：支持 `mootdx`（通达信 TCP）、腾讯财经、东方财富（内置限流与防封机制）、新浪财经、同花顺等免费数据源。

---



## 免责声明

本项目仅供学习与研究使用，不构成任何投资建议。投资有风险，决策需谨慎。请始终做好自己的尽职调查（DYOR）。

## License

[MIT License](LICENSE)
