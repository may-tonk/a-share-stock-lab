from datetime import timedelta

from .db import connection
from .provider import NUMERIC_FIELDS, china_now, daily_cutoff, fetch_daily, normalize_symbol


def classify(existing, incoming):
    """精确区分新增、数值变化和未变化，不依赖MySQL受影响行数的特殊语义。"""
    inserted = updated = unchanged = 0
    for row in incoming:
        old = existing.get(row["trade_date"])
        if old is None:
            inserted += 1
        elif any(old[key] != row[key] for key in NUMERIC_FIELDS):
            updated += 1
        else:
            unchanged += 1
    return inserted, updated, unchanged


def sync(symbol, start, end):
    symbol = normalize_symbol(symbol)
    if start > end:
        raise ValueError("开始日期不能晚于结束日期")
    effective_end = min(end, daily_cutoff())
    if start > effective_end:
        raise ValueError("所选区间尚无可采集的完整日线日期")
    started = china_now()
    try:
        result = fetch_daily(symbol, start, effective_end)
    except Exception as exc:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("""INSERT INTO sync_logs
                (symbol,start_date,end_date,status,message,started_at,finished_at)
                VALUES (%s,%s,%s,'failed',%s,%s,%s)""",
                (symbol, start, effective_end, str(exc)[:500], started, china_now()))
        raise
    rows = result["quotes"]
    now = china_now()
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("""INSERT INTO stocks (symbol,code,market,name,created_at,updated_at)
            VALUES (%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE name=VALUES(name),updated_at=VALUES(updated_at)""",
            (symbol, symbol.split(".")[1], symbol.split(".")[0], result["name"], now, now))
        cursor.execute("SELECT * FROM daily_quotes WHERE symbol=%s AND trade_date BETWEEN %s AND %s",
                       (symbol, start, effective_end))
        existing = {r["trade_date"]: r for r in cursor.fetchall()}
        inserted, updated, unchanged = classify(existing, rows)
        columns = ("symbol", "trade_date", *NUMERIC_FIELDS, "fetched_at")
        if rows:
            cursor.executemany(
                f"INSERT INTO daily_quotes ({','.join('`'+c+'`' for c in columns)}) VALUES ({','.join(['%s']*len(columns))}) "
                + "ON DUPLICATE KEY UPDATE " + ",".join(f"`{c}`=VALUES(`{c}`)" for c in (*NUMERIC_FIELDS, "fetched_at")),
                [tuple(row[c] for c in columns[:-1]) + (now,) for row in rows],
            )
            cursor.execute("SELECT MIN(trade_date) AS first_day, MAX(trade_date) AS last_day, COUNT(*) AS total FROM daily_quotes WHERE symbol=%s", (symbol,))
            stats = cursor.fetchone()
            cursor.execute("""INSERT INTO sync_state (symbol,first_trade_date,latest_trade_date,total_rows,last_success_at)
                VALUES (%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE first_trade_date=VALUES(first_trade_date),
                latest_trade_date=VALUES(latest_trade_date),total_rows=VALUES(total_rows),last_success_at=VALUES(last_success_at)""",
                (symbol, stats["first_day"], stats["last_day"], stats["total"], now))
        status = "success" if rows else "no_data"
        cursor.execute("""INSERT INTO sync_logs
            (symbol,start_date,end_date,status,fetched_rows,inserted_rows,updated_rows,unchanged_rows,started_at,finished_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (symbol,start,effective_end,status,len(rows),inserted,updated,unchanged,started,now))
        cursor.execute("SELECT * FROM sync_state WHERE symbol=%s", (symbol,))
        state = cursor.fetchone()
    return {"symbol": symbol, "name": result["name"], "start_date": start, "requested_end_date": end,
            "effective_end_date": effective_end, "fetched": len(rows), "inserted": inserted,
            "updated": updated, "unchanged": unchanged, "status": status, "state": state}


def update(symbol, end=None):
    symbol = normalize_symbol(symbol)
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT * FROM sync_state WHERE symbol=%s", (symbol,))
        state = cursor.fetchone()
    if not state:
        raise ValueError("该股票还没有历史数据，请先指定日期范围进行首次采集")
    # 回查14个自然日用于覆盖近期修正，不将周末简单当作漏数。
    start = max(state["first_trade_date"], state["latest_trade_date"] - timedelta(days=14))
    return sync(symbol, start, end or daily_cutoff())


def list_stocks():
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("""SELECT s.*, t.first_trade_date, t.latest_trade_date, t.total_rows, t.last_success_at
            FROM stocks s LEFT JOIN sync_state t ON t.symbol=s.symbol ORDER BY s.symbol""")
        return cursor.fetchall()


def set_tracked(symbol, tracked):
    symbol = normalize_symbol(symbol)
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT symbol FROM stocks WHERE symbol=%s", (symbol,))
        if not cursor.fetchone():
            raise ValueError("股票尚未采集")
        cursor.execute("UPDATE stocks SET tracked=%s,updated_at=%s WHERE symbol=%s", (tracked, china_now(), symbol))
    return {"symbol": symbol, "tracked": tracked}


def quotes(symbol, start=None, end=None, limit=100, offset=0):
    symbol = normalize_symbol(symbol)
    if start and end and start > end:
        raise ValueError("开始日期不能晚于结束日期")
    where = ["q.symbol=%s"]
    args = [symbol]
    for day, condition in ((start, "q.trade_date >= %s"), (end, "q.trade_date <= %s")):
        if day:
            where.append(condition)
            args.append(day)
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM daily_quotes q WHERE " + " AND ".join(where), args)
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT q.*,s.name FROM daily_quotes q JOIN stocks s ON s.symbol=q.symbol WHERE "
                       + " AND ".join(where) + " ORDER BY q.trade_date LIMIT %s OFFSET %s", (*args, limit, offset))
        return {"total": total, "items": cursor.fetchall()}


def logs(limit=10, offset=0):
    if not 1 <= limit <= 50 or offset < 0:
        raise ValueError("采集记录每次可读取1至50条，偏移量不能为负数")
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS total FROM sync_logs")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT * FROM sync_logs ORDER BY id DESC LIMIT %s OFFSET %s", (limit, offset))
        return {"total": total, "items": cursor.fetchall()}

