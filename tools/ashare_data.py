#!/usr/bin/env python3
"""A股数据工具 — 腾讯行情 + 东方财富搜索/财务，零外部依赖（仅 stdlib）。

为 Claude Code Skills 提供 A 股实时行情、财务数据等数据。
设计原则：独立模块，不影响现有工具；使用 curl 直连绕过系统代理。

用法（由 Skills 自动调用）：
    python3.11 tools/ashare_data.py quote 600519                    # 实时行情
    python3.11 tools/ashare_data.py financials 600519               # 核心财务数据（近5年）
    python3.11 tools/ashare_data.py valuation 600519                # 估值指标
    python3.11 tools/ashare_data.py search 茅台                      # 搜索股票代码

需要 Python >= 3.8，零外部依赖。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from decimal import Decimal, InvalidOperation


def _force_utf8_stdio():
    """把 stdout/stderr 强制切到 UTF-8，防止 Windows 编码崩溃。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

_force_utf8_stdio()

_TIMEOUT = 15
_CURL_BIN = shutil.which("curl") or "curl"


def _curl(url):
    """用 curl --noproxy 直连，绕过系统代理。"""
    result = subprocess.run(
        [_CURL_BIN, "-s", "--noproxy", "*",
         "-H", "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
         url],
        capture_output=True, timeout=_TIMEOUT,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ConnectionError(f"请求失败: {url}")
    # 腾讯行情 API 返回 GBK 编码，其他返回 UTF-8
    try:
        return result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return result.stdout.decode("gbk")


def _curl_json(url, params=None):
    """curl 获取 JSON。"""
    if params:
        from urllib.parse import urlencode
        url = f"{url}?{urlencode(params)}"
    return json.loads(_curl(url))


# ---------------------------------------------------------------------------
# 腾讯行情 API（稳定可靠，无需鉴权）
# ---------------------------------------------------------------------------

def _normalize_a_code(code: str) -> str:
    return code.strip().replace(".SH", "").replace(".SZ", "").replace(".BJ", "")


def _board_prefix(code: str) -> str:
    """Tencent board prefix: sh / sz / bj.

    92xxxx 北交所新股必须在 9xxxx 沪市 B 股之前判断，否则会被标成 sh。
    688 科创板以 6 开头，归沪市，不能落到 startswith('8') 的北交所分支。
    """
    c = _normalize_a_code(code)
    if c.startswith(("6", "5")) or (c.startswith("9") and not c.startswith("92")):
        return "sh"
    if c.startswith(("0", "3", "2", "1")):
        return "sz"
    if c.startswith(("4", "8", "92")):
        return "bj"
    return "sh"


def _listing_exchange(code: str) -> str:
    """Exchange suffix for East Money SECUCODE: SH / SZ / BJ."""
    return _board_prefix(code).upper()


def _qq_code(code: str) -> str:
    """将股票代码转为腾讯行情格式。"""
    c = _normalize_a_code(code)
    return f"{_board_prefix(c)}{c}"


def _parse_qq_quote(raw: str) -> dict:
    """解析腾讯行情数据。格式：v_shXXXXXX="字段1~字段2~..."; """
    start = raw.find('"')
    end = raw.rfind('"')
    if start < 0 or end <= start:
        return {}
    fields = raw[start + 1:end].split("~")
    if len(fields) < 50:
        return {}
    return {
        "name": fields[1],
        "code": fields[2],
        "price": fields[3],
        "prev_close": fields[4],
        "open": fields[5],
        "volume": fields[6],         # 手
        "buy_vol": fields[7],
        "sell_vol": fields[8],
        "high": fields[33] if len(fields) > 33 else fields[3],
        "low": fields[34] if len(fields) > 34 else fields[3],
        "change_pct": fields[32],
        "change_amt": fields[31],
        "turnover_amt": fields[37] if len(fields) > 37 else "-",
        "turnover_rate": fields[38] if len(fields) > 38 else "-",
        "pe": fields[39] if len(fields) > 39 else "-",
        "market_cap": fields[45] if len(fields) > 45 else "-",    # 总市值（亿）
        "float_cap": fields[44] if len(fields) > 44 else "-",     # 流通市值（亿）
        "pb": fields[46] if len(fields) > 46 else "-",
        # 注意：腾讯 ~ 分隔协议第 47/48 位是当日涨停价/跌停价，不是 52 周极值（issue #70）
        "limit_up": fields[47] if len(fields) > 47 else "-",
        "limit_down": fields[48] if len(fields) > 48 else "-",
        # 腾讯 ~72/73 为流通股本/总股本（股）。第 38 位是换手率，不能当股本。
        "float_shares": fields[72] if len(fields) > 72 else "-",
        "total_shares": fields[73] if len(fields) > 73 else "-",
    }


def _em_secid(code: str) -> str:
    """将股票代码转为东方财富 secid 格式：沪市前缀 1.，深市/北交所前缀 0.。"""
    c = _normalize_a_code(code)
    prefix = "1" if _board_prefix(c) == "sh" else "0"
    return f"{prefix}.{c}"


def _fetch_52w(code: str) -> tuple:
    """从东方财富取 52 周最高/最低（f174/f175）。

    腾讯行情协议无此数据。优先 push2delay（主站 push2 对连续请求限流较严，
    52 周极值不受延时行情影响），失败回退 push2。取不到返回 ("-", "-")。
    """
    secid = _em_secid(code)
    query = f"api/qt/stock/get?secid={secid}&fields=f174,f175&invt=2&fltt=2"
    for host in ("push2delay.eastmoney.com", "push2.eastmoney.com"):
        try:
            data = _curl_json(f"https://{host}/{query}").get("data") or {}
            high, low = data.get("f174"), data.get("f175")
            if high not in (None, "-") and low not in (None, "-"):
                return high, low
        except Exception:
            continue
    return "-", "-"


def _optional_decimal(value):
    if value is None or value == "-" or value == "":
        return None
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if d == 0:
        return None
    return d


def verify_price_times_shares(price, shares, reported_cap_yuan, max_deviation_pct=5.0):
    """Independent check: price × shares vs reported cap in yuan.

    Never derive shares from the cap being verified. If the raw share count
    looks like 万股 (off by ~1e4), rescale once.
    Returns a dict, or None if any input is missing.
    """
    p = _optional_decimal(price)
    s = _optional_decimal(shares)
    r = _optional_decimal(reported_cap_yuan)
    if p is None or s is None or r is None:
        return None
    calc = p * s
    dev = abs(float(calc - r) / float(r)) * 100 if r != 0 else 0.0
    if dev > 50:
        calc_wan = p * s * Decimal(10000)
        dev_wan = abs(float(calc_wan - r) / float(r)) * 100
        if dev_wan < dev:
            calc, s, dev = calc_wan, s * Decimal(10000), dev_wan
    return {
        "ok": dev <= max_deviation_pct,
        "calculated": calc,
        "reported": r,
        "deviation_pct": dev,
        "shares_used": s,
    }


def _fetch_total_shares(code: str):
    """East Money f84 = 总股本（股，fltt=2 原始值）。取不到返回 None。"""
    secid = _em_secid(code)
    query = f"api/qt/stock/get?secid={secid}&fields=f84&invt=2&fltt=2"
    for host in ("push2delay.eastmoney.com", "push2.eastmoney.com"):
        try:
            data = _curl_json(f"https://{host}/{query}").get("data") or {}
            shares = data.get("f84")
            if shares not in (None, "-", ""):
                return shares
        except Exception:
            continue
    return None


def _fmt_yi(value) -> str:
    if value is None or value == "-" or value == "":
        return "-"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return str(value)
    if abs(v) >= 1e8:
        return f"{v / 1e8:.2f}亿"
    if abs(v) >= 1e4:
        return f"{v / 1e4:.2f}万"
    return f"{v:.2f}"


def _fmt_pct(value) -> str:
    if value is None or value == "-" or value == "":
        return "-"
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return str(value)


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------

def cmd_quote(code: str):
    """实时行情快照。"""
    qq_code = _qq_code(code)
    raw = _curl(f"https://qt.gtimg.cn/q={qq_code}")
    d = _parse_qq_quote(raw)
    if not d:
        print(f"❌ 未找到股票 {code}")
        return

    print("=" * 60)
    print(f"实时行情: {d['name']} ({d['code']})")
    print("=" * 60)
    print(f"  当前价:     {d['price']}")
    print(f"  涨跌幅:     {d['change_pct']}%")
    print(f"  涨跌额:     {d['change_amt']}")
    print(f"  今开:       {d['open']}")
    print(f"  最高:       {d['high']}")
    print(f"  最低:       {d['low']}")
    print(f"  昨收:       {d['prev_close']}")
    print(f"  成交量:     {d['volume']} 手")
    print(f"  成交额:     {d['turnover_amt']}万")
    print(f"  总市值:     {d['market_cap']}亿")
    print(f"  流通市值:   {d['float_cap']}亿")
    print(f"  PE(动):     {d['pe']}")
    print(f"  PB:         {d['pb']}")
    print(f"  换手率:     {d['turnover_rate']}%")
    high_52w, low_52w = _fetch_52w(code)
    print(f"  52周最高:   {high_52w}")
    print(f"  52周最低:   {low_52w}")


def cmd_valuation(code: str):
    """估值指标汇总。"""
    qq_code = _qq_code(code)
    raw = _curl(f"https://qt.gtimg.cn/q={qq_code}")
    d = _parse_qq_quote(raw)
    if not d:
        print(f"❌ 未找到股票 {code}")
        return

    price = d["price"]
    market_cap_yi = d["market_cap"]

    print("=" * 60)
    print(f"估值指标: {d['name']} ({d['code']})")
    print("=" * 60)
    print(f"  当前价:     {price}")
    print(f"  总市值:     {market_cap_yi}亿")
    print(f"  流通市值:   {d['float_cap']}亿")
    print(f"  PE(动):     {d['pe']}")
    print(f"  PB:         {d['pb']}")
    high_52w, low_52w = _fetch_52w(code)
    print(f"  52周最高:   {high_52w}")
    print(f"  52周最低:   {low_52w}")

    shares = _optional_decimal(d.get("total_shares"))
    if shares is None:
        shares = _optional_decimal(_fetch_total_shares(code))
    reported_yuan = _optional_decimal(market_cap_yi)
    if reported_yuan is not None:
        reported_yuan *= Decimal("1e8")
    result = verify_price_times_shares(price, shares, reported_yuan)
    if result is None:
        print("\n  ⚠️ 缺少独立总股本，无法验算市值（不会用市值反推股本）")
    else:
        print(f"\n  总股本:     {_fmt_yi(float(result['shares_used']))}股")
        print(f"  计算市值:   {_fmt_yi(float(result['calculated']))}")
        if result["ok"]:
            print(f"  市值验算:   ✅ 股价×股本 vs 报告市值，偏差 {result['deviation_pct']:.2f}%")
        else:
            print(f"  市值验算:   ❌ 偏差 {result['deviation_pct']:.2f}% > 5%，请核对本位与股本口径")


def cmd_financials(code: str):
    """近5年核心财务数据。"""
    qq_code = _qq_code(code)
    raw = _curl(f"https://qt.gtimg.cn/q={qq_code}")
    d = _parse_qq_quote(raw)
    name = d.get("name", code) if d else code

    code_clean = _normalize_a_code(code)
    market = _listing_exchange(code_clean)

    # 东方财富 datacenter API（年报数据）
    fin_url = "https://datacenter.eastmoney.com/securities/api/data/get"
    params = {
        "type": "RPT_F10_FINANCE_MAINFINADATA",
        "sty": "ALL",
        "filter": f'(SECUCODE="{code_clean}.{market}")(REPORT_TYPE="年报")',
        "p": "1",
        "ps": "5",
        "sr": "-1",
        "st": "REPORT_DATE",
        "source": "HSF10",
        "client": "PC",
    }
    reports = []
    try:
        data = _curl_json(fin_url, params)
        reports = data.get("result", {}).get("data", [])
    except Exception:
        pass

    # 如果年报筛选无结果，去掉年报限制
    if not reports:
        params["filter"] = f'(SECUCODE="{code_clean}.{market}")'
        try:
            data = _curl_json(fin_url, params)
            reports = data.get("result", {}).get("data", [])
        except Exception:
            pass

    print("=" * 60)
    print(f"核心财务数据: {name} ({code_clean})")
    print("=" * 60)

    if not reports:
        print("  ⚠️ 未能获取财务数据，建议通过 WebSearch 补充")
        return

    for r in reports[:5]:
        date = r.get("REPORT_DATE", "")[:10]
        report_name = r.get("REPORT_DATE_NAME", "")
        revenue = r.get("TOTALOPERATEREVE")
        net_profit = r.get("PARENTNETPROFIT")
        kcf_profit = r.get("KCFJCXSYJLR")
        gross_margin = r.get("XSMLL")
        net_margin = r.get("XSJLL")
        eps = r.get("EPSJB")
        bps = r.get("BPS")
        roe = r.get("ROEJQ")
        roic = r.get("ROIC")
        ocf = r.get("NETCASH_OPERATE_PK")
        debt_ratio = r.get("ZCFZL")
        inventory_days = r.get("CHZZTS")
        ar_days = r.get("YSZKZZTS")
        rev_growth = r.get("TOTALOPERATEREVETZ")
        profit_growth = r.get("PARENTNETPROFITTZ")
        kcf_growth = r.get("KCFJCXSYJLRTZ")

        print(f"\n  --- {date} {report_name} ---")
        if revenue is not None:
            print(f"  营收:           {_fmt_yi(revenue)}")
        if rev_growth is not None:
            print(f"  营收增速:       {_fmt_pct(rev_growth)}")
        if net_profit is not None:
            print(f"  归母净利润:     {_fmt_yi(net_profit)}")
        if profit_growth is not None:
            print(f"  净利润增速:     {_fmt_pct(profit_growth)}")
        if kcf_profit is not None:
            print(f"  扣非净利润:     {_fmt_yi(kcf_profit)}")
        if kcf_growth is not None:
            print(f"  扣非净利增速:   {_fmt_pct(kcf_growth)}")
        if gross_margin is not None:
            print(f"  销售毛利率:     {_fmt_pct(gross_margin)}")
        if net_margin is not None:
            print(f"  销售净利率:     {_fmt_pct(net_margin)}")
        if eps is not None:
            print(f"  基本每股收益:   {eps}")
        if bps is not None:
            try:
                print(f"  每股净资产:     {float(bps):.2f}")
            except (ValueError, TypeError):
                print(f"  每股净资产:     {bps}")
        if roe is not None:
            print(f"  ROE(加权):      {_fmt_pct(roe)}")
        if roic is not None:
            print(f"  ROIC:           {_fmt_pct(roic)}")
        if ocf is not None:
            print(f"  经营现金流OCF:  {_fmt_yi(ocf)}")
        if debt_ratio is not None:
            print(f"  资产负债率:     {_fmt_pct(debt_ratio)}")
        if inventory_days is not None:
            try:
                print(f"  存货周转天数:   {float(inventory_days):.1f}天")
            except (ValueError, TypeError):
                pass
        if ar_days is not None:
            try:
                print(f"  应收周转天数:   {float(ar_days):.1f}天")
            except (ValueError, TypeError):
                pass


def cmd_search(keyword: str):
    """搜索股票代码。"""
    url = "https://searchadapter.eastmoney.com/api/suggest/get"
    # Public East Money suggest-API client token (the same value the website
    # sends). Override with EASTMONEY_SEARCH_TOKEN if it is rotated.
    _EASTMONEY_PUBLIC_SEARCH_TOKEN = "D43BF722C8E33BDC906FB84D85E326E8"
    token = os.environ.get("EASTMONEY_SEARCH_TOKEN") or _EASTMONEY_PUBLIC_SEARCH_TOKEN
    params = {
        "input": keyword,
        "type": "14",
        "token": token,
        "count": "10",
    }
    data = _curl_json(url, params)
    results = data.get("QuotationCodeTable", {}).get("Data", [])

    if not results:
        print(f"❌ 未找到匹配 '{keyword}' 的股票")
        return

    print("=" * 60)
    print(f"搜索结果: '{keyword}'")
    print("=" * 60)
    for r in results:
        code = r.get("Code", "")
        name = r.get("Name", "")
        market = r.get("MktNum", "")
        mkt_label = {"1": "沪", "2": "深", "3": "北"}.get(str(market), "")
        print(f"  {code} {name} [{mkt_label}]")


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="A股数据工具 — 腾讯行情 + 东方财富财务数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    p_quote = sub.add_parser("quote", help="实时行情")
    p_quote.add_argument("code", help="股票代码，如 600519")

    p_fin = sub.add_parser("financials", help="核心财务数据（近5年）")
    p_fin.add_argument("code", help="股票代码")

    p_val = sub.add_parser("valuation", help="估值指标")
    p_val.add_argument("code", help="股票代码")

    p_search = sub.add_parser("search", help="搜索股票代码")
    p_search.add_argument("keyword", help="公司名或关键词")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmds = {
        "quote": lambda: cmd_quote(args.code),
        "financials": lambda: cmd_financials(args.code),
        "valuation": lambda: cmd_valuation(args.code),
        "search": lambda: cmd_search(args.keyword),
    }
    cmds[args.command]()


if __name__ == "__main__":
    main()
