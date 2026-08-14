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

    ema10 = float(latest.get("close_10_ema", np.nan))
    sma20 = float(latest.get("close_20_sma", np.nan))
    sma50 = float(latest.get("close_50_sma", np.nan))
    sma200 = float(latest.get("close_200_sma", np.nan))

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

    if close_val > ema10 > sma50:
        if not np.isnan(sma200) and sma50 > sma200:
            trend_state = "Strong Bullish"
            trend_desc = "强势多头排列 (均线全多头发散)"
        else:
            trend_state = "Bullish"
            trend_desc = "偏多头趋势 (站上短期与中期均线)"
    elif close_val < ema10 < sma50:
        if not np.isnan(sma200) and sma50 < sma200:
            trend_state = "Strong Bearish"
            trend_desc = "极弱空头排列 (全均线破位)"
        else:
            trend_state = "Bearish"
            trend_desc = "偏空头趋势 (受制于中短期均线)"

    # --- MACD Signal ---
    if macd_val > macds_val and macdh_val > 0:
        if prev_macdh <= 0:
            macd_signal = "零轴上/下金叉 (Golden Cross)"
        else:
            macd_signal = "红柱动能运行中 (Bullish Momentum)"
    else:
        if prev_macdh >= 0:
            macd_signal = "死叉形成 (Death Cross)"
        else:
            macd_signal = "绿柱整理中 (Bearish Momentum)"

    # --- RSI Signal ---
    if rsi14 >= 75:
        rsi_state = "严重超买 (>75, 警惕冲高回落)"
    elif rsi14 >= 60:
        rsi_state = "强势多头区间 (60-75)"
    elif rsi14 <= 25:
        rsi_state = "严重超卖 (<25, 关注止跌反弹)"
    elif rsi14 <= 40:
        rsi_state = "弱势探底区间 (25-40)"
    else:
        rsi_state = "中性平衡区间 (40-60)"

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

    # --- Support & Resistance Calculations ---
    recent_60 = res_df.tail(60)
    high_col = "high" if "high" in recent_60.columns else "High"
    low_col = "low" if "low" in recent_60.columns else "Low"
    swing_high_60 = float(recent_60[high_col].max())
    swing_low_60 = float(recent_60[low_col].min())

    resistance_levels = sorted({
        round(v, 2) for v in [swing_high_60, boll_up, close_val + 2 * atr14] if v > close_val
    })
    support_levels = sorted({
        round(v, 2) for v in [swing_low_60, boll_low, sma50, close_val - 2 * atr14] if v < close_val
    }, reverse=True)

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
            "resistance_levels": resistance_levels[:3],
            "support_levels": support_levels[:3],
            "stop_loss_suggested_2atr": round(close_val - 2 * atr14, 2),
        }
    }

    return res_df, summary
