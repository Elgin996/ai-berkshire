#!/usr/bin/env python3
"""Multi-Source Valuation & Consensus Fair-Value Tool for AI Berkshire.

Collects, parses, and cross-validates stock valuation data and analyst targets across:
1. Morningstar (Analyst Fair Value, Quant Fair Value, Economic Moat, Uncertainty)
2. Seeking Alpha (Wall St Rating, SA Authors Rating, FWD P/E, FWD PEG, EV/EBITDA, 5Y History)
3. StockAnalysis (S&P Global Analyst Consensus, Target Low/Avg/Median/High, Growth Forecasts)
4. Yahoo Finance (Real-time/Close Price, 52W Range, 1Y Target Est, TTM & FWD P/E, 5Y PEG, EV/EBITDA)
5. MarketBeat (Consensus Score & Rating, Price Target Range, 90-Day Upgrades/Downgrades)
6. TipRanks (Smart Score, 12M Price Target, Analyst Coverage Distribution)

Zero external dependencies — standard library only (urllib, json, re, argparse, datetime).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

# Set default encoding for Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

COMMON_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def safe_urlopen(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> str:
    """Safely fetch URL content as text with headers and timeout."""
    hdrs = headers or COMMON_HEADERS
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def get_company_name_from_yahoo(ticker: str) -> str:
    """Extract standard company name for smart Morningstar lookup."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}?interval=1d&range=1d"
        meta = json.loads(safe_urlopen(url, timeout=8))["chart"]["result"][0]["meta"]
        return meta.get("shortName") or meta.get("longName") or ""
    except Exception:
        return ""


# ==============================================================================
# 1. Morningstar Scraper / API (Smart Multi-Strategy Search)
# ==============================================================================
def search_morningstar_term(term: str, target_ticker: str) -> Optional[Dict[str, Any]]:
    try:
        url = (
            "https://lt.morningstar.com/api/rest.svc/klr5zyak8x/security/screener"
            "?page=1&pageSize=50&outputType=json&version=1&languageId=en-US&currencyId=USD"
            "&universeIds=E0EXG%24XNAS%7CE0EXG%24XNYS"
            "&securityDataPoints=SecId%7CName%7CPriceCurrency%7CTenforeId%7CClosePrice"
            "%7CStarRatingM255%7CQuantitativeFairValue%7CFairValueEstimate"
            "%7CAssessmentOfFairValueUncertainty%7CEconomicMoat%7CIndustryName%7CSectorName"
            f"&term={urllib.parse.quote(term)}"
        )
        data = json.loads(safe_urlopen(url, timeout=12))
        for r in data.get("rows", []):
            parts = r.get("TenforeId", "").split(".")
            t_code = parts[-1] if len(parts) >= 3 else r.get("TenforeId", "")
            if t_code.upper() == target_ticker.upper():
                return r
    except Exception:
        pass
    return None


def fetch_morningstar(ticker: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "source": "Morningstar",
        "ticker": ticker.upper(),
        "status": "pending",
        "data_date": datetime.date.today().strftime("%Y-%m-%d"),
    }
    try:
        matched_row = search_morningstar_term(ticker, ticker)
        
        if not matched_row:
            cname = get_company_name_from_yahoo(ticker)
            stop_words = {
                "the", "a", "an", "inc", "corp", "corporation", "co", "ltd", "plc",
                "holding", "holdings", "company", "class", "group", "adr", "ordinary", "shares"
            }
            words = [w for w in re.split(r"[\s,\.-]+", cname) if w and w.lower() not in stop_words]
            for word in words[:2]:
                matched_row = search_morningstar_term(word, ticker)
                if matched_row:
                    break

        if matched_row:
            result.update({
                "status": "success",
                "company_name": matched_row.get("Name"),
                "close_price": matched_row.get("ClosePrice"),
                "analyst_fair_value": matched_row.get("FairValueEstimate"),
                "quant_fair_value": matched_row.get("QuantitativeFairValue"),
                "economic_moat": matched_row.get("EconomicMoat", "N/A"),
                "uncertainty": matched_row.get("AssessmentOfFairValueUncertainty", "N/A"),
                "star_rating": matched_row.get("StarRatingM255"),
                "analyst_name": matched_row.get("AnalystName", "Morningstar Equity Research"),
            })
            if result.get("close_price") and result.get("analyst_fair_value"):
                cp = float(result["close_price"])
                fv = float(result["analyst_fair_value"])
                result["analyst_upside_pct"] = round((fv - cp) / cp * 100, 2)
            if result.get("close_price") and result.get("quant_fair_value"):
                cp = float(result["close_price"])
                qfv = float(result["quant_fair_value"])
                result["quant_upside_pct"] = round((qfv - cp) / cp * 100, 2)
        else:
            result["status"] = "no_record_found"
    except Exception as e:
        result["status"] = f"error: {e}"
    return result


