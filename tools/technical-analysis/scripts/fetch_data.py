import logging
import os
from typing import Any

from symbols import cache_is_usable, normalize_symbol_info

logger = logging.getLogger(__name__)

TENCENT_HTTP_TIMEOUT = 8


def get_cache_dir() -> str:
    """Return local cache directory for storing OHLCV data."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cache_dir = os.path.join(base_dir, ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def fetch_tencent_kline(tx_symbol: str, count: int = 640):
    """Fetch front-rehabilitated (QFQ) daily OHLCV from Tencent Finance HTTP API."""
    import pandas as pd
    import requests

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
    import requests

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

    if len(parts) >= 80:
        try:
            result["shares_outstanding"] = float(parts[72]) if parts[72] else None
            result["total_shares"] = float(parts[73]) if parts[73] else None
            result["discount_rate_pct"] = float(parts[77]) if parts[77] else None
            result["iopv"] = float(parts[78]) if parts[78] else None
        except (ValueError, IndexError):
            pass

    return result


def fetch_yfinance_kline(yf_symbol: str, count_years: int = 3):
    """Fallback fetcher using yfinance for US / global stocks."""
    import pandas as pd
    try:
        import yfinance as yf
        df = yf.download(yf_symbol, period=f"{count_years}y", progress=False, auto_adjust=True)
        if df.empty:
            raise ValueError(f"yfinance returned empty data for {yf_symbol}")
        df = df.reset_index()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.rename(columns={"index": "Date", "Datetime": "Date"})
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
        df = df.dropna(subset=["Date", "Close"]).sort_values("Date").reset_index(drop=True)
        return df[["Date", "Open", "High", "Low", "Close", "Volume"]]
    except ImportError:
        raise RuntimeError("yfinance is required for US / global asset downloads")


def get_ohlcv_data(symbol: str, as_of_date: str | None = None):
    """Universal OHLCV fetcher with local disk caching and anti-lookahead filtering.

    Returns:
      (DataFrame with columns ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'], symbol_info dict)
    """
    import pandas as pd

    sym_info = normalize_symbol_info(symbol)
    cache_dir = get_cache_dir()
    cache_file = os.path.join(cache_dir, f"{sym_info['tencent_symbol']}_kline.csv")

    curr_dt = pd.to_datetime(as_of_date) if as_of_date else pd.Timestamp.today()
    today_dt = pd.Timestamp.today()

    df = None
    if os.path.exists(cache_file):
        try:
            cached = pd.read_csv(cache_file, parse_dates=["Date"])
            max_cached = None
            if not cached.empty and "Date" in cached.columns:
                max_cached = pd.to_datetime(cached["Date"]).max().date()
            if (
                not cached.empty
                and "Close" in cached.columns
                and cache_is_usable(
                    curr_dt.date(),
                    today_dt.date(),
                    os.path.getmtime(cache_file),
                    max_cached,
                )
            ):
                df = cached
        except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError) as e:
            logger.debug("Failed to read cache %s: %s", cache_file, e)

    if df is None:
        if sym_info["market"] in ("CN", "HK"):
            df = fetch_tencent_kline(sym_info["tencent_symbol"])
        else:
            df = fetch_yfinance_kline(sym_info["yahoo_symbol"])
        df.to_csv(cache_file, index=False)

    df = df[df["Date"] <= curr_dt].reset_index(drop=True)
    if df.empty:
        raise ValueError(f"No OHLCV records found on or before {as_of_date or 'today'}")

    return df, sym_info
