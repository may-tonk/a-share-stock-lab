"""只获取东方财富日线、不复权数据；无自动重试、备用源或代理切换。"""
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

import requests

URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
CHINA_TZ = timezone(timedelta(hours=8))
NUMERIC_FIELDS = (
    "open", "close", "high", "low", "volume", "amount",
    "amplitude", "change_pct", "change_amount", "turnover",
)


class ProviderError(RuntimeError):
    pass


def china_now():
    return datetime.now(CHINA_TZ).replace(tzinfo=None)


def daily_cutoff():
    # 第一版在北京时间18点后尝试获取当日日线；是否已发布以接口返回为准。
    now = china_now()
    return now.date() if now.hour >= 18 else now.date() - timedelta(days=1)


def normalize_symbol(value: str):
    value = value.strip().lower()
    match = re.fullmatch(r"(?:(sh|sz|bj)\.?)(\d{6})|([0-9]{6})", value)
    if not match:
        raise ValueError("股票代码格式应为000001或sz.000001")
    code = match.group(2) or match.group(3)
    if code.startswith("6"):
        market = "sh"
    elif code.startswith(("0", "3")):
        market = "sz"
    elif code.startswith(("4", "8", "92")):
        market = "bj"
    else:
        raise ValueError("请输入沪深京A股代码")
    if match.group(1) and match.group(1) != market:
        raise ValueError("交易所前缀与股票代码不匹配")
    return f"{market}.{code}"


def parse_payload(payload, symbol, start, end):
    if not isinstance(payload, dict) or payload.get("rc") != 0:
        raise ProviderError("行情接口返回错误状态")
    data = payload.get("data")
    if data is None:
        raise ProviderError("接口未返回股票信息，请检查股票代码")
    if data.get("code") != symbol.split(".")[1]:
        raise ProviderError("接口返回的股票代码不一致")
    if not isinstance(data.get("name"), str) or not data["name"]:
        raise ProviderError("接口未返回股票名称")
    quotes = []
    seen = set()
    try:
        for line in data.get("klines") or []:
            cells = line.split(",")
            if len(cells) != 11:
                raise ProviderError("行情字段数量变化，请检查接口")
            day = date.fromisoformat(cells[0])
            if not start <= day <= end:
                continue
            if day in seen:
                raise ProviderError("接口返回了重复交易日期")
            seen.add(day)
            row = {"symbol": symbol, "trade_date": day}
            for field, raw in zip(NUMERIC_FIELDS, cells[1:]):
                number = None if raw in ("", "-", "--") else Decimal(raw)
                if number is not None and not number.is_finite():
                    raise ProviderError("行情包含非有限数值")
                row[field] = number
            if any(row[key] is None for key in NUMERIC_FIELDS[:6]):
                raise ProviderError("行情缺少价格或成交量额")
            if row["volume"] < 0 or row["volume"] != row["volume"].to_integral_value():
                raise ProviderError("成交量格式异常")
            row["volume"] = int(row["volume"])
            quotes.append(row)
    except (ValueError, InvalidOperation, TypeError) as exc:
        raise ProviderError("行情日期或数值无法解析") from exc
    return {"symbol": symbol, "name": data["name"], "quotes": sorted(quotes, key=lambda r: r["trade_date"])}


def fetch_daily(symbol: str, start: date, end: date):
    symbol = normalize_symbol(symbol)
    code = symbol.split(".")[1]
    market_id = "1" if symbol.startswith("sh.") else "0"
    params = {
        "secid": f"{market_id}.{code}", "klt": "101", "fqt": "0",
        "beg": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "ut": "7eea3edcaed734bea9cbfc24409ed989",
    }
    try:
        response = requests.get(URL, params=params, timeout=20, headers={
            "User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/",
        })
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise ProviderError("行情HTTP请求失败，请稍后手动重试") from exc
    return parse_payload(payload, symbol, start, end)

