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


def format_markdown_report(sym_info: dict, summary: dict, quote_info: dict, detailed: bool = False) -> str:
    """Generate a clean, structured, institutional-grade minimalist technical analysis report in Markdown."""
    sym = sym_info["canonical"]
    market = sym_info["market"]
    is_etf = sym_info["is_etf"]
    p = summary["price"]
    ma = summary["moving_averages"]
    macd = summary["macd"]
    rsi = summary["rsi"]
    boll = summary["bollinger"]
    vol = summary["volatility"]
    vd = summary.get("volume_dynamics", {})
    vp = summary.get("volume_profile", {})

    name_label = quote_info.get("name", "") if quote_info else ""
    header_title = f"# 技术分析简报: {sym} {name_label}".strip()

    md = []
    md.append(header_title)
    market_str = "A股 (CN)" if market == "CN" else ("港股 (HK)" if market == "HK" else market)
    curr_unit = "元" if market == "CN" else ("港元" if market == "HK" else "美元")
    if is_etf:
        market_str += " 指数ETF"
    md.append(f"- **分析基准日期**: {summary['date']} | **市场分类**: {market_str}\n")

    # 一、 市场事实与真实量价 (Ground Truth)
    md.append("## 一、 市场事实与真实量价 (Ground Truth)")
    md.append(f"- **最新收盘 (QFQ)**: **{p['close']}** {curr_unit} (日内极值: {p['low']} ~ {p['high']})")

    # Format standardized volume
    raw_vol = p["volume"]
    if is_etf:
        units = raw_vol * 100
        wan_units = units / 10000
        vol_str = f"**{raw_vol:,.0f} 手** ({wan_units:.2f} 万份 / {units:,.0f} 份)"
    elif market == "CN":
        shares = raw_vol * 100
        wan_shares = shares / 10000
        vol_str = f"**{raw_vol:,.0f} 手** ({wan_shares:.2f} 万股 / {shares:,.0f} 股)"
    elif market == "HK":
        vol_str = f"**{raw_vol:,.0f} 股**"
    else:
        vol_str = f"**{raw_vol:,.0f}**"

    fact_items = [f"- **成交量与规模**: {vol_str}"]
    if quote_info:
        if quote_info.get("turnover_amount_wanyuan") is not None:
            amt_wy = quote_info["turnover_amount_wanyuan"]
            amt_unit = "港元" if market == "HK" else "元"
            amt_str = f"{amt_wy / 10000:.2f} 亿{amt_unit}" if amt_wy >= 10000 else f"{amt_wy:.2f} 万{amt_unit}"
            fact_items.append(f"**成交额**: **{amt_str}**")
        if quote_info.get("turnover_rate") is not None:
            fact_items.append(f"**换手率**: **{quote_info['turnover_rate']:.2f}%**")
    md.append(" | ".join(fact_items))

    # Float & Market Cap / ETF Friction
    if quote_info:
        scale_items = []
        if quote_info.get("shares_outstanding") is not None:
            so = quote_info["shares_outstanding"]
            unit_label = "亿份" if is_etf else "亿股"
            scale_items.append(f"**流通盘规模**: **{so / 1e8:.2f} {unit_label}** ({int(so):,} {'份' if is_etf else '股'})")
        if quote_info.get("market_cap_circ_yi") is not None and not is_etf:
            scale_items.append(f"**流通市值**: **{quote_info['market_cap_circ_yi']:.2f} 亿{curr_unit}**")
        if scale_items:
            md.append(f"- {' | '.join(scale_items)}")

        if is_etf:
            etf_items = []
            if quote_info.get("iopv") is not None:
                etf_items.append(f"**实时参考净值 (IOPV)**: **{quote_info['iopv']}**")
            if quote_info.get("discount_rate_pct") is not None:
                dr = quote_info['discount_rate_pct']
                dr_state = "溢价" if dr > 0 else "折价"
                etf_items.append(f"**实时折溢价率**: **{dr:+.2f}% ({dr_state})**")
            if etf_items:
                md.append(f"- {' | '.join(etf_items)}")

    # 二、 趋势与均线中轴 (Trend & Structural Levels)
    md.append("\n## 二、 趋势与均线中轴 (Trend & Structural Levels)")
    if ma.get("sma50") is not None:
        val50 = ma["sma50"]
        diff50 = ((p["close"] - val50) / val50) * 100
        pos50 = "处于均线上方 (中期偏多)" if p["close"] >= val50 else "处于均线下方 (中期承压)"
        md.append(f"- **50 SMA (中期牛熊分界)**: **{val50:.2f}** {curr_unit} (现价相对偏离: **{diff50:+.2f}%**，{pos50})")
    if ma.get("sma200") is not None:
        val200 = ma["sma200"]
        diff200 = ((p["close"] - val200) / val200) * 100
        pos200 = "站上长期生命线 (长期偏多)" if p["close"] >= val200 else "位于长期生命线下方 (长期偏弱)"
        md.append(f"- **200 SMA (长期机构生命线)**: **{val200:.2f}** {curr_unit} (现价相对偏离: **{diff200:+.2f}%**，{pos200})")

    if vd:
        vma20_val = vd.get("vma20")
        vol_ratio_20 = vd.get("vol_ratio_20")
        if vma20_val is not None and vol_ratio_20 is not None:
            v_desc = "放量" if vol_ratio_20 >= 1.2 else ("缩量" if vol_ratio_20 <= 0.8 else "量能平稳")
            md.append(f"- **基准量能对比**: 今日成交量 / 20日均量 (VMA20) = **{vol_ratio_20:.2f}** ({v_desc}，{vd.get('desc', '')})")

    # 三、 筹码分布与结构地图 (Volume Profile - 90日窗口)
    if vp:
        window_days = vp.get("window_bars", 90)
        md.append(f"\n## 三、 筹码分布与结构地图 (Volume Profile - {window_days}日)")
        poc = vp.get("poc", {})
        ov = vp.get("overhead_supply", {})
        sp = vp.get("support_shelf", {})
        if poc:
            md.append(f"- **筹码控制峰 (POC)**: 价格密集区 `[{poc.get('range')}]` (中轴 **{poc.get('mid_price')}** {curr_unit}, 占近 {window_days} 日总成交量 **{poc.get('vol_pct')}%**)")
        if ov:
            pk = ov.get("peak_cluster")
            pk_str = f" (核心套牢峰: `[{pk.get('range')}]` 占 {pk.get('vol_pct')}%)" if pk else ""
            md.append(f"- **上方套牢筹码**: 累计套牢筹码占近 {window_days} 日总成交量 **{ov.get('total_trapped_vol_pct')}%**{pk_str}")
        if sp:
            sk = sp.get("peak_cluster")
            sk_str = f" (主要承接峰: `[{sk.get('range')}]` 占 {sk.get('vol_pct')}%)" if sk else ""
            md.append(f"- **下方承接支撑**: 累计承接筹码占近 {window_days} 日总成交量 **{sp.get('total_support_vol_pct')}%**{sk_str}")

    # 四、 情绪与波动风控 (Sentiment & Risk Filter)
    md.append("\n## 四、 情绪与波动风控 (Sentiment & Risk Filter)")
    rsi14_val = rsi.get("rsi14")
    if rsi14_val is not None:
        if rsi14_val >= 70:
            rsi_hint = "进入超买区，谨防冲高回落，切忌盲目追高"
        elif rsi14_val <= 30:
            rsi_hint = "进入超卖区，短线情绪释放充分，切忌恐慌杀跌"
        elif rsi14_val >= 55:
            rsi_hint = "处于多头偏强运行区间"
        elif rsi14_val <= 45:
            rsi_hint = "处于偏弱整理区间"
        else:
            rsi_hint = "处于中性平衡区间"
        md.append(f"- **情绪过滤器 (RSI 14)**: **{rsi14_val:.2f}** ({rsi_hint})")

    atr14_val = vol.get("atr14")
    atr_pct = vol.get("atr_pct")
    if atr14_val is not None:
        pct_str = f" (日均真实波幅约 **{atr_pct:.2f}%**)" if atr_pct is not None else ""
        md.append(f"- **真实波幅 (ATR 14)**: **{atr14_val:.2f}** {curr_unit}{pct_str}")

    bw = boll.get("bandwidth_pct")
    if bw is not None:
        bw_desc = "通道极度收窄，处于低波动变盘蓄势期" if bw < 6.0 else ("通道扩张中，处于趋势释放期" if bw > 15.0 else "通道宽度正常")
        md.append(f"- **布林通道带宽 (Bandwidth)**: **{bw:.2f}%** ({bw_desc})")

    stop_2atr = summary.get("key_levels", {}).get("stop_loss_suggested_2atr")
    if stop_2atr is not None:
        md.append(f"- **波段交易参考防守位 (2*ATR)**: **{stop_2atr:.2f}** {curr_unit}\n  > [!NOTE]\n  > *风控说明：`2*ATR` 仅供短线或右侧波段交易防守参考。核心价值投资持仓（左侧/定投）应以商业模式与估值安全边际为根本准绳，避免被 A 股日常波动洗出。*")

    # If detailed is True, append auxiliary technical tables
    if detailed:
        md.append("\n## 附录：全量量化指标明细 (Detailed Metrics)")
        md.append(f"- **10 EMA**: {ma.get('ema10')} | **20 SMA**: {ma.get('sma20')} | **VWMA 20**: {vol.get('vwma20')}")
        md.append(f"- **MACD (12,26,9)**: DIF={macd.get('dif')}, DEA={macd.get('dea')}, Hist={macd.get('hist')} | 信号: {macd.get('signal')}")
        md.append(f"- **RSI (6,14)**: RSI6={rsi.get('rsi6')}, RSI14={rsi.get('rsi14')}")
        md.append(f"- **布林带 (20,2)**: 上轨={boll.get('upper')}, 中轨={boll.get('mid')}, 下轨={boll.get('lower')}, 位置={boll.get('position')}")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="Quantitative technical analysis tool for China A-shares, Hong Kong stocks, ETFs, and global equities."
    )
    parser.add_argument("symbol", type=str, help="Stock or ETF ticker symbol (e.g. 600519.SS, 0700.HK, 563360, NVDA)")
    parser.add_argument("--date", type=str, default=None, help="Analysis date in YYYY-MM-DD format (default: today)")
    parser.add_argument("--format", type=str, choices=["markdown", "json"], default="markdown", help="Output format: markdown (default) or json")
    parser.add_argument("--detailed", action="store_true", help="Include full detailed indicator metrics in markdown output")
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
            report_md = format_markdown_report(sym_info, summary, quote_info, detailed=args.detailed)
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
