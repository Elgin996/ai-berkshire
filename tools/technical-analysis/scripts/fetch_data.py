import logging
import os
import re
import time
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

TENCENT_HTTP_TIMEOUT = 8
CACHE_TTL_SECONDS = 900  # 15 minutes for live intraday data


def get_cache_dir() -> str:
    """Return local cache directory for storing OHLCV data."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_dir = os.path.join(base_dir, ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def normalize_symbol_info(raw: str) -> dict[str, Any]:
    """Parse symbol into asset class, canonical code, and vendor-specific tickers.

    Supported formats:
      - A-Shares: 600519.SS, 000001.SZ, 300394.SZ, 688012.SH, 835185.BJ, sh600519, 600519
      - HK Stocks: 0700.HK, 9988.HK, 3690.HK, hk00700, 00700
      - A-Share ETFs: 510300, 159915, 588000, 563360, sh510300
      - US / Global: NVDA, AAPL, MSFT, BTC-USD
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Symbol must be a non-empty string")

    s = raw.strip()
    upper_s = s.upper()
    lower_s = s.lower()

    # 1. Hong Kong Stocks
    if upper_s.endswith(".HK") or (lower_s.startswith("hk") and lower_s[2:].isdigit()):
        digits = re.sub(r"\D", "", upper_s)
        tx_code = f"hk{digits.zfill(5)}"
        return {
            "raw": raw,
            "market": "HK",
            "is_etf": False,
            "canonical": f"{digits.zfill(4)}.HK",
            "tencent_symbol": tx_code,
            "yahoo_symbol": f"{digits.zfill(4)}.HK",
        }

    # 2. A-Shares and A-Share ETFs
    # Check suffixes
    if upper_s.endswith((".SS", ".SH", ".SZ", ".BJ")):
        code_part = upper_s[:-3]
        suffix = upper_s[-2:]
        if suffix in ("SS", "SH"):
            tx_prefix = "sh"
        elif suffix == "SZ":
            tx_prefix = "sz"
        else:
            tx_prefix = "bj"
        tx_code = f"{tx_prefix}{code_part}"
        is_etf = code_part.startswith(("51", "56", "58", "15", "16"))
        return {
            "raw": raw,
            "market": "CN",
            "is_etf": is_etf,
            "canonical": f"{code_part}.{ 'SS' if tx_prefix == 'sh' else tx_prefix.upper() }",
            "tencent_symbol": tx_code,
            "yahoo_symbol": f"{code_part}.{ 'SS' if tx_prefix == 'sh' else 'SZ' }",
        }

    # Check prefixes (sh/sz/bj)
    if lower_s.startswith(("sh", "sz", "bj")) and lower_s[2:].isdigit():
        prefix = lower_s[:2]
        digits = lower_s[2:]
        is_etf = digits.startswith(("51", "56", "58", "15", "16"))
        return {
            "raw": raw,
            "market": "CN",
            "is_etf": is_etf,
            "canonical": f"{digits}.{'SS' if prefix == 'sh' else prefix.upper()}",
            "tencent_symbol": lower_s,
            "yahoo_symbol": f"{digits}.{'SS' if prefix == 'sh' else 'SZ'}",
        }

    # Pure 6-digit number (A-shares)
    if len(s) == 6 and s.isdigit():
        if s.startswith(("60", "68", "90", "51", "56", "58")):
            prefix = "sh"
        elif s.startswith(("00", "30", "20", "15", "16", "39")):
            prefix = "sz"
        elif s.startswith(("8", "4", "92")):
            prefix = "bj"
        else:
            prefix = "sh"
        is_etf = s.startswith(("51", "56", "58", "15", "16"))
        return {
            "raw": raw,
            "market": "CN",
            "is_etf": is_etf,
            "canonical": f"{s}.{'SS' if prefix == 'sh' else prefix.upper()}",
            "tencent_symbol": f"{prefix}{s}",
            "yahoo_symbol": f"{s}.{'SS' if prefix == 'sh' else 'SZ'}",
        }

    # Pure 5-digit number (HK stock)
    if len(s) == 5 and s.isdigit() and not s.startswith(("60", "68", "00", "30")):
        return {
            "raw": raw,
            "market": "HK",
            "is_etf": False,
            "canonical": f"{s.zfill(4)}.HK",
            "tencent_symbol": f"hk{s}",
            "yahoo_symbol": f"{s.zfill(4)}.HK",
        }

    # 3. US / Global Assets
    return {
        "raw": raw,
        "market": "US_GLOBAL",
        "is_etf": False,
        "canonical": upper_s,
        "tencent_symbol": lower_s,
        "yahoo_symbol": upper_s,
    }


