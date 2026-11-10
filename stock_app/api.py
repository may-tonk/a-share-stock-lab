from datetime import date
from io import BytesIO

import pymysql
from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import service
from .db import connection
from .config import ROOT
from .export import export_quotes
from .provider import ProviderError, daily_cutoff, normalize_symbol

app = FastAPI(title="A股日线采集实验", version="0.2.0", description="React行情工作台：自选股票、日线采集、MySQL增量更新及Excel导出。")


@app.exception_handler(ValueError)
def value_error(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(ProviderError)
def provider_error(request: Request, exc: ProviderError):
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(pymysql.MySQLError)
def database_error(request: Request, exc: pymysql.MySQLError):
    return JSONResponse(status_code=503, content={"detail": "MySQL操作失败，请检查本地.env配置、数据库服务和建表情况"})


class CollectRequest(BaseModel):
    symbol: str = Field(description="用户选择的股票代码，例如000001或sz.000001")
    start_date: date
    end_date: date


class UpdateRequest(BaseModel):
    symbol: str
    end_date: date | None = None


class TrackingRequest(BaseModel):
    tracked: bool


@app.get("/api/health", tags=["状态"])
def health():
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT 1")
    return {"status": "ok", "database": "mysql", "frequency": "daily", "adjustment": "none", "daily_cutoff": daily_cutoff()}


@app.post("/api/collect", tags=["采集"])
def collect(body: CollectRequest):
    return jsonable_encoder(service.sync(body.symbol, body.start_date, body.end_date))


@app.post("/api/update", tags=["采集"])
def update(body: UpdateRequest):
    return jsonable_encoder(service.update(body.symbol, body.end_date))


@app.get("/api/stocks", tags=["股票"])
def stocks():
    return service.list_stocks()


@app.patch("/api/stocks/{symbol}/tracking", tags=["股票"])
def tracking(symbol: str, body: TrackingRequest):
    return service.set_tracked(symbol, body.tracked)


@app.post("/api/update-tracked", tags=["采集"])
def update_tracked(end_date: date | None = None):
    # 第一版顺序更新；列表由用户实际采集和启停选择决定。
    return [service.update(stock["symbol"], end_date) for stock in service.list_stocks()
            if stock["tracked"] and stock["latest_trade_date"]]


@app.get("/api/quotes", tags=["数据"])
def quotes(symbol: str, start_date: date | None = None, end_date: date | None = None,
           limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    return service.quotes(symbol, start_date, end_date, limit, offset)


@app.get("/api/logs", tags=["数据"])
def logs(limit: int = Query(10, ge=1, le=50), offset: int = Query(0, ge=0)):
    return service.logs(limit, offset)


@app.get("/api/export", tags=["数据"])
def export(symbol: str, start_date: date | None = None, end_date: date | None = None):
    content = export_quotes(symbol, start_date, end_date)
    filename = f"{normalize_symbol(symbol)}_daily.xlsx"
    return StreamingResponse(BytesIO(content), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# 构建后同源提供React页面，数据库配置始终只由后端读取。
frontend_dist = ROOT / "frontend" / "dist"
if frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

