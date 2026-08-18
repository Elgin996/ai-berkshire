"""Ticker normalization and OHLCV cache freshness — stdlib only."""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Optional

CACHE_TTL_SECONDS = 900  # 15 minutes for live intraday data


def hk_codes(digits: str) -> tuple[str, str]:
    """Return (canonical/yahoo code like 0700.HK, tencent code like hk00700)."""
    core = digits.lstrip("0") or "0"
    yahoo = f"{core.zfill(4)}.HK"
    tencent = f"hk{core.zfill(5)}"
    return yahoo, tencent


def cache_is_usable(
    as_of: date,
    today: date,
    cache_mtime: float,
    max_cached_date: Optional[date],
    now_ts: Optional[float] = None,
    ttl_seconds: int = CACHE_TTL_SECONDS,
) -> bool:
    """Whether an on-disk OHLCV CSV can be used for as_of.

    Today / future: require TTL. Historical: require bars covering as_of and
    a file written on a later calendar day (so yesterday's session is complete).
    """
    if max_cached_date is None:
        return False
    if as_of >= today:
        import time
        ts = time.time() if now_ts is None else now_ts
        return (ts - cache_mtime) < ttl_seconds
    written = datetime.fromtimestamp(cache_mtime).date()
    return max_cached_date >= as_of and written > as_of


def normalize_symbol_info(raw: str) -> dict[str, Any]:
    """Parse symbol into asset class, canonical code, and vendor-specific tickers.

    Supported formats:
      - A-Shares: 600519.SS, 000001.SZ, 300394.SZ, 688012.SH, 835185.BJ, sh600519, 600519
      - HK Stocks: 0700.HK, 9988.HK, 3690.HK, hk00700, 00700, 0700
      - A-Share ETFs: 510300, 159915, 588000, 563360, sh510300
      - US / Global: NVDA, AAPL, MSFT, BTC-USD
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Symbol must be a non-empty string")

    s = raw.strip()
    upper_s = s.upper()
    lower_s = s.lower()

    def _cn_yahoo(prefix: str, code: str) -> str:
        if prefix == "sh":
            return f"{code}.SS"
        if prefix == "bj":
            return f"{code}.BJ"
        return f"{code}.SZ"

    def _cn_canonical(prefix: str, code: str) -> str:
        if prefix == "sh":
            return f"{code}.SS"
        return f"{code}.{prefix.upper()}"

    # 1. Hong Kong Stocks
    if upper_s.endswith(".HK") or (lower_s.startswith("hk") and lower_s[2:].isdigit()):
        digits = re.sub(r"\D", "", upper_s)
        canonical, tx_code = hk_codes(digits)
        return {
            "raw": raw,
            "market": "HK",
            "is_etf": False,
            "canonical": canonical,
            "tencent_symbol": tx_code,
            "yahoo_symbol": canonical,
        }

    # 2. A-Shares and A-Share ETFs
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
            "canonical": _cn_canonical(tx_prefix, code_part),
            "tencent_symbol": tx_code,
            "yahoo_symbol": _cn_yahoo(tx_prefix, code_part),
        }

    if lower_s.startswith(("sh", "sz", "bj")) and lower_s[2:].isdigit():
        prefix = lower_s[:2]
        digits = lower_s[2:]
        is_etf = digits.startswith(("51", "56", "58", "15", "16"))
        return {
            "raw": raw,
            "market": "CN",
            "is_etf": is_etf,
            "canonical": _cn_canonical(prefix, digits),
            "tencent_symbol": lower_s,
            "yahoo_symbol": _cn_yahoo(prefix, digits),
        }

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
            "canonical": _cn_canonical(prefix, s),
            "tencent_symbol": f"{prefix}{s}",
            "yahoo_symbol": _cn_yahoo(prefix, s),
        }

    # Pure 4- or 5-digit number: HK (A-shares are 6 digits)
    if s.isdigit() and 4 <= len(s) <= 5:
        canonical, tx_code = hk_codes(s)
        return {
            "raw": raw,
            "market": "HK",
            "is_etf": False,
            "canonical": canonical,
            "tencent_symbol": tx_code,
            "yahoo_symbol": canonical,
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
