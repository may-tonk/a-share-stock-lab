"""真实接口→HTTP处理→MySQL→查询→Excel的验证，重复执行不会重复入库。"""
import json
import sys
from datetime import date
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from openpyxl import load_workbook

from stock_app.api import app
from stock_app.config import ROOT
from stock_app.db import connection, init_database


def require(response):
    assert response.status_code == 200, response.text
    return response.json()


def main():
    init_database()
    client = TestClient(app)
    assert require(client.get("/api/health"))["database"] == "mysql"
    first = require(client.post("/api/collect", json={
        "symbol": "000001", "start_date": "2024-10-08", "end_date": "2024-10-11"}))
    assert first["fetched"] == 4
    extended = require(client.post("/api/update", json={"symbol": "000001", "end_date": "2024-10-18"}))
    assert extended["state"]["total_rows"] >= 9
    repeated = require(client.post("/api/update", json={"symbol": "000001", "end_date": "2024-10-18"}))
    assert repeated["inserted"] == 0 and repeated["updated"] == 0
    weekend = require(client.post("/api/collect", json={
        "symbol": "000001", "start_date": "2024-10-19", "end_date": "2024-10-20"}))
    assert weekend["status"] == "no_data"
    assert weekend["state"]["latest_trade_date"] == repeated["state"]["latest_trade_date"]
    sample_filter = {"symbol": "000001", "start_date": "2024-10-08", "end_date": "2024-10-18"}
    page = require(client.get("/api/quotes", params={**sample_filter, "limit": 3, "offset": 3}))
    assert page["total"] == 9 and len(page["items"]) == 3
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS n,COUNT(DISTINCT trade_date) AS unique_n FROM daily_quotes WHERE symbol='sz.000001' AND trade_date BETWEEN '2024-10-08' AND '2024-10-18'")
        counts = cursor.fetchone()
    assert counts["n"] == counts["unique_n"] == 9
    export = client.get("/api/export", params=sample_filter)
    assert export.status_code == 200, export.text
    workbook = load_workbook(BytesIO(export.content), data_only=True)
    sheet = workbook["股票日线"]
    assert sheet.max_row == 13
    assert sheet["A5"].value == "000001" and sheet["A5"].data_type == "s"
    assert sheet["B5"].value == "平安银行"
    assert sheet["C5"].value.date() == date(2024, 10, 8)
    assert abs(sheet["K5"].value - 0.0549) < 1e-10
    assert sheet["K5"].number_format == "0.00%"
    assert sheet["H5"].value == 5888978
    rows = require(client.get("/api/quotes", params=sample_filter))
    output = ROOT / "outputs" / "采集验证"
    output.mkdir(parents=True, exist_ok=True)
    (output / "平安银行_20241008_20241018.xlsx").write_bytes(export.content)
    (output / "行情样例.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {"symbol": "sz.000001", "name": "平安银行", "first": first,
              "extended": extended, "repeated": repeated, "weekend": weekend,
              "database_counts": counts, "excel_data_rows": 9,
              "checked": ["MySQL连接", "真实HTTP采集", "扩大日期范围", "重复运行不重复插入", "周末空数据不推进进度", "分页查询", "Excel代码前导零、日期及百分比"]}
    (output / "验证结果.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

