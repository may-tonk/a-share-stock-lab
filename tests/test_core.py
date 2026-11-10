from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from stock_app import provider, service
from stock_app.api import app
from stock_app.provider import ProviderError, normalize_symbol, parse_payload


def sample():
    # 用于解析器测试的固定样例，不作为联网采集结果。
    return {"rc": 0, "data": {"code": "000001", "name": "测试股票", "klines": [
        "2024-10-08,13.43,12.88,13.43,12.34,5888978,7602664023.92,8.93,5.49,0.67,3.03"
    ]}}


@pytest.mark.parametrize("value,expected", [("000001", "sz.000001"), ("SH600519", "sh.600519"), ("bj.920001", "bj.920001")])
def test_symbol_selection(value, expected):
    assert normalize_symbol(value) == expected


@pytest.mark.parametrize("value", ["sh.000001", "hello", "000001;DROP TABLE stocks", "234567"])
def test_reject_invalid_symbol(value):
    with pytest.raises(ValueError):
        normalize_symbol(value)


def test_parse_daily_units_and_precision():
    result = parse_payload(sample(), "sz.000001", date(2024, 10, 8), date(2024, 10, 11))
    row = result["quotes"][0]
    assert row["volume"] == 5888978  # 手，入库不擅自转换为股
    assert row["amount"] == Decimal("7602664023.92")
    assert row["change_pct"] == Decimal("5.49")  # 接口百分数，导出时才除以100
    assert row["trade_date"] == date(2024, 10, 8)


def test_provider_empty_data_and_invalid_response():
    data = sample()
    data["data"]["klines"] = []
    assert parse_payload(data, "sz.000001", date(2024, 10, 8), date(2024, 10, 11))["quotes"] == []
    with pytest.raises(ProviderError):
        parse_payload({"rc": 1}, "sz.000001", date(2024, 10, 8), date(2024, 10, 11))


def test_field_drift_is_visible():
    data = sample()
    data["data"]["klines"][0] += ",unexpected"
    with pytest.raises(ProviderError, match="字段数量"):
        parse_payload(data, "sz.000001", date(2024, 10, 8), date(2024, 10, 11))


def test_insert_changed_and_unchanged_count():
    row = parse_payload(sample(), "sz.000001", date(2024, 10, 8), date(2024, 10, 11))["quotes"][0]
    assert service.classify({}, [row]) == (1, 0, 0)
    assert service.classify({row["trade_date"]: row}, [row]) == (0, 0, 1)
    old = dict(row, close=Decimal("12.00"))
    assert service.classify({row["trade_date"]: old}, [row]) == (0, 1, 0)


def test_daily_cutoff_uses_china_time(monkeypatch):
    monkeypatch.setattr(provider, "china_now", lambda: datetime(2026, 11, 10, 9))
    assert provider.daily_cutoff() == date(2026, 11, 9)
    monkeypatch.setattr(provider, "china_now", lambda: datetime(2026, 11, 10, 18))
    assert provider.daily_cutoff() == date(2026, 11, 10)


def test_update_uses_saved_trade_date_with_overlap(monkeypatch):
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, *args): pass
        def fetchone(self):
            return {"first_trade_date": date(2024, 1, 1), "latest_trade_date": date(2024, 10, 18)}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def cursor(self): return Cursor()
    monkeypatch.setattr(service, "connection", Connection)
    monkeypatch.setattr(service, "sync", lambda *args: args)
    assert service.update("000001", date(2024, 10, 25)) == ("sz.000001", date(2024, 10, 4), date(2024, 10, 25))


def test_api_date_validation_before_network():
    client = TestClient(app)
    assert client.post("/api/collect", json={"symbol": "000001", "start_date": "bad", "end_date": "2024-10-11"}).status_code == 422
    response = client.post("/api/collect", json={"symbol": "000001", "start_date": "2024-10-12", "end_date": "2024-10-11"})
    assert response.status_code == 400

