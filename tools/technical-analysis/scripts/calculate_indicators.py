from typing import Any

import numpy as np
import pandas as pd
from stockstats import wrap


def compute_volume_profile(df: pd.DataFrame, n_bars: int = 90, n_bins: int = 25) -> dict[str, Any]:
    """Compute volume distribution by price (Volume Profile / VPVR) over the recent window."""
    vp_window = min(len(df), n_bars)
    df_vp = df.tail(vp_window)
    if df_vp.empty:
        return {}

    low_col = "low" if "low" in df_vp.columns else "Low"
    high_col = "high" if "high" in df_vp.columns else "High"
    vol_col = "volume" if "volume" in df_vp.columns else "Volume"
    close_col = "close" if "close" in df_vp.columns else "Close"

    p_min = float(df_vp[low_col].min())
    p_max = float(df_vp[high_col].max())
    if p_max <= p_min or np.isnan(p_min) or np.isnan(p_max):
        return {}

    bins = np.linspace(p_min, p_max, n_bins + 1)
    bin_volumes = np.zeros(n_bins)
    total_vol = 0.0

    for _, row in df_vp.iterrows():
        r_low = float(row[low_col])
        r_high = float(row[high_col])
        r_vol = float(row[vol_col])
        total_vol += r_vol
        if r_high == r_low:
            idx = int(np.clip(np.digitize([r_low], bins)[0] - 1, 0, n_bins - 1))
            bin_volumes[idx] += r_vol
        else:
            for b_i in range(n_bins):
                b_low = bins[b_i]
                b_high = bins[b_i + 1]
                overlap = max(0.0, min(r_high, b_high) - max(r_low, b_low))
                if overlap > 0:
                    bin_volumes[b_i] += r_vol * (overlap / (r_high - r_low))

    if total_vol <= 0:
        return {}

    latest_close = float(df_vp[close_col].iloc[-1])

    # 1. POC (Point of Control)
    poc_idx = int(np.argmax(bin_volumes))
    poc_range = (round(float(bins[poc_idx]), 2), round(float(bins[poc_idx + 1]), 2))
    poc_mid = round((poc_range[0] + poc_range[1]) / 2, 2)
    poc_pct = round((bin_volumes[poc_idx] / total_vol) * 100, 1)

    # 2. Overhead Supply Peak (above latest_close)
    above_indices = [i for i in range(n_bins) if bins[i] >= latest_close]
    overhead_peak = None
    overhead_total_pct = round(sum(bin_volumes[i] for i in above_indices) / total_vol * 100, 1) if above_indices else 0.0
    if above_indices:
        max_above_idx = max(above_indices, key=lambda i: bin_volumes[i])
        r_low = round(float(bins[max_above_idx]), 2)
        r_high = round(float(bins[max_above_idx + 1]), 2)
        overhead_peak = {
            "range": f"{r_low:.2f} ~ {r_high:.2f}",
            "mid_price": round((r_low + r_high) / 2, 2),
            "vol_pct": round(float(bin_volumes[max_above_idx]) / total_vol * 100, 1),
        }

    # 3. Support Shelf Peak (below latest_close)
    below_indices = [i for i in range(n_bins) if bins[i + 1] <= latest_close]
    support_peak = None
    support_total_pct = round(sum(bin_volumes[i] for i in below_indices) / total_vol * 100, 1) if below_indices else 0.0
    if below_indices:
        max_below_idx = max(below_indices, key=lambda i: bin_volumes[i])
        s_low = round(float(bins[max_below_idx]), 2)
        s_high = round(float(bins[max_below_idx + 1]), 2)
        support_peak = {
            "range": f"{s_low:.2f} ~ {s_high:.2f}",
            "mid_price": round((s_low + s_high) / 2, 2),
            "vol_pct": round(float(bin_volumes[max_below_idx]) / total_vol * 100, 1),
        }

    return {
        "window_bars": vp_window,
        "poc": {
            "range": f"{poc_range[0]:.2f} ~ {poc_range[1]:.2f}",
            "mid_price": poc_mid,
            "vol_pct": poc_pct,
        },
        "overhead_supply": {
            "total_trapped_vol_pct": overhead_total_pct,
            "peak_cluster": overhead_peak,
        },
        "support_shelf": {
            "total_support_vol_pct": support_total_pct,
            "peak_cluster": support_peak,
        },
    }


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

    # Calculate Volume Profile (筹码分布)
    vp_data = compute_volume_profile(res_df, n_bars=90, n_bins=25)

    raw_resistances = []
    if not np.isnan(boll_up):
        raw_resistances.append({"price": round(boll_up, 2), "source": "布林线上轨 (Bollinger Upper Band)"})
    if not np.isnan(atr14):
        raw_resistances.append({"price": round(close_val + 2 * atr14, 2), "source": "Close + 2*ATR (动态波动极值/止盈参考)"})
    if vp_data and vp_data.get("overhead_supply", {}).get("peak_cluster"):
        ov_peak = vp_data["overhead_supply"]["peak_cluster"]
        raw_resistances.append({
            "price": ov_peak["mid_price"],
            "source": f"高位套牢筹码密集区 (Volume Shelf {ov_peak['range']}, 占近90日成交量 {ov_peak['vol_pct']}%)"
        })
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
    if vp_data and vp_data.get("support_shelf", {}).get("peak_cluster"):
        sp_peak = vp_data["support_shelf"]["peak_cluster"]
        raw_supports.append({
            "price": sp_peak["mid_price"],
            "source": f"主要筹码支撑峰 (Volume Shelf {sp_peak['range']}, 占近90日成交量 {sp_peak['vol_pct']}%)"
        })
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

    # 7. Volume Dynamics & VMA
    vol_col_name = "volume" if "volume" in res_df.columns else "Volume"
    vma5_series = res_df[vol_col_name].rolling(5).mean()
    vma20_series = res_df[vol_col_name].rolling(20).mean()

    vma5_val = float(vma5_series.iloc[-1]) if len(vma5_series) >= 5 and not np.isnan(vma5_series.iloc[-1]) else vol_val
    vma20_val = float(vma20_series.iloc[-1]) if len(vma20_series) >= 20 and not np.isnan(vma20_series.iloc[-1]) else vol_val

    vol_ratio_5 = round(vol_val / vma5_val, 2) if vma5_val > 0 else 1.0
    vol_ratio_20 = round(vol_val / vma20_val, 2) if vma20_val > 0 else 1.0

    prev_close_val = float(prev.get("close", prev.get("Close")))
    price_change_pct = ((close_val - prev_close_val) / prev_close_val * 100) if prev_close_val > 0 else 0.0

    if price_change_pct >= 2.0:
        if vol_ratio_5 >= 1.2 or vol_ratio_20 >= 1.2:
            vp_desc = f"放量拉升 (+{price_change_pct:.2f}%, 量比={vol_ratio_5} > 1.2, 多头资金主动进攻)"
            vp_state = "Volume Breakout"
        else:
            vp_desc = f"缩量推升 / 量价顶背离 (+{price_change_pct:.2f}%, 量比={vol_ratio_5} < 1.0, 呈缩量推升特征，谨防冲高回落)"
            vp_state = "Volume Divergence"
    elif price_change_pct <= -2.0:
        if vol_ratio_5 >= 1.2 or vol_ratio_20 >= 1.2:
            vp_desc = f"放量下挫 ({price_change_pct:.2f}%, 量比={vol_ratio_5} > 1.2, 空头抛压沉重)"
            vp_state = "Volume Selloff"
        else:
            vp_desc = f"缩量回调 ({price_change_pct:.2f}%, 量比={vol_ratio_5} < 1.0, 属缩量良性洗盘)"
            vp_state = "Low Volume Pullback"
    else:
        if vol_ratio_5 < 0.7:
            vp_desc = f"极致地量整理 (量比={vol_ratio_5} < 0.7, 市场观望情绪浓厚，等待方向选择)"
            vp_state = "Extremely Low Volume"
        else:
            vp_desc = f"温和震荡换手 (量比={vol_ratio_5}, 量价相对平稳)"
            vp_state = "Normal Volume Consolidation"

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
        "volume_dynamics": {
            "vma5": round(vma5_val, 2),
            "vma20": round(vma20_val, 2),
            "vol_ratio_5": vol_ratio_5,
            "vol_ratio_20": vol_ratio_20,
            "state": vp_state,
            "desc": vp_desc,
        },
        "volume_profile": vp_data,
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
