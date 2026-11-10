import argparse
import json
from datetime import date
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="A股日线采集、MySQL增量更新与Excel导出")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="创建配置中的数据库及四张表")
    serve = commands.add_parser("serve", help="启动本地后端及接口调试页面")
    serve.add_argument("--port", type=int, default=8006)
    for action in ("collect", "update", "export"):
        cmd = commands.add_parser(action)
        cmd.add_argument("--symbol", required=True)
        cmd.add_argument("--end", type=date.fromisoformat, required=action == "collect")
        if action != "update":
            cmd.add_argument("--start", type=date.fromisoformat, required=action == "collect")
        if action == "export":
            cmd.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.command == "init-db":
        from stock_app.db import init_database
        init_database()
        result = {"status": "数据库及四张表已初始化"}
    elif args.command == "serve":
        import uvicorn
        uvicorn.run("stock_app.api:app", host="127.0.0.1", port=args.port)
        return
    elif args.command == "export":
        from stock_app.export import export_quotes
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(export_quotes(args.symbol, args.start, args.end))
        result = {"output": str(output)}
    else:
        from stock_app.service import sync, update
        result = (sync(args.symbol, args.start, args.end) if args.command == "collect"
                  else update(args.symbol, args.end))
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # 不输出连接对象、密码或配置内容。
        from stock_app.provider import ProviderError
        import pymysql
        if isinstance(exc, pymysql.MySQLError):
            raise SystemExit("MySQL操作失败，请检查.env连接配置、服务和数据库权限")
        if isinstance(exc, (ValueError, ProviderError)):
            raise SystemExit(str(exc))
        raise

