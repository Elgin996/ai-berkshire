import argparse
import json
import os
import sys

import requests

# Ensure UTF-8 output across Windows, Linux, and macOS
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add parent directory to sys.path to allow sibling imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from calculate_indicators import compute_all_indicators
from fetch_data import fetch_tencent_quote, get_ohlcv_data


def format_markdown_report(sym_info: dict, summary: dict, quote_info: dict) -> str:
    """Generate a clean, structured, institutional-grade technical analysis report in Markdown."""
    sym = sym_info["canonical"]
    market = sym_info["market"]
    is_etf = sym_info["is_etf"]
    p = summary["price"]
    ma = summary["moving_averages"]
    macd = summary["macd"]
    rsi = summary["rsi"]
    boll = summary["bollinger"]
    vol = summary["volatility"]
    trend = summary["trend"]
    levels = summary["key_levels"]

    name_label = quote_info.get("name", "") if quote_info else ""
    header_title = f"# 技术分析报告: {sym} {name_label}".strip()

    md = []
    md.append(header_title)
    md.append(f"- **分析基准日期**: {summary['date']}")
    md.append(f"- **市场分类**: {market} {'(指数ETF)' if is_etf else ''}")
    md.append(f"- **综合趋势定性**: **{trend['desc']}**\n")

    # 1. 真实量价基准表
    md.append("## 一、 量价基准数据 (Ground-Truth OHLCV)")
    md.append("| 字段 | 数值 | 说明 |")
    md.append("| :--- | :---: | :--- |")
    md.append(f"| 最新收盘价 | **{p['close']}** | 前复权 (QFQ) 收盘价 |")
    md.append(f"| 开 / 高 / 低 | {p['open']} / {p['high']} / {p['low']} | 日内极值区间 |")
    md.append(f"| 成交量 (Volume) | {p['volume']:,} | 场内成交量 |")

    # ETF 特有字段展示
    if is_etf and quote_info:
        if quote_info.get("iopv") is not None:
            md.append(f"| 实时参考净值 (IOPV) | **{quote_info['iopv']}** | 估算单位净值 |")
        if quote_info.get("discount_rate_pct") is not None:
            dr = quote_info['discount_rate_pct']
            dr_state = "溢价" if dr > 0 else "折价"
            md.append(f"| 实时折溢价率 | **{dr:.2f}%** | 当前处于{dr_state}状态 |")
        if quote_info.get("shares_outstanding") is not None:
            shares_yi = quote_info['shares_outstanding'] / 1e8
            md.append(f"| 基金总份额 | **{shares_yi:.2f} 亿份** | 主力场内沉淀份额 |")
        if quote_info.get("turnover_rate") is not None:
            md.append(f"| 换手率 | **{quote_info['turnover_rate']:.2f}%** | 场内交易活跃度 |")

    # 2. 均线与趋势系统
    md.append("\n## 二、 移动平均线系统 (Moving Averages)")
    md.append("| 均线周期 | 数值 | 价格相对位置 |")
    md.append("| :--- | :---: | :--- |")
    for name, val in [("10 EMA (短期动能)", ma["ema10"]), ("20 SMA (月度中轴)", ma["sma20"]), ("50 SMA (中期牛熊)", ma["sma50"]), ("200 SMA (长期牛熊)", ma["sma200"])]:
        if val is not None:
            pos = "站上均线 (支撑)" if p["close"] >= val else "处于均线下方 (压制)"
            diff_pct = ((p["close"] - val) / val) * 100
            md.append(f"| {name} | {val:.2f} | {pos} ({diff_pct:+.2f}%) |")

    # 3. 动量与震荡指标
    md.append("\n## 三、 核心技术指标矩阵 (MACD & RSI & Bollinger)")
    md.append(f"- **MACD 指标**: DIF=`{macd['dif']}`, DEA=`{macd['dea']}`, 柱状图=`{macd['hist']}`  \n  ➔ **信号评估**: **{macd['signal']}**")
    md.append(f"- **RSI 强弱指标**: RSI(6)=`{rsi['rsi6']}`, RSI(14)=`{rsi['rsi14']}`  \n  ➔ **状态评估**: **{rsi['state']}**")
    md.append(f"- **布林通道 (20,2)**: 上轨=`{boll['upper']}`, 中轨=`{boll['mid']}`, 下轨=`{boll['lower']}`, 带宽=`{boll['bandwidth_pct']}%`  \n  ➔ **通道位置**: **{boll['position']}**")
    md.append(f"- **真实波幅 (ATR 14)**: `{vol['atr14']}` (日均波动幅度约 `{vol['atr_pct']}%`)")
    if vol.get("vwma20"):
        md.append(f"- **成交量加权均价 (VWMA 20)**: `{vol['vwma20']}`")

    # 4. 关键点位与操作建议
    md.append("\n## 四、 关键支撑阻力与风控点位")
    md.append("| 维度 | 关键价位 | 说明 |")
    md.append("| :--- | :--- | :--- |")
    res_str = " / ".join(map(str, levels["resistance_levels"])) if levels["resistance_levels"] else "暂无临近压力"
    sup_str = " / ".join(map(str, levels["support_levels"])) if levels["support_levels"] else "暂无临近支撑"
    md.append(f"| **上方阻力位 (Resistance)** | **{res_str}** | 突破需量能配合 |")
    md.append(f"| **下方支撑位 (Support)** | **{sup_str}** | 逢低回踩防守区间 |")
    md.append(f"| **建议防守止损点 (2*ATR)** | **{levels['stop_loss_suggested_2atr']}** | 跌破此位需严格控制仓位 |")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="Quantitative technical analysis tool for China A-shares, Hong Kong stocks, ETFs, and global equities."
    )
    parser.add_argument("symbol", type=str, help="Stock or ETF ticker symbol (e.g. 600519.SS, 0700.HK, 563360, NVDA)")
    parser.add_argument("--date", type=str, default=None, help="Analysis date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--format", type=str, choices=["markdown", "json"], default="markdown", help="Output format: markdown (default) or json")
    parser.add_argument("--no-quote", action="store_true", help="Disable real-time quote snapshot fetch")

    args = parser.parse_args()

    try:
        # 1. Fetch OHLCV data
        df, sym_info = get_ohlcv_data(args.symbol, as_of_date=args.date)

        # 2. Compute Indicators
        _, summary = compute_all_indicators(df)

        # 3. Fetch Real-time quote snapshot if available
        quote_info = {}
        if not args.no_quote and sym_info["market"] in ("CN", "HK"):
            try:
                quote_info = fetch_tencent_quote(sym_info["tencent_symbol"])
            except (requests.RequestException, ValueError, KeyError):
                pass

        # 4. Render output
        if args.format == "json":
            output_payload = {
                "symbol_info": sym_info,
                "quote_info": quote_info,
                "technical_summary": summary,
            }
            print(json.dumps(output_payload, ensure_ascii=False, indent=2))
        else:
            report_md = format_markdown_report(sym_info, summary, quote_info)
            print(report_md)

        sys.exit(0)

    except (RuntimeError, ValueError, KeyError, OSError, requests.RequestException) as e:
        if args.format == "json":
            print(json.dumps({"error": str(e), "symbol": args.symbol}, ensure_ascii=False))
        else:
            print(f"Error analyzing {args.symbol}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
