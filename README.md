# A股日线采集与增量更新实验

已完成React + TypeScript行情工作台与FastAPI后端。正式存储使用MySQL，Excel为按需导出的查看文件。前端页面显示数据库中的真实行情。

## 首次安装（GitHub源码或源码压缩包）

需要Python 3.11、Node.js 24和MySQL 8.0。源码不包含数据库密码、已采集的数据、Python虚拟环境、node_modules或前端构建产物。

在项目根目录打开PowerShell，按顺序执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
# 仅首次复制；已有.env时请保留原文件。
Copy-Item .env.example .env
```

编辑本地`.env`，设置自己的MySQL连接信息和密码，然后执行：

```powershell
.\.venv\Scripts\python.exe main.py init-db
cd frontend
npm.cmd ci
npm.cmd run build
cd ..
.\启动项目.cmd
```

`init-db`会创建`.env`指定的数据库和表，所用MySQL账号需具备相应权限。打开 http://127.0.0.1:8006 ，点击“添加股票”开始首次采集。

## 打开工作台

双击项目根目录的`启动项目.cmd`即可启动。也可以在项目目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\启动项目.ps1
```

打开 http://127.0.0.1:8006 。完成首次安装后，启动时仅需运行后端，不需要同时启动两个服务。若前端构建不存在，启动脚本会尝试安装并构建前端；Python环境和本地配置仍需按首次安装步骤准备。关闭运行窗口或按Ctrl+C停止服务。启动脚本不会自动打开浏览器。

页面操作：

1. 点击“添加股票”，输入用户选择的股票代码和日期，采集后自动加入自选列表；也可点击左侧已有股票。
2. 修改日期后点击“查询”，只查询已保存的数据；点击“采集所选区间”才会向行情接口下载或补采。
3. “增量更新”根据本地最新交易日期回查近期数据，并更新至表单中的结束日期。需要更新到最近时，请将结束日期改为最近日期。
4. 切换收盘价、成交量图表，浏览分页明细，或按当前已查询的日期范围导出Excel。
5. “暂停跟踪”将股票标记为暂停，不删除历史，也不禁止手动采集；当前没有自动定时任务。
6. 工作台仅请求并显示最近3条采集记录。“采集记录”页面每页最多10条，点击翻页才请求对应页，不在前端累积历史记录。数据库保留全部历史。

图表最多展示所选范围的前1000条日线，超出时页面明确提示；明细表使用后端分页，可查看完整结果。添加新股票按代码输入，左侧搜索仅筛选已采集股票名称和代码。

## 前端开发和重新构建

需要Node.js 22.12及以上（本机使用24）。开发模式下先运行后端，再执行：

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

开发地址 http://127.0.0.1:5173 ，Vite会将/api请求转发给8006端口的后端。更新前端代码后执行`npm.cmd run build`，再刷新8006页面即可看到新构建。前端从不读取MySQL密码或.env文件。React源码位于frontend/src，依赖版本由package-lock.json锁定。

## 运行环境

Python 3.11、MySQL 8.0。建议使用独立`.venv`环境。本地`.env`保存连接配置，不应提交或分发。也可以使用uv安装依赖：

```powershell
uv venv .venv --python 3.11
uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt
# 在.env中填写自己的数据库配置；已有配置时不要覆盖。
.\.venv\Scripts\python.exe main.py init-db
.\.venv\Scripts\python.exe main.py serve
```

也可使用`启动后端.ps1`。服务只监听本机。打开 http://127.0.0.1:8006/docs 使用接口调试页面；前端构建存在时，根地址提供React页面。

## 一只股票的小范围测试

示例选择平安银行000001，2024-10-08至2024-10-18。股票代码和日期均为输入参数，程序没有固定的采集名单。

```powershell
.\.venv\Scripts\python.exe main.py collect --symbol 000001 --start 2024-10-08 --end 2024-10-11
.\.venv\Scripts\python.exe main.py update --symbol 000001 --end 2024-10-18
.\.venv\Scripts\python.exe main.py update --symbol 000001 --end 2024-10-18
.\.venv\Scripts\python.exe main.py export --symbol 000001 --start 2024-10-08 --end 2024-10-18 --output outputs\平安银行.xlsx
```

