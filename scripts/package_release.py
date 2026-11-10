"""从审核过的Git提交打包源码，不复制本地配置或运行数据。"""
import argparse
import hashlib
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "a-share-stock-lab/"
ROOT_FILES = {
    ".gitignore", ".env.example", "README.md", "main.py", "schema.sql",
    "requirements.txt", "requirements-dev.txt", "启动项目.cmd", "启动项目.ps1", "启动后端.ps1",
}
SOURCE_DIRS = {"stock_app", "tests", "scripts"}
FRONT_FILES = {"package.json", "package-lock.json", "index.html", "tsconfig.json", "vite.config.ts"}
PATTERNS = [
    re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(rb"\bsk-[A-Za-z0-9_-]{24,}\b"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"https?://[^\s/]+:[^\s/@]+@"),
]


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def allowed(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return False
    if name in ROOT_FILES:
        return True
    if path.parts[0] in SOURCE_DIRS:
        return path.suffix == ".py" and "__pycache__" not in path.parts
    if path.parts[0] == "frontend":
        return (len(path.parts) == 2 and path.name in FRONT_FILES) or (
            len(path.parts) >= 3 and path.parts[1] == "src" and path.suffix in {".ts", ".tsx", ".css"}
        )
    return False


def check(name, data, secrets):
    if not allowed(name):
        raise RuntimeError(f"发布清单中存在未允许的文件：{name}")
    if any(pattern.search(data) for pattern in PATTERNS):
        raise RuntimeError(f"发现疑似凭据，请人工检查文件：{name}")
    if any(secret in data for secret in secrets):
        raise RuntimeError(f"发现与本地敏感配置相同的内容，请检查文件：{name}")
    if b"C:" + b"\\Users\\" in data or b"C:" + b"/Users/" in data:
        raise RuntimeError(f"发现本机用户目录，请检查文件：{name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="仅检查Git暂存区，不生成压缩包")
    args = parser.parse_args()
    top = Path(git("rev-parse", "--show-toplevel").decode().strip()).resolve()
    if top != ROOT:
        raise RuntimeError("请先在本项目根目录创建独立Git仓库")
    values = dotenv_values(ROOT / ".env") if (ROOT / ".env").exists() else {}
    secrets = [value.encode() for key, value in values.items() if value and len(value) >= 4
               and any(part in key.upper() for part in ("PASSWORD", "SECRET", "TOKEN", "API_KEY"))]
    if args.check:
        names = git("ls-files", "-z").decode().split("\0")
        files = [(name, git("show", f":{name}")) for name in names if name]
    else:
        names = git("ls-tree", "-r", "--name-only", "-z", "HEAD").decode().split("\0")
        files = [(name, git("show", f"HEAD:{name}")) for name in names if name]
    if not files:
        raise RuntimeError("没有可发布的源码文件")
    for name, data in files:
        check(name, data, secrets)
    print(f"发布检查通过：{len(files)}个源码文件，未发现被禁止的文件或所检查的凭据特征。")
    if args.check:
        return
    revision = git("rev-parse", "--short=8", "HEAD").decode().strip()
    day = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")
    output = ROOT / "releases" / f"a-share-stock-lab-source-{day}-{revision}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in files:
            archive.writestr(PREFIX + name, data)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(files)
        for member in archive.infolist():
            check(member.filename.removeprefix(PREFIX), archive.read(member), secrets)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    print(f"压缩包：{output}")
    print(f"大小：{output.stat().st_size}字节；SHA256：{digest}")


if __name__ == "__main__":
    main()
