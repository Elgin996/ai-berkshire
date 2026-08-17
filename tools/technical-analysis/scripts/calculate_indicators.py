from typing import Any

import numpy as np
import pandas as pd
from stockstats import wrap


def compute_all_indicators(df_input: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Compute comprehensive technical indicators using vector operations and stockstats.

    Returns:
      (indicator_df, latest_metrics_summary)
    """
    df = df_input.copy()
    if "Date" not in df.columns:
        raise ValueError("DataFrame must have a 'Date' column")

    df = df.sort_values("Date").reset_index(drop=True)
    stock = wrap(df)

    # 1. Moving Averages
    _ = stock["close_10_ema"]
    _ = stock["close_20_sma"]
    _ = stock["close_50_sma"]
    _ = stock["close_200_sma"]

    # 2. MACD
    _ = stock["macd"]   # DIF (12, 26)
    _ = stock["macds"]  # DEA (9)
    _ = stock["macdh"]  # Histogram

    # 3. RSI
    _ = stock["rsi_6"]
    _ = stock["rsi_14"]

    # 4. Bollinger Bands (20, 2)
    _ = stock["boll"]     # Middle (20 SMA)
    _ = stock["boll_ub"]  # Upper band
    _ = stock["boll_lb"]  # Lower band

    # 5. Volatility (ATR 14)
    _ = stock["atr_14"]

    # 6. VWMA 20
    _ = stock["vwma_20"]

    res_df = pd.DataFrame(stock)

    # Extract latest row metrics
    latest = res_df.iloc[-1]
    prev = res_df.iloc[-2] if len(res_df) > 1 else latest

    latest_date_str = pd.to_datetime(latest.get("Date", latest.get("date"))).strftime("%Y-%m-%d")
    close_val = float(latest.get("close", latest.get("Close")))
    open_val = float(latest.get("open", latest.get("Open")))
    high_val = float(latest.get("high", latest.get("High")))
    low_val = float(latest.get("low", latest.get("Low")))
    vol_val = float(latest.get("volume", latest.get("Volume", 0)))

    n_bars = len(res_df)

    ema10 = float(latest.get("close_10_ema", np.nan)) if n_bars >= 10 else np.nan
    sma20 = float(latest.get("close_20_sma", np.nan)) if n_bars >= 20 else np.nan
    sma50 = float(latest.get("close_50_sma", np.nan)) if n_bars >= 50 else np.nan
    sma200 = float(latest.get("close_200_sma", np.nan)) if n_bars >= 200 else np.nan

    macd_val = float(latest.get("macd", np.nan))
    macds_val = float(latest.get("macds", np.nan))
    macdh_val = float(latest.get("macdh", np.nan))
    prev_macdh = float(prev.get("macdh", np.nan))

    rsi6 = float(latest.get("rsi_6", np.nan))
    rsi14 = float(latest.get("rsi_14", np.nan))

    boll_mid = float(latest.get("boll", np.nan))
    boll_up = float(latest.get("boll_ub", np.nan))
    boll_low = float(latest.get("boll_lb", np.nan))

    atr14 = float(latest.get("atr_14", np.nan))
    vwma20 = float(latest.get("vwma_20", np.nan))

    # --- Trend Assessment ---
    trend_state = "Consolidating"
    trend_desc = "震荡整理"

    has_ema10 = not np.isnan(ema10)
    has_sma20 = not np.isnan(sma20)
    has_sma50 = not np.isnan(sma50)
    has_sma200 = not np.isnan(sma200)

    if has_ema10 and has_sma20 and has_sma50:
        if close_val > ema10 > sma20 > sma50:
            if has_sma200 and sma50 > sma200:
                trend_state = "Strong Bullish"
                trend_desc = "标准多头排列 (均线全顺向多头发散)"
            else:
                trend_state = "Bullish"
                trend_desc = "多头排列 (站上中短期均线顺向发散)"
        elif close_val > ema10 and ema10 > sma50 and sma20 <= sma50:
            trend_state = "Bullish Reversal"
            trend_desc = "修复型多头 (短期均线上穿突破，20日线金叉推进中)"
        elif close_val > ema10 and close_val > sma20:
            trend_state = "Bullish"
            trend_desc = "偏多头趋势 (站上短期中轴支撑)"
        elif close_val < ema10 < sma20 < sma50:
            if has_sma200 and sma50 < sma200:
                trend_state = "Strong Bearish"
                trend_desc = "极弱空头排列 (均线全空头发散)"
            else:
                trend_state = "Bearish"
                trend_desc = "空头排列 (受制于中短期均线顺向下行)"
        elif close_val < ema10 and ema10 < sma50 and sma20 >= sma50:
            trend_state = "Bearish Reversal"
            trend_desc = "破位型空头 (短期均线跌破，中短期死叉扩散中)"
        elif close_val < ema10 and close_val < sma20:
            trend_state = "Bearish"
            trend_desc = "偏空头趋势 (受制于短期均线压制)"
    elif has_ema10 and has_sma20:
        if close_val > ema10 > sma20:
            trend_state = "Bullish"
            trend_desc = "短期多头排列 (站上10/20日均线)"
        elif close_val < ema10 < sma20:
            trend_state = "Bearish"
            trend_desc = "短期空头排列 (跌破10/20日均线)"
        elif close_val > ema10:
            trend_state = "Bullish"
            trend_desc = "偏多头 (站上10日攻击线)"
        else:
            trend_state = "Bearish"
            trend_desc = "偏空头 (跌破10日攻击线)"

    # --- MACD Signal ---
    macd_signal_parts = []
    if macd_val > macds_val:
        if prev_macdh <= 0:
            macd_signal_parts.append("金叉形成 (Golden Cross)")
        else:
            macd_signal_parts.append("红柱动能运行中 (Bullish Momentum)")
    else:
        if prev_macdh >= 0:
            macd_signal_parts.append("死叉形成 (Death Cross)")
        else:
            macd_signal_parts.append("绿柱整理中 (Bearish Momentum)")

    prev_macds = float(prev.get("macds", np.nan))
    if macd_val > 0 and macds_val > 0:
        if not np.isnan(prev_macds) and prev_macds <= 0:
            macd_signal_parts.append("DEA慢线上穿零轴 (多头全面确立)")
        else:
            macd_signal_parts.append("零轴上方强势区")
    elif macd_val < 0 and macds_val < 0:
        macd_signal_parts.append("零轴下方弱势区")

    if macdh_val > 0 and macdh_val < prev_macdh:
        macd_signal_parts.append("红柱动能微幅收敛")
    elif macdh_val < 0 and macdh_val > prev_macdh:
        macd_signal_parts.append("绿柱动能微幅收缩")

    macd_signal = " / ".join(macd_signal_parts) if macd_signal_parts else "动能平衡"

    # --- RSI Signal (Dual-cycle RSI 6 & 14) ---
    if rsi6 >= 75 and rsi14 >= 70:
        rsi_state = f"极端双超买 (RSI6={rsi6:.1f}>75, RSI14={rsi14:.1f}>70, 严防冲高回落)"
    elif rsi6 >= 75:
        rsi_state = f"短线动能超买 (RSI6={rsi6:.1f}>75, 警惕分时冲高回落与乖离修复)"
    elif rsi6 <= 25 and rsi14 <= 30:
        rsi_state = f"极端双超卖 (RSI6={rsi6:.1f}<25, RSI14={rsi14:.1f}<30, 关注超跌反弹)"
    elif rsi6 <= 25:
        rsi_state = f"短线超跌探底 (RSI6={rsi6:.1f}<25, 关注止跌反弹)"
    elif rsi14 >= 60:
        rsi_state = f"强势多头区间 (RSI14={rsi14:.1f})"
    elif rsi14 <= 40:
        rsi_state = f"弱势探底区间 (RSI14={rsi14:.1f})"
    else:
        rsi_state = f"中性平衡区间 (RSI14={rsi14:.1f})"

    # --- Bollinger Position ---
    boll_width = (boll_up - boll_low) / boll_mid * 100 if boll_mid > 0 else 0
    if close_val >= boll_up:
        boll_pos = "触及或突破上轨 (压力区/高波动)"
    elif close_val <= boll_low:
        boll_pos = "触及或跌破下轨 (支撑区/超跌)"
    elif close_val >= boll_mid:
        boll_pos = "运行于中轨与上轨之间 (偏强通道)"
    else:
        boll_pos = "运行于中轨与下轨之间 (偏弱通道)"

    # --- Support & Resistance Calculations with Explicit Provenance ---
    recent_window = min(n_bars, 60)
    recent_sub = res_df.tail(recent_window)
    high_col = "high" if "high" in recent_sub.columns else "High"
    low_col = "low" if "low" in recent_sub.columns else "Low"
    swing_high_60 = float(recent_sub[high_col].max()) if not recent_sub.empty else np.nan
    swing_low_60 = float(recent_sub[low_col].min()) if not recent_sub.empty else np.nan

    raw_resistances = []
    if not np.isnan(boll_up):
        raw_resistances.append({"price": round(boll_up, 2), "source": "布林线上轨 (Bollinger Upper Band)"})
    if not np.isnan(atr14):
        raw_resistances.append({"price": round(close_val + 2 * atr14, 2), "source": "Close + 2*ATR (动态波动极值/止盈参考)"})
    if not np.isnan(swing_high_60):
        raw_resistances.append({"price": round(swing_high_60, 2), "source": f"{recent_window}日历史最高点 (Swing High/套牢密集区)"})

    raw_supports = []
    if has_ema10:
        raw_supports.append({"price": round(ema10, 2), "source": "10 EMA (短期攻击线支撑)"})
    if not np.isnan(atr14):
        raw_supports.append({"price": round(close_val - 2 * atr14, 2), "source": "Close - 2*ATR (动态跟踪止损线)"})
    if has_sma50:
        raw_supports.append({"price": round(sma50, 2), "source": "50 SMA (中期牛熊生命线)"})
    if has_sma20:
        raw_supports.append({"price": round(sma20, 2), "source": "20 SMA / 布林中轨"})
    if not np.isnan(swing_low_60):
        raw_supports.append({"price": round(swing_low_60, 2), "source": f"{recent_window}日历史最低点 (Swing Low)"})

    # Filter resistance > close_val and support < close_val
    valid_res = [r for r in raw_resistances if r["price"] > close_val]
    valid_res.sort(key=lambda x: x["price"])
    dedup_res = []
    seen_res_prices = set()
    for r in valid_res:
        if r["price"] not in seen_res_prices:
            dedup_res.append(r)
            seen_res_prices.add(r["price"])

    valid_sup = [s for s in raw_supports if s["price"] < close_val]
    valid_sup.sort(key=lambda x: x["price"], reverse=True)
    merged_sup = []
    skip_next = False
    for i in range(len(valid_sup)):
        if skip_next:
            skip_next = False
            continue
        cur = valid_sup[i]
        if i + 1 < len(valid_sup):
            nxt = valid_sup[i + 1]
            diff_pct = abs(cur["price"] - nxt["price"]) / cur["price"] * 100
            if diff_pct <= 0.8:
                merged_sup.append({
                    "price": cur["price"],
                    "source": f"{cur['source']} 与 {nxt['source']} [双重共振强支撑, 约 {cur['price']}~{nxt['price']}]"
                })
                skip_next = True
                continue
        merged_sup.append(cur)

    dedup_sup = []
    seen_sup_prices = set()
    for s in merged_sup:
        if s["price"] not in seen_sup_prices:
            dedup_sup.append(s)
            seen_sup_prices.add(s["price"])

    resistance_levels = [r["price"] for r in dedup_res[:3]]
    support_levels = [s["price"] for s in dedup_sup[:3]]

    summary = {
        "date": latest_date_str,
        "price": {
            "open": round(open_val, 2),
            "close": round(close_val, 2),
            "high": round(high_val, 2),
            "low": round(low_val, 2),
            "volume": int(vol_val),
        },
        "moving_averages": {
            "ema10": round(ema10, 2) if not np.isnan(ema10) else None,
            "sma20": round(sma20, 2) if not np.isnan(sma20) else None,
            "sma50": round(sma50, 2) if not np.isnan(sma50) else None,
            "sma200": round(sma200, 2) if not np.isnan(sma200) else None,
        },
        "macd": {
            "dif": round(macd_val, 3),
            "dea": round(macds_val, 3),
            "hist": round(macdh_val, 3),
            "signal": macd_signal,
        },
        "rsi": {
            "rsi6": round(rsi6, 2),
            "rsi14": round(rsi14, 2),
            "state": rsi_state,
        },
        "bollinger": {
            "mid": round(boll_mid, 2),
            "upper": round(boll_up, 2),
            "lower": round(boll_low, 2),
            "bandwidth_pct": round(boll_width, 2),
            "position": boll_pos,
        },
        "volatility": {
            "atr14": round(atr14, 2),
            "atr_pct": round((atr14 / close_val) * 100, 2) if close_val > 0 else None,
            "vwma20": round(vwma20, 2) if not np.isnan(vwma20) else None,
        },
        "trend": {
            "state": trend_state,
            "desc": trend_desc,
        },
        "key_levels": {
            "resistance_levels": resistance_levels,
            "support_levels": support_levels,
            "resistance_details": dedup_res[:3],
            "support_details": dedup_sup[:3],
            "stop_loss_suggested_2atr": round(close_val - 2 * atr14, 2),
        }
    }

    return res_df, summary