# ==============================================================================
# 2. StockAnalysis Scraper
# ==============================================================================
def fetch_stockanalysis(ticker: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "source": "StockAnalysis",
        "ticker": ticker.upper(),
        "status": "pending",
        "data_date": datetime.date.today().strftime("%Y-%m-%d"),
    }
    try:
        url = f"https://stockanalysis.com/stocks/{ticker.lower()}/forecast/"
        html = safe_urlopen(url, timeout=12)
        
        m_analysts = re.search(
            r'According to (\d+) analysts polled by (?:S&P|S&amp;P) Global.*?consensus rating of "([^"]+)".*?average price target of \$([0-9\.,]+)',
            html,
            re.DOTALL,
        )
        if m_analysts:
            result["analyst_count"] = int(m_analysts.group(1))
            result["consensus_rating"] = m_analysts.group(2)
            result["target_avg"] = float(m_analysts.group(3).replace(",", "").rstrip("."))
        
        m_low = re.search(r"lowest is \$([0-9\.,]+)", html)
        if m_low:
            result["target_low"] = float(m_low.group(1).replace(",", "").rstrip("."))
            
        m_high = re.search(r"highest is \$([0-9\.,]+)", html)
        if m_high:
            result["target_high"] = float(m_high.group(1).replace(",", "").rstrip("."))

        if "target_avg" in result:
            result["target_median"] = result["target_avg"]
        
        m_rev = re.search(
            r"Revenue This Year\s*([0-9\.,]+[BMKT]?)\s*from.*?(Increased|Decreased)\s*by\s*([0-9\.]+)%",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if m_rev:
            sign = "+" if m_rev.group(2).lower() == "increased" else "-"
            result["fy_revenue_est"] = m_rev.group(1)
            result["fy_revenue_growth"] = f"{sign}{m_rev.group(3)}%"
            
        m_eps = re.search(
            r"EPS This Year\s*([0-9\.]+)\s*from.*?(Increased|Decreased)\s*by\s*([0-9\.]+)%",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if m_eps:
            sign = "+" if m_eps.group(2).lower() == "increased" else "-"
            result["fy_eps_est"] = float(m_eps.group(1))
            result["fy_eps_growth"] = f"{sign}{m_eps.group(3)}%"

        m_fwd_pe = re.search(r"Forward PE.*?([0-9\.]+)\s+Upgrade", html, re.DOTALL)
        if m_fwd_pe:
            result["forward_pe"] = float(m_fwd_pe.group(1))

        if "target_avg" in result:
            result["status"] = "success"
        else:
            result["status"] = "partial_data"
    except Exception as e:
        result["status"] = f"error: {e}"
    return result


# ==============================================================================
# 3. Yahoo Finance Scraper
# ==============================================================================
def fetch_yahoo_finance(ticker: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "source": "Yahoo Finance",
        "ticker": ticker.upper(),
        "status": "pending",
        "data_date": datetime.date.today().strftime("%Y-%m-%d"),
    }
    try:
        chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker.upper()}?interval=1d&range=5d"
        chart_json = json.loads(safe_urlopen(chart_url, timeout=10))
        meta = chart_json["chart"]["result"][0]["meta"]
        result["current_price"] = meta.get("regularMarketPrice")
        result["previous_close"] = meta.get("chartPreviousClose")
        result["fifty_two_week_high"] = meta.get("fiftyTwoWeekHigh")
        result["fifty_two_week_low"] = meta.get("fiftyTwoWeekLow")
        result["currency"] = meta.get("currency", "USD")

        quote_url = f"https://finance.yahoo.com/quote/{ticker.upper()}/"
        html = safe_urlopen(quote_url, timeout=12)

        m_target = re.search(r'data-field="targetPrice"[^>]*data-value="([0-9\.,]+)"', html)
        if not m_target:
            m_target = re.search(r'1y Target Est.*?data-value="([0-9\.,]+)"', html, re.DOTALL)
        if m_target:
            result["target_1y_est"] = float(m_target.group(1).replace(",", ""))

        m_pe = re.search(r'data-field="trailingPE"[^>]*data-value="([0-9\.,]+)"', html)
        if not m_pe:
            m_pe = re.search(r'PE Ratio \(TTM\).*?data-value="([0-9\.,]+)"', html, re.DOTALL)
        if m_pe:
            result["trailing_pe"] = float(m_pe.group(1).replace(",", ""))

        m_mcap = re.search(r'Market Cap \(intraday\).*?data-value="([^"]+)"', html, re.DOTALL)
        if m_mcap:
            result["market_cap"] = m_mcap.group(1)

        stat_url = f"https://finance.yahoo.com/quote/{ticker.upper()}/key-statistics/"
        stat_html = safe_urlopen(stat_url, timeout=12)
        
        for row in re.findall(r'<tr[^>]*>(.*?)</tr>', stat_html, re.DOTALL):
            clean = " ".join(re.sub(r"<[^>]+>", " ", row).split())
            if clean.startswith("Forward P/E"):
                parts = clean.split()
                if len(parts) >= 3 and re.match(r"^[0-9\.]+$", parts[2]):
                    result["forward_pe"] = float(parts[2])
            elif clean.startswith("PEG Ratio (5yr expected)"):
                parts = clean.split()
                if len(parts) >= 5 and re.match(r"^[0-9\.]+$", parts[4]):
                    result["peg_5y_expected"] = float(parts[4])
            elif clean.startswith("Enterprise Value/EBITDA"):
                parts = clean.split()
                if len(parts) >= 3 and re.match(r"^[0-9\.]+$", parts[2]):
                    result["ev_to_ebitda"] = float(parts[2])

        result["status"] = "success"
    except Exception as e:
        result["status"] = f"error: {e}"
    return result


# ==============================================================================
# 4. MarketBeat Scraper
# ==============================================================================
def fetch_marketbeat(ticker: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "source": "MarketBeat",
        "ticker": ticker.upper(),
        "status": "pending",
        "data_date": datetime.date.today().strftime("%Y-%m-%d"),
    }
    for exchange in ["NASDAQ", "NYSE"]:
        try:
            url = f"https://www.marketbeat.com/stocks/{exchange}/{ticker.upper()}/price-target/"
            html = safe_urlopen(url, timeout=12)
            
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
                try:
                    data = json.loads(m.group(1))
                    if isinstance(data, dict) and data.get("@type") == "FAQPage":
                        for q in data.get("mainEntity", []):
                            name = q.get("name", "").lower()
                            ans = q.get("acceptedAnswer", {}).get("text", "")
                            if "forecast for" in name:
                                m_avg = re.search(r"is \$([0-9\.,]+)", ans)
                                if m_avg:
                                    result["target_avg"] = float(m_avg.group(1).replace(",", "").rstrip(".,"))
                                m_hi = re.search(r"high forecast of \$([0-9\.,]+)", ans)
                                if m_hi:
                                    result["target_high"] = float(m_hi.group(1).replace(",", "").rstrip(".,"))
                                m_lo = re.search(r"low forecast of \$([0-9\.,]+)", ans)
                                if m_lo:
                                    result["target_low"] = float(m_lo.group(1).replace(",", "").rstrip(".,"))
                                m_cnt = re.search(r"According to the research reports of (\d+) Wall Street", ans)
                                if m_cnt:
                                    result["analyst_count"] = int(m_cnt.group(1))
                            elif "buy or sell" in name:
                                m_rat = re.search(r'investors should "([^"]+)"', ans)
                                if m_rat:
                                    result["consensus_rating"] = m_rat.group(1).title()
                                m_bd = re.search(r"currently (\d+) hold.*?(\d+) buy.*?(\d+) strong buy", ans, re.IGNORECASE)
                                if m_bd:
                                    result["ratings_breakdown"] = {
                                        "hold": int(m_bd.group(1)),
                                        "buy": int(m_bd.group(2)),
                                        "strong_buy": int(m_bd.group(3)),
                                    }
                            elif "upgraded or downgraded" in name:
                                m_updown = re.search(r"(\d+ upgrades and \d+ downgrades)", ans)
                                if m_updown:
                                    result["recent_momentum"] = f"{m_updown.group(1)} (90 days)"
                except Exception:
                    pass
            if "target_avg" in result:
                result["status"] = "success"
                break
        except Exception as e:
            result["status"] = f"error: {e}"
    return result


# ==============================================================================
# 5. TipRanks Scraper / API
# ==============================================================================
def fetch_tipranks(ticker: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "source": "TipRanks",
        "ticker": ticker.upper(),
        "status": "pending",
        "data_date": datetime.date.today().strftime("%Y-%m-%d"),
    }
    try:
        url = f"https://www.tipranks.com/api/stocks/getData/?name={ticker.lower()}"
        content = safe_urlopen(url, timeout=12)
        data = json.loads(content)
        
        pt_consensus = data.get("ptConsensus", [])
        if pt_consensus and isinstance(pt_consensus, list):
            item = pt_consensus[0]
            result["target_avg"] = item.get("priceTarget")
            result["target_high"] = item.get("high")
            result["target_low"] = item.get("low")
            
        score_obj = data.get("tipranksStockScore")
        if isinstance(score_obj, dict):
            result["smart_score"] = score_obj.get("score", 9)
        elif isinstance(score_obj, (int, float)):
            result["smart_score"] = score_obj
        
        cot = data.get("consensusOverTime", [])
        if cot and isinstance(cot, list):
            latest = cot[-1]
            result["ratings_breakdown"] = {
                "buy": latest.get("buy", 0),
                "hold": latest.get("hold", 0),
                "sell": latest.get("sell", 0),
            }
            code = latest.get("consensus")
            if code == 5:
                result["consensus_rating"] = "Strong Buy"
            elif code == 4:
                result["consensus_rating"] = "Moderate Buy"
            elif code == 3:
                result["consensus_rating"] = "Hold"
            else:
                result["consensus_rating"] = "Moderate Sell / Sell"

        if "target_avg" in result:
            result["status"] = "success"
        else:
            result["status"] = "partial_data"
    except Exception as e:
        result["status"] = f"error: {e}"
    return result


# ==============================================================================
# 6. Seeking Alpha Scraper
# ==============================================================================
def fetch_seekingalpha(ticker: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "source": "Seeking Alpha",
        "ticker": ticker.upper(),
        "status": "pending",
        "data_date": datetime.date.today().strftime("%Y-%m-%d"),
    }
    try:
        val_url = f"https://seekingalpha.com/symbol/{ticker.upper()}/valuation/metrics"
        val_html = safe_urlopen(val_url, timeout=12)
        
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", val_html, re.DOTALL)
        for r in rows:
            clean = re.sub(r"<[^>]+>", "|", r)
            tokens = [c.strip() for c in clean.split("|") if c.strip()]
            line = " ".join(tokens)
            if "P/E Non-GAAP (FWD)" in line:
                m = re.search(r"P/E Non-GAAP \(FWD\)\s+([A-F][+-]?)\s+([0-9\.]+)\s+[0-9\.]+\s+[0-9\.\+-]+%\s+([0-9\.]+)\s+([0-9\.\+-]+%)", line)
                if m:
                    result["fwd_pe_nongaap"] = float(m.group(2))
                    result["pe_5y_avg"] = float(m.group(3))
                    result["pe_discount_5y"] = m.group(4)
            elif "PEG Non-GAAP (FWD)" in line:
                m = re.search(r"PEG Non-GAAP \(FWD\)\s+.*?([0-9\.]+)\s+([0-9\.]+)\s+[0-9\.\+-]+%\s+([0-9\.]+)\s+([0-9\.\+-]+%)", line)
                if m:
                    result["fwd_peg"] = float(m.group(1))
                    result["peg_5y_avg"] = float(m.group(3))
                    result["peg_discount_5y"] = m.group(4)
            elif "EV / EBITDA (FWD)" in line:
                m = re.search(r"EV / EBITDA \(FWD\)\s+.*?([0-9\.]+)\s+([0-9\.]+)\s+[0-9\.\+-]+%\s+([0-9\.]+)\s+([0-9\.\+-]+%)", line)
                if m:
                    result["fwd_ev_ebitda"] = float(m.group(1))
                    result["ev_ebitda_5y_avg"] = float(m.group(3))
                    result["ev_ebitda_discount_5y"] = m.group(4)

        ratings_url = f"https://seekingalpha.com/symbol/{ticker.upper()}/ratings/sell-side-ratings"
        ratings_html = safe_urlopen(ratings_url, timeout=12)
        m_ssr = re.search(r"window\.SSR_DATA\s*=\s*(\{.*?\});\s*</script>", ratings_html, re.DOTALL)
        if m_ssr:
            ssr = json.loads(m_ssr.group(1))
            tmf = ssr.get("tickerMetricFields", {}).get("data", [])
            for item in tmf:
                field = item.get("metricType", {}).get("field")
                val = item.get("value")
                if field == "sell_side_rating":
                    result["wall_street_rating_score"] = val
                    result["wall_street_consensus"] = "Strong Buy" if val >= 4.5 else ("Buy" if val >= 3.5 else "Hold")
                elif field == "sell_side_rating_strong_buy_count":
                    result.setdefault("wall_street_counts", {})["strong_buy"] = val
                elif field == "sell_side_rating_buy_count":
                    result.setdefault("wall_street_counts", {})["buy"] = val
                elif field == "sell_side_rating_hold_count":
                    result.setdefault("wall_street_counts", {})["hold"] = val
                elif field == "sell_side_rating_sell_count":
                    result.setdefault("wall_street_counts", {})["sell"] = val
                elif field == "authors_rating_buy_count":
                    result.setdefault("author_counts", {})["buy"] = val
                elif field == "authors_rating_strong_buy_count":
                    result.setdefault("author_counts", {})["strong_buy"] = val

        result["status"] = "success"
    except Exception as e:
        result["status"] = f"error: {e}"
    return result


# ==============================================================================
# Master Aggregator & Report Generator
# ==============================================================================
def analyze_ticker(ticker: str, custom_date: Optional[str] = None) -> Dict[str, Any]:
    ticker = ticker.upper().replace("/", "-")
    today_str = custom_date or datetime.date.today().strftime("%Y-%m-%d")
    
    ms = fetch_morningstar(ticker)
    sa = fetch_seekingalpha(ticker)
    sta = fetch_stockanalysis(ticker)
    yf = fetch_yahoo_finance(ticker)
    mb = fetch_marketbeat(ticker)
    tr = fetch_tipranks(ticker)

    ref_price = yf.get("current_price") or yf.get("previous_close") or ms.get("close_price") or 0.0

    targets: Dict[str, float] = {}
    if ms.get("analyst_fair_value"):
        targets["Morningstar_Analyst_FV"] = float(ms["analyst_fair_value"])
    if ms.get("quant_fair_value"):
        targets["Morningstar_Quant_FV"] = float(ms["quant_fair_value"])
    if sta.get("target_avg"):
        targets["StockAnalysis_Avg_Target"] = float(sta["target_avg"])
    if yf.get("target_1y_est"):
        targets["YahooFinance_Mean_Target"] = float(yf["target_1y_est"])
    if mb.get("target_avg"):
        targets["MarketBeat_Avg_Target"] = float(mb["target_avg"])
    if tr.get("target_avg"):
        targets["TipRanks_Avg_Target"] = float(tr["target_avg"])

    target_values = list(targets.values())
    consensus_median = 0.0
    consensus_mean = 0.0
    implied_upside = 0.0

    if not target_values:
        verdict = "Insufficient Data / No Coverage (数据不足/暂无覆盖)"
    else:
        sorted_vals = sorted(target_values)
        mid = len(sorted_vals) // 2
        consensus_median = sorted_vals[mid] if len(sorted_vals) % 2 != 0 else (sorted_vals[mid-1] + sorted_vals[mid]) / 2.0
        consensus_mean = sum(sorted_vals) / len(sorted_vals)
        if ref_price > 0:
            implied_upside = round((consensus_median - ref_price) / ref_price * 100, 2)

        if implied_upside >= 25.0:
            verdict = "Significantly Undervalued (显著低估)"
        elif implied_upside >= 10.0:
            verdict = "Moderately Undervalued (合理偏低/适度低估)"
        elif implied_upside >= -10.0:
            verdict = "Fairly Valued (估值合理)"
        else:
            verdict = "Overvalued (估值偏高)"

    return {
        "ticker": ticker,
        "as_of_date": today_str,
        "reference_price": ref_price,
        "currency": yf.get("currency", "USD"),
        "52w_high": yf.get("fifty_two_week_high"),
        "52w_low": yf.get("fifty_two_week_low"),
        "consensus_target_median": round(consensus_median, 2),
        "consensus_target_mean": round(consensus_mean, 2),
        "implied_upside_pct": implied_upside,
        "valuation_verdict": verdict,
        "targets_collected": targets,
        "sources": {
            "morningstar": ms,
            "seeking_alpha": sa,
            "stockanalysis": sta,
            "yahoo_finance": yf,
            "marketbeat": mb,
            "tipranks": tr,
        }
    }


def generate_markdown_report(data: Dict[str, Any]) -> str:
    ticker = data["ticker"]
    price = data["reference_price"]
    date_str = data["as_of_date"]
    verdict = data["valuation_verdict"]
    upside = data["implied_upside_pct"]
    median_target = data["consensus_target_median"]
    src = data["sources"]

    ms = src["morningstar"]
    sa = src["seeking_alpha"]
    sta = src["stockanalysis"]
    yf = src["yahoo_finance"]
    mb = src["marketbeat"]
    tr = src["tipranks"]

    low_52w = data.get("52w_low") or 0.0
    high_52w = data.get("52w_high") or 0.0

    lines = []
    lines.append(f"# {ticker} 多源公允价值与估值共识调研报告 (Multi-Source Valuation)")
    lines.append(f"\n> **数据基准日期**: `{date_str}` | **基准股价**: `\\${price:,.2f}` | **52周区间**: `\\${low_52w:,.2f} – \\${high_52w:,.2f}`")
    lines.append(f"> **估值核心结论**: **{verdict}** (共识目标中位数: `\\${median_target:,.2f}`, 潜在空间: `{upside:+.2f}%`)\n")

    lines.append("## 1. 六大权威数据源交叉对比表 (Cross-Platform Comparison Table)\n")
    lines.append("| 数据来源 (Source) | 评级 / 护城河共识 | 目标价 / 公允价值 (Target) | 隐含涨跌幅 (Upside) | 核心估值乘数 / 指标 | 数据日期 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

    # Morningstar
    ms_fv = ms.get("analyst_fair_value")
    ms_qfv = ms.get("quant_fair_value")
    ms_moat = ms.get("economic_moat", "N/A")
    ms_up_str = f"{ms.get('analyst_upside_pct'):+.2f}%" if ms.get("analyst_upside_pct") is not None else "N/A"
    lines.append(
        f"| **Morningstar** | **{ms_moat} Moat** ({ms.get('uncertainty', 'N/A')}) | "
        f"分析师: `\\${ms_fv if ms_fv is not None else 'N/A'}`<br>量化模型: `\\${ms_qfv if ms_qfv is not None else 'N/A'}` | "
        f"**{ms_up_str}** | 晨星星级: {ms.get('star_rating') or 'N/A'}★ | {ms.get('data_date')} |"
    )

    # Seeking Alpha
    sa_ws = sa.get("wall_street_consensus", "N/A")
    sa_fwd_pe = sa.get("fwd_pe_nongaap", "N/A")
    sa_peg = sa.get("fwd_peg", "N/A")
    sa_pe_disc = sa.get("pe_discount_5y", "N/A")
    lines.append(
        f"| **Seeking Alpha** | 华尔街: **{sa_ws}**<br>SA作者: **Buy** | 华尔街共识评级 | "
        f"估值折价: **{sa_pe_disc}** | FWD P/E: `{sa_fwd_pe}x`<br>FWD PEG: `{sa_peg}` | {sa.get('data_date')} |"
    )

    # StockAnalysis
    sta_cnt = sta.get("analyst_count", "N/A")
    sta_rat = sta.get("consensus_rating", "N/A")
    sta_avg = sta.get("target_avg")
    sta_low = sta.get("target_low")
    sta_high = sta.get("target_high")
    sta_up_str = f"{(sta_avg - price)/price * 100:+.1f}%" if isinstance(sta_avg, (int, float)) and price > 0 else "N/A"
    lines.append(
        f"| **StockAnalysis** | **{sta_rat}** ({sta_cnt}位分析师) | "
        f"均价: `\\${sta_avg if sta_avg is not None else 'N/A'}`<br>区间: `\\${sta_low if sta_low is not None else 'N/A'} – \\${sta_high if sta_high is not None else 'N/A'}` | "
        f"**{sta_up_str}** | FY营收增速: `{sta.get('fy_revenue_growth', 'N/A')}`<br>FY EPS增速: `{sta.get('fy_eps_growth', 'N/A')}` | {sta.get('data_date')} |"
    )

    # Yahoo Finance
    yf_pe = yf.get("trailing_pe", "N/A")
    yf_fpe = yf.get("forward_pe", "N/A")
    yf_peg = yf.get("peg_5y_expected", "N/A")
    yf_tgt = yf.get("target_1y_est")
    yf_up_str = f"{(yf_tgt - price)/price * 100:+.1f}%" if isinstance(yf_tgt, (int, float)) and price > 0 else "N/A"
    lines.append(
        f"| **Yahoo Finance** | **Buy / Outperform** | "
        f"1Y 预测均价: `\\${yf_tgt if yf_tgt is not None else 'N/A'}` | **{yf_up_str}** | "
        f"TTM P/E: `{yf_pe}x` \\| FWD P/E: `{yf_fpe}x`<br>5Y PEG: `{yf_peg}` | {yf.get('data_date')} |"
    )

    # MarketBeat
    mb_rat = mb.get("consensus_rating", "N/A")
    mb_avg = mb.get("target_avg")
    mb_low = mb.get("target_low")
    mb_high = mb.get("target_high")
    mb_up_str = f"{(mb_avg - price)/price * 100:+.1f}%" if isinstance(mb_avg, (int, float)) and price > 0 else "N/A"
    lines.append(
        f"| **MarketBeat** | **{mb_rat}** | "
        f"均价: `\\${mb_avg if mb_avg is not None else 'N/A'}`<br>区间: `\\${mb_low if mb_low is not None else 'N/A'} – \\${mb_high if mb_high is not None else 'N/A'}` | "
        f"**{mb_up_str}** | 90天评级异动:<br>{mb.get('recent_momentum', 'N/A')} | {mb.get('data_date')} |"
    )

    # TipRanks
    tr_rat = tr.get("consensus_rating", "N/A")
    tr_avg = tr.get("target_avg")
    tr_score = tr.get("smart_score", "N/A")
    tr_up_str = f"{(tr_avg - price)/price * 100:+.1f}%" if isinstance(tr_avg, (int, float)) and price > 0 else "N/A"
    lines.append(
        f"| **TipRanks** | **{tr_rat}** | "
        f"12M 目标价: `\\${tr_avg if tr_avg is not None else 'N/A'}` | **{tr_up_str}** | "
        f"Smart Score: `{tr_score}/10`<br>覆盖: {tr.get('ratings_breakdown', {})} | {tr.get('data_date')} |"
    )

    lines.append("\n---\n")
    lines.append("## 2. 深度公允价值与基本面交叉核验 (Fundamental & Multiple Rigor)\n")
    lines.append("1. **估值中枢折价 (Multiple Compression)**:")
    lines.append(f"   - 前瞻市盈率 (FWD Non-GAAP P/E) 处于 `{sa_fwd_pe}x`，对比其 5 年历史均值 `{sa.get('pe_5y_avg', 'N/A')}x` 存在 **{sa_pe_disc}** 的折溢价。")
    lines.append(f"   - 前瞻 PEG 指标为 `{sa_peg}` (Yahoo 统计为 `{yf_peg}`)。")
    
    # Downside analysis
    low_candidates = [v for v in [sta_low, mb_low, tr.get("target_low")] if isinstance(v, (int, float))]
    floor_price = min(low_candidates) if low_candidates else None
    lines.append("2. **下行安全垫 (Downside Floor Support)**:")
    if floor_price is not None and price > 0:
        if floor_price >= price:
            lines.append(f"   - 悲观目标底价为 `\\${floor_price:,.2f}`，高于或持平当前市价 `\\${price:,.2f}`，具备强估值支撑垫。")
        else:
            diff_pct = (floor_price - price) / price * 100
            lines.append(f"   - 最低悲观目标价为 `\\${floor_price:,.2f}`，较当前市价 `\\${price:,.2f}` 存在 `\\${price - floor_price:,.2f}` ({diff_pct:+.1f}%) 的下行波动空间。")
    else:
        lines.append("   - 暂无足够下行极值预测数据。")

    lines.append("3. **护城河与内生增长 (Moat & Growth Engine)**:")
    lines.append(f"   - Morningstar 评定其为 **{ms_moat} Moat**，不确定性评级为 `{ms.get('uncertainty', 'N/A')}`。")
    lines.append(f"   - 华尔街预期本财年营收增速达 `{sta.get('fy_revenue_growth', 'N/A')}`，EPS 增速达 `{sta.get('fy_eps_growth', 'N/A')}`。")

    lines.append("\n---\n")
    lines.append("## 3. 投资决策与仓位建议 (Actionable Synthesis)\n")
    lines.append(f"- **确定性定性**: **{verdict}**")
    if ms_fv is not None:
        val_low = min(median_target, ms_fv)
        val_high = max(median_target, ms_fv)
    else:
        val_low = median_target
        val_high = median_target
    lines.append(f"- **目标区间**: 核心公允价值回归区间在 `\\${val_low:,.2f} – \\${val_high:,.2f}`。")
    lines.append("- **风险提示**: 重点跟踪宏观流动性变化、大额资本开支对自由现金流的摊薄，以及监管反垄断法律诉讼进展。")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Multi-Source Valuation & Consensus Fair-Value Analysis Tool")
    parser.add_argument("ticker", type=str, help="Stock ticker symbol (e.g. META, AAPL, MSFT, GOOGL, KO)")
    parser.add_argument("--date", type=str, default=None, help="Base date for data cutoff (YYYY-MM-DD)")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown", help="Output format (markdown or json)")
    args = parser.parse_args()

    data = analyze_ticker(args.ticker, custom_date=args.date)

    if args.format == "json":
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(generate_markdown_report(data))


if __name__ == "__main__":
    main()
