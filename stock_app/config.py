import os
import re
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DATABASE = os.getenv("MYSQL_DATABASE", "stock_lab6")
if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", DATABASE):
    raise ValueError("MYSQL_DATABASE须为字母开头的数据库名称")


def connection_options():
    password = os.getenv("MYSQL_PASSWORD")
    if password is None:
        raise ValueError("请在项目.env中设置MYSQL_PASSWORD")
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": password,
        "charset": "utf8mb4",
        "connect_timeout": 5,
    }