新建空库时，上述首次采集应获取4条，扩大范围新增5条，总计9条；再次更新新增0条。示例外的历史区间可使用collect明确补采。

## 接口

| 方法与路径 | 用途 |
| --- | --- |
| GET /api/health | 检查MySQL连接和日线截止日期 |
| POST /api/collect | 指定股票及起止日期下载或补采 |
| POST /api/update | 根据已保存日期更新一只股票 |
| GET /api/stocks | 查询已采集股票及进度 |
| PATCH /api/stocks/{symbol}/tracking | 启用或停用列表中的股票，保留历史数据 |
| POST /api/update-tracked | 顺序更新列表中已启用的股票 |
| GET /api/quotes | 按股票及日期查询，带分页 |
| GET /api/logs | 分页查看采集记录，返回total和items；默认10条，单次最多50条，offset指定偏移量 |
| GET /api/export | 按股票及日期导出Excel |

首次采集请求：

```json
{"symbol":"000001","start_date":"2024-10-08","end_date":"2024-10-11"}
```

更新请求中的end_date可省略，省略时更新至默认日线截止日期：

```json
{"symbol":"000001","end_date":"2024-10-18"}
```

## 数据与更新规则

- 数据源：东方财富历史行情HTTP入口 https://push2his.eastmoney.com/api/qt/stock/kline/get 。参数映射参考 https://github.com/akfamily/akshare/blob/main/akshare/stock/quote/stock_hist_em.py 。当前代码直接请求该入口，不依赖AKShare安装。
- 仅采集日线、不复权数据。行情包括交易日期、开高低收、成交量（手）、成交额（元）、振幅、涨跌幅、涨跌额、换手率。
- 股票代码支持六位代码或sh./sz./bj.前缀。当前真实测试只覆盖深圳000001；沪市、北交所和名称搜索留待后续验证/完善，当前未实现全市场股票搜索目录。
- 更新依据是每只股票实际入库的最新交易日期，采集时间只作为审计信息。
- 增量请求回查14个自然日，最早不超过本地最早交易日期。主键为股票加交易日期，重复运行更新原行，不重复新增。
- first_trade_date和latest_trade_date表示已存数据的最小、最大日期，不保证中间连续；历史中段缺失通过collect指定区间补采，第一版没有自动历史缺口扫描。
- 行情入库、进度和成功日志在同一次事务中提交。网络出错记录失败日志，空行情记录no_data，均不推进交易日期进度。
- 全部采集时间按北京时间记录。北京时间18点之前，默认最多采集到昨天；18点之后尝试当日日线，是否发布以接口返回为准。18点为实验的简化截点，不是数据源时效承诺。
- 不配置定时任务，当前由命令或API手动触发。按需求暂不实现自动重试、复杂断流恢复、代理和备用源。也未实现多任务并发采集，请顺序使用。
- 每次Excel导出重新查询数据库，不将Excel当作同步进度依据；单次最多10万行，超过时提示缩小范围，不截断。股票代码为文本、日期为日期值、百分比为数值并应用百分比格式。

## 数据表

`schema.sql`包含stocks（股票与采集开关）、daily_quotes（行情）、sync_state（已存进度）、sync_logs（采集日志）四张表。初始化只创建项目指定数据库及不存在的表，不删除已有数据。

## 验证

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\verify_live.py
```

单元测试不请求网络、不写数据库。真实验证脚本会使用当前.env连接MySQL并采集示例股票，核验示例日期区间的9条真实行情、日志、Excel样例和JSON验证记录；其他已采集日期不受影响，重复执行不会删除或清空数据。

## 源码打包

项目提供`scripts/package_release.py`，从Git提交生成脱敏源码ZIP，不把本地运行文件打入压缩包：

```powershell
.\.venv\Scripts\python.exe scripts\package_release.py --check
.\.venv\Scripts\python.exe scripts\package_release.py
```

`--check`检查Git暂存区的发布文件和常见凭据特征；正式打包从HEAD提交读取文件，检查后输出到`releases/`，同时生成SHA256校验文件。压缩包与仓库源码一致，需要依照首次安装步骤配置后运行。

`.env`及其本地变体、数据库内容、采集结果、日志、依赖目录、缓存、压缩包和原始课程截图均不纳入源码发布；`.env.example`只保留占位配置。

