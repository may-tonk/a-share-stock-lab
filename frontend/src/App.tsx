import { useCallback, useEffect, useState } from 'react'
import { Activity, ArrowDownToLine, ArrowRight, CalendarDays, Check, CircleAlert, Database, FolderClock, Info, LayoutDashboard, ListFilter, Pause, Play, Plus, RefreshCw, Search, Sprout, TrendingUp, X } from 'lucide-react'
import { api } from './api'
import { changeClass, LogsTable, number, QuoteTable, signed, timestamp } from './DataTables'
import PriceChart from './PriceChart'
import StockDialog from './StockDialog'
import type { DateRange, Health, LogPage, QuotePage, Stock, SyncLog, SyncResult } from './types'

const PAGE_SIZE = 10
const emptyPage: QuotePage = { total: 0, items: [] }
const messageOf = (error: unknown) => error instanceof Error ? error.message : '操作失败，请重试。'
function defaultRange(end?: string): DateRange {
  const last = end || new Date().toLocaleDateString('sv-SE', { timeZone: 'Asia/Shanghai' })
  const start = new Date(last + 'T12:00:00Z')
  start.setUTCDate(start.getUTCDate() - 30)
  return { start: start.toISOString().slice(0, 10), end: last }
}

export default function App() {
  const [view, setView] = useState<'workspace' | 'history'>('workspace')
  const [stocks, setStocks] = useState<Stock[]>([])
  const [logs, setLogs] = useState<SyncLog[]>([])
  const [logPage, setLogPage] = useState(0)
  const [logData, setLogData] = useState<LogPage>({ total: 0, items: [] })
  const [logsLoading, setLogsLoading] = useState(false)
  const [health, setHealth] = useState<Health | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [range, setRange] = useState<DateRange>(() => defaultRange())
  const [applied, setApplied] = useState<DateRange>(range)
  const [series, setSeries] = useState<QuotePage>(emptyPage)
  const [table, setTable] = useState<QuotePage>(emptyPage)
  const [page, setPage] = useState(0)
  const [version, setVersion] = useState(0)
  const [initializing, setInitializing] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [chartLoading, setChartLoading] = useState(false)
  const [tableLoading, setTableLoading] = useState(false)
  const [dialog, setDialog] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const active = stocks.find(stock => stock.symbol === selected)

  const chooseStock = useCallback((stock: Stock) => {
    const nextRange = stock.first_trade_date && stock.latest_trade_date
      ? { start: stock.first_trade_date, end: stock.latest_trade_date } : defaultRange()
    setSelected(stock.symbol); setRange(nextRange); setApplied(nextRange); setPage(0)
    setSeries(emptyPage); setTable(emptyPage); setView('workspace')
  }, [])

  const refreshOverview = useCallback(async (signal?: AbortSignal) => {
    const [status, list, history] = await Promise.all([api.health(signal), api.stocks(signal), api.logs(3, 0, signal)])
    setHealth(status); setStocks(list); setLogs(history.items)
    return list
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    refreshOverview(controller.signal).then(list => {
      if (!controller.signal.aborted && list.length) chooseStock(list.find(stock => stock.tracked) || list[0])
    }).catch(error => { if (!controller.signal.aborted) setNotice({ kind: 'error', text: messageOf(error) }) })
      .finally(() => { if (!controller.signal.aborted) setInitializing(false) })
    return () => controller.abort()
  }, [chooseStock, refreshOverview])

  useEffect(() => {
    if (view !== 'history') return
    const controller = new AbortController()
    setLogsLoading(true)
    api.logs(10, logPage * 10, controller.signal)
      .then(data => { if (!controller.signal.aborted) setLogData(data) })
      .catch(error => {
        if (!controller.signal.aborted) {
          setLogData({ total: 0, items: [] }); setLogPage(0)
          setNotice({ kind: 'error', text: messageOf(error) })
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLogsLoading(false) })
    return () => controller.abort()
  }, [view, logPage, version])

  useEffect(() => {
    if (!selected) return
    const controller = new AbortController()
    setChartLoading(true); setSeries(emptyPage)
    api.quotes(selected, applied, 1000, 0, controller.signal).then(data => { if (!controller.signal.aborted) setSeries(data) })
      .catch(error => { if (!controller.signal.aborted) setNotice({ kind: 'error', text: messageOf(error) }) })
      .finally(() => { if (!controller.signal.aborted) setChartLoading(false) })
    return () => controller.abort()
  }, [selected, applied, version])

  useEffect(() => {
    if (!selected) return
    const controller = new AbortController()
    setTableLoading(true)
    api.quotes(selected, applied, PAGE_SIZE, page * PAGE_SIZE, controller.signal)
      .then(data => { if (!controller.signal.aborted) setTable(data) })
      .catch(error => { if (!controller.signal.aborted) { setTable(emptyPage); setNotice({ kind: 'error', text: messageOf(error) }) } })
      .finally(() => { if (!controller.signal.aborted) setTableLoading(false) })
    return () => controller.abort()
  }, [selected, applied, page, version])

  const announceResult = (result: SyncResult) => {
    const cutoff = result.effective_end_date !== result.requested_end_date ? `；完整日线采集至 ${result.effective_end_date}` : ''
    setNotice({ kind: 'success', text: result.status === 'no_data'
      ? `${result.name}：所选区间暂无行情，同步进度保持不变。${cutoff}`
      : `${result.name}：新增 ${result.inserted} 条，修正 ${result.updated} 条，未变化 ${result.unchanged} 条${cutoff}。` })
  }

  const validateRange = () => {
    if (!range.start || !range.end || range.start > range.end) {
      setNotice({ kind: 'error', text: '请选择有效日期，开始日期不能晚于结束日期。' }); return false
    }
    return true
  }

  const collect = async (symbol: string, dates: DateRange) => {
    setBusy('collect'); setNotice(null)
    try {
      const result = await api.collect(symbol, dates)
      const list = await refreshOverview()
      const stock = list.find(item => item.symbol === result.symbol)
      if (stock) { setSelected(stock.symbol); setRange(dates); setApplied(dates); setPage(0) }
      setVersion(value => value + 1); announceResult(result); setDialog(false); setView('workspace')
    } finally { setBusy(null) }
  }

  const syncSelected = async (mode: 'collect' | 'update') => {
    if (!selected || !validateRange()) return
    try {
      if (mode === 'collect') { await collect(selected, range); return }
      setBusy('update'); setNotice(null)
      const result = await api.update(selected, range.end)
      await refreshOverview()
      setApplied({ ...range }); setPage(0); setVersion(value => value + 1); announceResult(result)
    } catch (error) { setNotice({ kind: 'error', text: messageOf(error) }) }
    finally { setBusy(null) }
  }

  const refresh = async () => {
    setBusy('refresh'); setNotice(null)
    try {
      const list = await refreshOverview()
      if (!selected && list.length) chooseStock(list[0])
      setVersion(value => value + 1)
      setNotice({ kind: 'success', text: '已刷新本地数据。' })
    } catch (error) { setHealth(null); setNotice({ kind: 'error', text: messageOf(error) }) }
    finally { setBusy(null); setInitializing(false) }
  }

  const exportData = async () => {
    if (!selected) return
    setBusy('export'); setNotice(null)
    try { await api.export(selected, applied); setNotice({ kind: 'success', text: 'Excel已生成并开始下载。' }) }
    catch (error) { setNotice({ kind: 'error', text: messageOf(error) }) }
    finally { setBusy(null) }
  }

  const toggleTracking = async () => {
    if (!active) return
    setBusy('tracking'); setNotice(null)
    try {
      await api.tracking(active.symbol, !active.tracked); await refreshOverview()
      setNotice({ kind: 'success', text: active.tracked ? '已暂停跟踪，历史数据继续保留，仍可手动采集。' : '已恢复跟踪，后续可继续更新。' })
    } catch (error) { setNotice({ kind: 'error', text: messageOf(error) }) }
    finally { setBusy(null) }
  }

  const filtered = stocks.filter(stock => `${stock.name}${stock.code}`.includes(search.trim()))
  const last = series.items.at(-1)
  const first = series.items[0]
  const change = first && last && first.close !== 0 ? (last.close / first.close - 1) * 100 : null
  const marketName = active?.market === 'sh' ? '上交所' : active?.market === 'sz' ? '深交所' : '北交所'

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={event => { event.preventDefault(); setView('workspace') }}><span className="brand-mark"><Sprout size={25} strokeWidth={1.8} /></span><span>拾序<small>STOCK LAB</small></span></a>
      <div className="sidebar-label">工作空间</div>
      <nav aria-label="主导航"><button className={view === 'workspace' ? 'nav-item active' : 'nav-item'} onClick={() => setView('workspace')}><LayoutDashboard size={18} />行情工作台<span className="nav-indicator" /></button><button className={view === 'history' ? 'nav-item active' : 'nav-item'} onClick={() => setView('history')}><FolderClock size={18} />采集记录</button></nav>
      <div className="watchlist-heading"><span className="sidebar-label">自选股票 <b>{stocks.length.toString().padStart(2, '0')}</b></span><button className="sidebar-icon" title="添加股票" aria-label="添加自选股票" disabled={!!busy} onClick={() => setDialog(true)}><Plus size={17} /></button></div>
      <div className="sidebar-search"><Search size={15} /><input aria-label="筛选已采集股票" placeholder="搜索自选名称 / 代码" value={search} onChange={event => setSearch(event.target.value)} /></div>
      <div className="watchlist">{filtered.map(stock => <button key={stock.symbol} className={`stock-item ${selected === stock.symbol ? 'selected' : ''}`} disabled={!!busy} onClick={() => chooseStock(stock)}><span className="market-badge">{stock.market.toUpperCase()}</span><span><strong>{stock.name}</strong><small>{stock.code} <span>· {stock.tracked ? '跟踪中' : '已暂停'}</span></small></span>{selected === stock.symbol && <i />}</button>)}
        {!filtered.length && <p className="sidebar-empty">{stocks.length ? '没有匹配的自选股票' : initializing ? '正在读取自选列表…' : '添加股票，开始采集。'}</p>}
      </div>
      <div className="sidebar-bottom"><div className="sidebar-note"><Database size={19} /><div><strong>让数据，有迹可循。</strong><p>从一条日线开始积累。</p></div></div><div className="sidebar-footer"><span className="avatar">实</span><div>程序设计实验<small>Experiment 06</small></div><span className="version">v1.0</span></div></div>
    </aside>

    <div className="main-shell"><header className="topbar"><div className="breadcrumb">工作空间 <span>/</span> <strong>{view === 'workspace' ? 'A股数据采集' : '采集记录'}</strong></div><div className={`connection ${health ? 'online' : ''}`}><i />{health ? 'MySQL 已连接' : initializing ? '正在连接…' : '服务未连接'}</div></header>
      <main>
        <div className="page-heading"><div><div className="eyebrow">YOUR DATA, YOUR PACE</div><h1>{view === 'workspace' ? '行情采集工作台' : '每一次采集，都有记录'}</h1><p>{view === 'workspace' ? '选择一只股票，积累每一个交易日的数据。' : '查看采集结果、更新数量和历史运行状态。'}</p></div><div className="heading-actions"><button className="button icon-text" disabled={!!busy} onClick={refresh}><RefreshCw size={16} className={busy === 'refresh' ? 'spin' : ''} />刷新</button><button className="button button-primary" disabled={!!busy} onClick={() => setDialog(true)}><Plus size={17} />添加股票</button></div></div>
        {notice && <div className={`notice ${notice.kind}`} role={notice.kind === 'error' ? 'alert' : 'status'}>{notice.kind === 'error' ? <CircleAlert size={18} /> : <Check size={18} />}<span>{notice.text}</span><button aria-label="关闭提示" onClick={() => setNotice(null)}><X size={16} /></button></div>}

        {view === 'history' ? <><div className="history-summary"><span className="pill"><Activity size={14} />共 {logData.total.toLocaleString()} 次运行</span><span>时间均为北京时间 · 每页10条 · 按时间倒序</span></div><LogsTable logs={logData.items} pagination={{ total: logData.total, page: logPage, pageSize: 10, loading: logsLoading, onPage: setLogPage }} /></>
          : !active ? <section className="panel welcome-panel"><div className="welcome-art"><TrendingUp size={54} strokeWidth={1.2} /></div><span className="eyebrow">START WITH ONE STOCK</span><h2>{initializing ? '正在连接你的数据…' : '从你的第一只股票开始'}</h2><p>输入股票代码，选择一小段日期。<br />采集成功后，即可查看走势、增量更新并导出Excel。</p><button className="button button-primary" disabled={!!busy || initializing} onClick={() => setDialog(true)}>添加并采集 <ArrowRight size={17} /></button></section>
            : <>
              <section className="panel collection-panel"><div className="stock-heading"><div className="stock-title"><span className="stock-avatar">{active.name.slice(0, 1)}</span><div><h2>{active.name}<span className="code-pill">{active.code}</span><span className="market-text">{marketName} A股</span></h2><p><span className="live-dot" />{active.tracked ? '自选跟踪中' : '已暂停跟踪'}<span className="separator">/</span>日线<span className="separator">/</span>不复权</p></div></div><button className="text-button muted" disabled={!!busy} onClick={toggleTracking}>{active.tracked ? <Pause size={14} /> : <Play size={14} />}{active.tracked ? '暂停跟踪' : '恢复跟踪'}</button></div>
                <form className="collection-form" onSubmit={event => { event.preventDefault(); if (validateRange()) { setApplied({ ...range }); setPage(0) } }}>
                  <label className="form-label">开始日期<div className="date-input"><CalendarDays size={16} /><input aria-label="开始日期" type="date" required value={range.start} onChange={event => setRange({ ...range, start: event.target.value })} disabled={!!busy} /></div></label>
                  <span className="date-dash">—</span><label className="form-label">结束日期<div className="date-input"><CalendarDays size={16} /><input aria-label="结束日期" type="date" required value={range.end} onChange={event => setRange({ ...range, end: event.target.value })} disabled={!!busy} /></div></label>
                  <button className="button query-button" type="submit" disabled={!!busy}><ListFilter size={16} />查询</button><div className="form-divider" /><button className="button" type="button" disabled={!!busy} onClick={() => syncSelected('collect')}><ArrowDownToLine size={16} />{busy === 'collect' ? '正在采集…' : '采集所选区间'}</button><button className="button button-primary" type="button" disabled={!!busy || !active.latest_trade_date} onClick={() => syncSelected('update')}><RefreshCw size={16} className={busy === 'update' ? 'spin' : ''} />{busy === 'update' ? '正在更新…' : '增量更新'}</button>
                </form>
                <div className="collection-hint"><Info size={14} /><span>增量更新以已存交易日期为起点，回查近期数据，更新至上方结束日期。</span><span className="cutoff">完整日线截止 <strong>{health?.daily_cutoff || '—'}</strong></span></div>
              </section>

              <div className="stats-grid"><div className="stat-card"><div className="stat-label">本地累计日线 <Database size={16} /></div><div className="stat-value">{(active.total_rows || 0).toLocaleString()}<small>条</small></div><div className="stat-foot">{active.first_trade_date ? `${active.first_trade_date} 起` : '等待首次采集'}</div></div>
                <div className="stat-card"><div className="stat-label">已存最新交易日 <CalendarDays size={16} /></div><div className="stat-value date-value">{active.latest_trade_date || '—'}</div><div className="stat-foot">最近同步 {timestamp(active.last_success_at)}</div></div>
                <div className="stat-card"><div className="stat-label">图示末日收盘价 <TrendingUp size={16} /></div><div className="stat-value">{chartLoading ? '—' : number(last?.close)}<small>元</small></div><div className={`stat-foot ${changeClass(last?.change_pct)}`}>{last ? `${last.trade_date}  ${signed(last.change_pct, '%')}` : '当前区间暂无行情'}</div></div>
                <div className="stat-card"><div className="stat-label">图示区间价格变化 <Activity size={16} /></div><div className={`stat-value ${changeClass(change)}`}>{chartLoading ? '—' : signed(change, '%')}</div><div className="stat-foot">首末交易日收盘价比较</div></div></div>
              <PriceChart rows={series.items} total={series.total} loading={chartLoading} />
              <QuoteTable rows={table.items} total={table.total} page={page} pageSize={PAGE_SIZE} loading={tableLoading} exporting={busy === 'export'} disabled={!!busy} onPage={setPage} onExport={exportData} />
              <LogsTable logs={logs} compact onMore={() => setView('history')} />
            </>}
        <footer className="page-footer"><span><span className="footer-dot" />东方财富日线行情</span><span>自主选择 · 持续积累 · 随时导出</span></footer>
      </main>
    </div>
    {dialog && <StockDialog initialRange={defaultRange(health?.daily_cutoff)} busy={!!busy} onClose={() => setDialog(false)} onCollect={collect} />}
  </div>
}
