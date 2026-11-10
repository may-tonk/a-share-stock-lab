import { ChevronLeft, ChevronRight, FileSpreadsheet, History } from 'lucide-react'
import type { Quote, SyncLog } from './types'

export const number = (value: number | null | undefined, digits = 2) => value == null ? '—' : value.toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
export const changeClass = (value: number | null | undefined) => value == null || value === 0 ? '' : value > 0 ? 'positive' : 'negative'
export const signed = (value: number | null | undefined, suffix = '') => value == null ? '—' : `${value > 0 ? '+' : ''}${number(value)}${suffix}`
export const timestamp = (value: string | null) => value ? value.replace('T', ' ').split('.')[0] : '尚未采集'

export function QuoteTable({ rows, total, page, pageSize, loading, exporting, disabled, onPage, onExport }: {
  rows: Quote[]; total: number; page: number; pageSize: number; loading: boolean; exporting: boolean; disabled: boolean;
  onPage: (page: number) => void; onExport: () => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize))
  return <section className="panel table-panel" aria-labelledby="detail-title">
    <div className="panel-heading"><div><h2 id="detail-title">日线数据明细 <span className="count-badge">{total.toLocaleString()} 条</span></h2><p>价格单位：元 / 股 · 成交量：手 · 成交额：元</p></div>
      <button className="button button-small" onClick={onExport} disabled={!total || disabled || loading}><FileSpreadsheet size={15} />{exporting ? '正在导出…' : '导出 Excel'}</button></div>
    <div className="table-scroll" aria-busy={loading}><table><thead><tr>
      {['交易日期', '开盘', '收盘', '最高', '最低', '涨跌幅', '成交量（手）', '成交额（元）', '振幅', '涨跌额', '换手率'].map(label => <th key={label}>{label}</th>)}
    </tr></thead><tbody>
      {loading ? <tr><td colSpan={11} className="table-empty">正在读取日线数据…</td></tr>
        : rows.length ? rows.map(row => <tr key={row.trade_date}>
          <td>{row.trade_date}</td><td>{number(row.open)}</td><td className="price-cell">{number(row.close)}</td><td>{number(row.high)}</td><td>{number(row.low)}</td>
          <td className={changeClass(row.change_pct)}>{signed(row.change_pct, '%')}</td><td>{number(row.volume, 0)}</td><td>{number(row.amount)}</td>
          <td>{number(row.amplitude)}{row.amplitude == null ? '' : '%'}</td><td className={changeClass(row.change_amount)}>{signed(row.change_amount)}</td><td>{number(row.turnover)}{row.turnover == null ? '' : '%'}</td>
        </tr>) : <tr><td colSpan={11} className="table-empty">暂无记录，请采集数据或调整日期范围。</td></tr>}
    </tbody></table></div>
    <div className="table-footer"><span>{total ? `显示第 ${page * pageSize + 1}–${Math.min((page + 1) * pageSize, total)} 条，共 ${total.toLocaleString()} 条` : '共 0 条记录'}</span>
      <div className="pagination"><button aria-label="上一页" disabled={page === 0 || loading} onClick={() => onPage(page - 1)}><ChevronLeft size={16} /></button><span>{page + 1} / {pages}</span><button aria-label="下一页" disabled={page + 1 >= pages || loading} onClick={() => onPage(page + 1)}><ChevronRight size={16} /></button></div>
    </div>
  </section>
}

export function LogsTable({ logs, compact = false, onMore, pagination }: {
  logs: SyncLog[]; compact?: boolean; onMore?: () => void;
  pagination?: { total: number; page: number; pageSize: number; loading: boolean; onPage: (page: number) => void };
}) {
  // 即使调用方传入更多记录，也只渲染当前页上限。
  const visible = logs.slice(0, compact ? 3 : 10)
  const pages = Math.max(1, Math.ceil((pagination?.total || 0) / 10))
  return <section className="panel logs-panel"><div className="panel-heading"><div><h2><History size={17} />{compact ? '最近采集记录' : '采集记录'}</h2><p>每次运行的新增、修正和未变化记录</p></div>{compact && <button className="text-button" onClick={onMore}>查看全部 <ChevronRight size={14} /></button>}</div>
    <div className="table-scroll"><table><thead><tr>{['运行时间（北京时间）', '股票', '请求区间', '状态', '新增', '修正', '未变化'].map(label => <th key={label}>{label}</th>)}</tr></thead><tbody>
      {pagination?.loading ? <tr><td colSpan={7} className="table-empty">正在读取采集记录…</td></tr> : visible.length ? visible.map(log => <tr key={log.id}><td>{timestamp(log.started_at)}</td><td>{log.symbol}</td><td>{log.start_date} — {log.end_date}</td><td><span className={`status-tag ${log.status}`} title={log.message || undefined}>{log.status === 'success' ? '已完成' : log.status === 'no_data' ? '暂无新数据' : '采集失败'}</span>{log.message && <small className="log-error">{log.message}</small>}</td><td>{log.inserted_rows}</td><td>{log.updated_rows}</td><td>{log.unchanged_rows}</td></tr>)
        : <tr><td colSpan={7} className="table-empty">完成首次采集后，运行记录会显示在这里。</td></tr>}
    </tbody></table></div>
    {!compact && pagination && <div className="table-footer"><span>{pagination.total ? `共 ${pagination.total.toLocaleString()} 条记录，每页最多 10 条` : '暂无采集记录'}</span>
      <div className="pagination"><button aria-label="采集记录上一页" disabled={pagination.page === 0 || pagination.loading} onClick={() => pagination.onPage(pagination.page - 1)}><ChevronLeft size={16} /></button><span>{pagination.page + 1} / {pages}</span><button aria-label="采集记录下一页" disabled={pagination.page + 1 >= pages || pagination.loading} onClick={() => pagination.onPage(pagination.page + 1)}><ChevronRight size={16} /></button></div>
    </div>}
  </section>
}
