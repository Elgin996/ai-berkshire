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
    vd = summary.get("volume_dynamics", {})
    vp = summary.get("volume_profile", {})

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

    # Format standardized volume
    raw_vol = p["volume"]
    if is_etf:
        lots = raw_vol / 100
        md.append(f"| 成交量 (Volume) | **{raw_vol:,} 份** ({lots:,.0f} 手) | 场内基金成交份额 |")
    elif market == "CN":
        lots = raw_vol / 100
        wan_shares = raw_vol / 10000
        md.append(f"| 成交量 (Volume) | **{raw_vol:,} 股** ({lots:,.0f} 手 / {wan_shares:.2f} 万股) | 场内实际成交股数与手数 |")
    elif market == "HK":
        md.append(f"| 成交量 (Volume) | **{raw_vol:,} 股** | 港股场内成交股数 |")
    else:
        md.append(f"| 成交量 (Volume) | **{raw_vol:,}** | 场内成交量 |")

    if quote_info:
        if quote_info.get("turnover_amount_wanyuan") is not None:
            amt_wy = quote_info["turnover_amount_wanyuan"]
            amt_str = f"{amt_wy / 10000:.2f} 亿元" if amt_wy >= 10000 else f"{amt_wy:.2f} 万元"
            md.append(f"| 成交额 (Turnover) | **{amt_str}** | 场内资金交投规模 |")
        if quote_info.get("turnover_rate") is not None:
            md.append(f"| 换手率 (Turnover Rate) | **{quote_info['turnover_rate']:.2f}%** | 当日筹码换手活跃度 |")
        if quote_info.get("shares_outstanding") is not None:
            so = quote_info["shares_outstanding"]
            unit_label = "亿份" if is_etf else "亿股"
            md.append(f"| 流通股本/份额 | **{so / 1e8:.2f} {unit_label}** ({int(so):,} {'份' if is_etf else '股'}) | 场内实际流通规模 |")
        if quote_info.get("market_cap_circ_yi") is not None and not is_etf:
            md.append(f"| 流通市值 | **{quote_info['market_cap_circ_yi']:.2f} 亿元** | 实时流通市值 |")

        # ETF 特有字段展示
        if is_etf:
            if quote_info.get("iopv") is not None:
                md.append(f"| 实时参考净值 (IOPV) | **{quote_info['iopv']}** | 估算单位净值 |")
            if quote_info.get("discount_rate_pct") is not None:
                dr = quote_info['discount_rate_pct']
                dr_state = "溢价" if dr > 0 else "折价"
                md.append(f"| 实时折溢价率 | **{dr:.2f}%** | 当前处于{dr_state}状态 |")

    # 2. 均线与趋势系统
    md.append("\n## 二、 移动平均线系统 (Moving Averages)")
    md.append("| 均线周期 | 数值 | 价格相对位置 |")
    md.append("| :--- | :---: | :--- |")
    for name, val in [("10 EMA (短期动能)", ma["ema10"]), ("20 SMA (月度中轴)", ma["sma20"]), ("50 SMA (中期牛熊)", ma["sma50"]), ("200 SMA (长期牛熊)", ma["sma200"])]:
        if val is not None:
            pos = "站上均线 (支撑)" if p["close"] >= val else "处于均线下方 (压制)"
            diff_pct = ((p["close"] - val) / val) * 100
            md.append(f"| {name} | {val:.2f} | {pos} ({diff_pct:+.2f}%) |")

    # 3. 量价配合与筹码分布 (Volume Dynamics & Profile)
    if vd or vp:
        md.append("\n## 三、 量价配合与筹码分布 (Volume Profile)")
        if vd:
            vma5_str = f"{int(vd['vma5']):,}" if vd.get('vma5') is not None else "--"
            vma20_str = f"{int(vd['vma20']):,}" if vd.get('vma20') is not None else "--"
            md.append(f"- **量能均线对比**: 5日均量 (VMA5)=`{vma5_str}`, 20日均量 (VMA20)=`{vma20_str}`")
            md.append(f"- **实时量比**: 5日量比=`{vd.get('vol_ratio_5', '--')}`, 20日量比=`{vd.get('vol_ratio_20', '--')}`")
            md.append(f"- **量价配合评估**: **{vd.get('desc', '--')}**")
        if vp:
            poc = vp.get("poc", {})
            ov = vp.get("overhead_supply", {})
            sp = vp.get("support_shelf", {})
            if poc:
                md.append(f"- **筹码控制峰 (POC)**: 价格密集区 `[{poc.get('range')}]` (中轴 `{poc.get('mid_price')}` 元, 占近 {vp.get('window_bars')} 日总成交量 `{poc.get('vol_pct')}%`)")
            if ov and ov.get("peak_cluster"):
                pk = ov["peak_cluster"]
                md.append(f"- **上方高位套牢筹码区**: 核心峰 `[{pk.get('range')}]` (占比 `{pk.get('vol_pct')}%`), 上方累计套牢筹码占近 {vp.get('window_bars')} 日总成交量 **{ov.get('total_trapped_vol_pct')}%**")
            if sp and sp.get("peak_cluster"):
                sk = sp["peak_cluster"]
                md.append(f"- **下方主要筹码支撑平台**: 核心峰 `[{sk.get('range')}]` (占比 `{sk.get('vol_pct')}%`), 下方累计承接筹码占近 {vp.get('window_bars')} 日总成交量 **{sp.get('total_support_vol_pct')}%**")

    # 4. 动量与震荡指标
    md.append("\n## 四、 核心技术指标矩阵 (MACD & RSI & Bollinger)")
    md.append(f"- **MACD 指标**: DIF=`{macd['dif']}`, DEA=`{macd['dea']}`, 柱状图=`{macd['hist']}`  \n  ➔ **信号评估**: **{macd['signal']}**")
    md.append(f"- **RSI 强弱指标**: RSI(6)=`{rsi['rsi6']}`, RSI(14)=`{rsi['rsi14']}`  \n  ➔ **状态评估**: **{rsi['state']}**")
    md.append(f"- **布林通道 (20,2)**: 上轨=`{boll['upper']}`, 中轨=`{boll['mid']}`, 下轨=`{boll['lower']}`, 带宽=`{boll['bandwidth_pct']}%`  \n  ➔ **通道位置**: **{boll['position']}**")
    md.append(f"- **真实波幅 (ATR 14)**: `{vol['atr14']}` (日均波动幅度约 `{vol['atr_pct']}%`)")
    if vol.get("vwma20"):
        md.append(f"- **成交量加权均价 (VWMA 20)**: `{vol['vwma20']}`")

    # 5. 关键点位与操作建议
    md.append("\n## 五、 关键支撑阻力与风控点位")
    md.append("| 维度 | 关键价位 (元) | 算法来源与技术含义 |")
    md.append("| :--- | :---: | :--- |")
    
    res_details = levels.get("resistance_details", [])
    if res_details:
        for i, r in enumerate(res_details, 1):
            md.append(f"| **上方阻力 R{i}** | **{r['price']:.2f}** | {r['source']} |")
    else:
        res_str = " / ".join(map(str, levels["resistance_levels"])) if levels["resistance_levels"] else "暂无临近压力"
        md.append(f"| **上方阻力位 (Resistance)** | **{res_str}** | 突破需量能配合 |")

    sup_details = levels.get("support_details", [])
    if sup_details:
        for i, s in enumerate(sup_details, 1):
            md.append(f"| **下方支撑 S{i}** | **{s['price']:.2f}** | {s['source']} |")
    else:
        sup_str = " / ".join(map(str, levels["support_levels"])) if levels["support_levels"] else "暂无临近支撑"
        md.append(f"| **下方支撑位 (Support)** | **{sup_str}** | 逢低回踩防守区间 |")

    stop_loss = levels.get("stop_loss_suggested_2atr")
    if stop_loss is not None:
        md.append(f"| **建议防守止损点 (2*ATR)** | **{stop_loss:.2f}** | 动态移动跟踪止损线，跌破需严格控制仓位 |")
    else:
        md.append("| **建议防守止损点 (2*ATR)** | **暂无足够数据** | 建议以均线或前低作为止损基准 |")

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
