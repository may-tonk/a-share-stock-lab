"""应用运行时的Excel导出功能，直接导出数据库查询结果。"""
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo

from .provider import URL, normalize_symbol
from .service import quotes

HEADERS = ["股票代码", "股票名称", "交易日期", "开盘价(元)", "收盘价(元)", "最高价(元)", "最低价(元)",
           "成交量(手)", "成交额(元)", "振幅", "涨跌幅", "涨跌额(元)", "换手率", "交易所", "复权方式", "采集时间(北京时间)"]
FIELDS = ["open", "close", "high", "low", "volume", "amount", "amplitude", "change_pct", "change_amount", "turnover"]


def export_quotes(symbol, start=None, end=None):
    symbol = normalize_symbol(symbol)
    result = quotes(symbol, start, end, limit=100_000)
    if not result["items"]:
        raise ValueError("所选区间没有已入库的行情数据")
    if result["total"] > 100_000:
        raise ValueError("单次导出上限10万行，请缩小日期范围")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "股票日线"
    sheet.merge_cells("A1:P1")
    sheet["A1"] = f"{result['items'][0]['name']}（{symbol}）日线行情 · 不复权"
    sheet["A1"].font = Font(name="微软雅黑", size=16, bold=True, color="17365D")
    sheet.row_dimensions[1].height = 30
    sheet.merge_cells("A2:P2")
    sheet["A2"] = f"数据来源：东方财富 {URL}；成交量单位为手（100股）；采集时间采用北京时间。"
    sheet["A2"].font = Font(name="微软雅黑", size=10, color="666666")
    sheet.append([])
    # 合并单元格不改变append的起始行，显式写入第4行以固定数据表位置。
    for col, header in enumerate(HEADERS, 1):
        cell = sheet.cell(4, col, header)
        cell.font = Font(name="微软雅黑", bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="244A73")
    for index, item in enumerate(result["items"], 5):
        metrics = [item[field] for field in FIELDS]
        for position in (6, 7, 9):
            if metrics[position] is not None:
                metrics[position] = metrics[position] / 100
        values = [symbol.split(".")[1], item["name"], item["trade_date"], *metrics,
                  symbol.split(".")[0], "不复权", item["fetched_at"]]
        for col, value in enumerate(values, 1):
            cell = sheet.cell(index, col, value)
            cell.font = Font(name="微软雅黑", size=11)
            cell.alignment = Alignment(vertical="center")
            if col == 1:
                cell.number_format = "@"
            elif col == 3:
                cell.number_format = "yyyy-mm-dd"
            elif col == 8:
                cell.number_format = "#,##0"
            elif col in (10, 11, 13):
                cell.number_format = "0.00%"
            elif col == 16:
                cell.number_format = "yyyy-mm-dd hh:mm:ss"
            elif 4 <= col <= 13:
                cell.number_format = "#,##0.00"
    table = Table(displayName="DailyQuotes", ref=f"A4:P{sheet.max_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    sheet.add_table(table)
    widths = [13, 15, 15, 16, 16, 16, 16, 17, 24, 13, 13, 17, 13, 11, 13, 26]
    for col, width in enumerate(widths, 1):
        sheet.column_dimensions[sheet.cell(4, col).column_letter].width = width
    sheet.freeze_panes = "D5"
    sheet.sheet_view.zoomScale = 85
    sheet.print_title_rows = "1:4"
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A3
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()

