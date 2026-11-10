from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from .config import DATABASE, ROOT, connection_options


@contextmanager
def connection():
    conn = pymysql.connect(**connection_options(), database=DATABASE, cursorclass=DictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    conn = pymysql.connect(**connection_options())
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DATABASE}` CHARACTER SET utf8mb4")
            cursor.execute(f"USE `{DATABASE}`")
            for statement in (ROOT / "schema.sql").read_text(encoding="utf-8").split(";"):
                if statement.strip():
                    cursor.execute(statement)
        conn.commit()
    finally:
        conn.close()