def fetch_tencent_kline(tx_symbol: str, count: int = 640) -> pd.DataFrame:
    """Fetch front-rehabilitated (QFQ) daily OHLCV from Tencent Finance HTTP API."""
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tx_symbol},day,,,{count},qfq"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://gu.qq.com/",
    }
    resp = requests.get(url, headers=headers, timeout=TENCENT_HTTP_TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"Tencent HTTP Error {resp.status_code}")

    res_json = resp.json()
    if not res_json or "data" not in res_json or tx_symbol not in res_json["data"]:
        raise ValueError(f"No data returned from Tencent Finance for {tx_symbol}")

    node = res_json["data"][tx_symbol]
    raw_bars = node.get("qfqday", node.get("day", []))
    if not raw_bars:
        raise ValueError(f"No K-line bars found for {tx_symbol}")

    rows = []
    for b in raw_bars:
        if len(b) >= 6:
            rows.append({
                "Date": b[0],
                "Open": float(b[1]),
                "Close": float(b[2]),
                "High": float(b[3]),
                "Low": float(b[4]),
                "Volume": float(b[5]),
            })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)
    return df


def fetch_tencent_quote(tx_symbol: str) -> dict[str, Any]:
    """Fetch real-time quote snapshot from Tencent (including ETF IOPV, discount rate, shares)."""
    url = f"https://qt.gtimg.cn/q={tx_symbol}"
    resp = requests.get(url, timeout=TENCENT_HTTP_TIMEOUT)
    text = resp.text.strip()
    if "=" not in text or "~" not in text:
        return {}

    payload = text.split("=")[1].strip('" ;')
    parts = payload.split("~")
    if len(parts) < 30:
        return {}

    vol_raw = float(parts[6]) if parts[6] else None
    result = {
        "name": parts[1],
        "code": parts[2],
        "current_price": float(parts[3]) if parts[3] else None,
        "last_close": float(parts[4]) if parts[4] else None,
        "open_price": float(parts[5]) if parts[5] else None,
        "volume_shares": vol_raw,
        "volume_lots": (vol_raw / 100) if vol_raw is not None else None,
        "change_amount": float(parts[31]) if len(parts) > 31 and parts[31] else None,
        "change_pct": float(parts[32]) if len(parts) > 32 and parts[32] else None,
        "high_price": float(parts[33]) if len(parts) > 33 and parts[33] else None,
        "low_price": float(parts[34]) if len(parts) > 34 and parts[34] else None,
        "turnover_amount_wanyuan": (float(parts[37]) / 10000.0 if tx_symbol.startswith("hk") else float(parts[37])) if len(parts) > 37 and parts[37] else None,
        "turnover_rate": float(parts[38]) if len(parts) > 38 and parts[38] else None,
    }

    if len(parts) >= 46:
        try:
            result["market_cap_circ_yi"] = float(parts[44]) if parts[44] else None
            result["market_cap_total_yi"] = float(parts[45]) if parts[45] else None
        except (ValueError, IndexError):
            pass

    # Extended ETF and shares fields if available
    if len(parts) >= 80:
        try:
            result["shares_outstanding"] = float(parts[72]) if parts[72] else None
            result["total_shares"] = float(parts[73]) if parts[73] else None
            result["discount_rate_pct"] = float(parts[77]) if parts[77] else None
            result["iopv"] = float(parts[78]) if parts[78] else None
        except (ValueError, IndexError):
            pass

    return result


def fetch_yfinance_kline(yf_symbol: str, count_years: int = 3) -> pd.DataFrame:
    """Fallback fetcher using yfinance for US / global stocks."""
    try:
        import yfinance as yf
        df = yf.download(yf_symbol, period=f"{count_years}y", progress=False, auto_adjust=True)
        if df.empty:
            raise ValueError(f"yfinance returned empty data for {yf_symbol}")
        df = df.reset_index()
        # Clean column names
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.rename(columns={"index": "Date", "Datetime": "Date"})
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        df = df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)
        return df[["Date", "Open", "High", "Low", "Close", "Volume"]]
    except ImportError:
        raise RuntimeError("yfinance is required for US / global asset downloads")


def get_ohlcv_data(symbol: str, as_of_date: str | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Universal OHLCV fetcher with local disk caching and anti-lookahead filtering.

    Returns:
      (DataFrame with columns ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'], symbol_info dict)
    """
    sym_info = normalize_symbol_info(symbol)
    cache_dir = get_cache_dir()
    cache_file = os.path.join(cache_dir, f"{sym_info['tencent_symbol']}_kline.csv")

    curr_dt = pd.to_datetime(as_of_date) if as_of_date else pd.Timestamp.today()
    today_dt = pd.Timestamp.today()

    df = None
    if os.path.exists(cache_file):
        try:
            cached = pd.read_csv(cache_file, parse_dates=["Date"])
            # Cache is fresh if historical or less than TTL
            is_same_day = curr_dt.date() >= today_dt.date()
            if not cached.empty and "Close" in cached.columns and (not is_same_day or (time.time() - os.path.getmtime(cache_file) < CACHE_TTL_SECONDS)):
                df = cached
        except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError) as e:
            logger.debug("Failed to read cache %s: %s", cache_file, e)

    if df is None:
        if sym_info["market"] in ("CN", "HK"):
            df = fetch_tencent_kline(sym_info["tencent_symbol"])
        else:
            df = fetch_yfinance_kline(sym_info["yahoo_symbol"])
        df.to_csv(cache_file, index=False)

    # Filter to as_of_date to eliminate look-ahead bias
    df = df[df["Date"] <= curr_dt].reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No OHLCV records found on or before {as_of_date or 'today'}")

    return df, sym_info
