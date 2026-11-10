import { useEffect, useRef, useState } from 'react'
import { ArrowRight, CalendarDays, X } from 'lucide-react'
import type { DateRange } from './types'

export default function StockDialog({ initialRange, busy, onClose, onCollect }: {
  initialRange: DateRange; busy: boolean; onClose: () => void;
  onCollect: (code: string, range: DateRange) => Promise<void>;
}) {
  const [code, setCode] = useState('')
  const [range, setRange] = useState(initialRange)
  const [error, setError] = useState('')
  const dialogRef = useRef<HTMLDialogElement>(null)
  useEffect(() => {
    const dialog = dialogRef.current!
    dialog.showModal()
    return () => dialog.close()
  }, [])
  return <dialog ref={dialogRef} className="stock-dialog" aria-labelledby="add-stock-title" aria-describedby="add-stock-description" onCancel={event => { event.preventDefault(); if (!busy) onClose() }}>
    <div className="dialog-heading"><div className="dialog-icon"><CalendarDays size={23} /></div><button className="icon-button" aria-label="关闭添加股票" disabled={busy} onClick={onClose}><X size={20} /></button></div>
    <h2 id="add-stock-title">添加一只股票</h2><p id="add-stock-description">选择股票和日期，采集第一段日线数据。</p>
    <form onSubmit={async event => {
      event.preventDefault(); setError('')
      if (!/^(?:(sh|sz|bj)\.?)?\d{6}$/i.test(code.trim())) { setError('请输入六位股票代码，例如000001。'); return }
      if (range.start > range.end) { setError('开始日期不能晚于结束日期。'); return }
      try { await onCollect(code.trim(), range) } catch (error) { setError(error instanceof Error ? error.message : '采集失败') }
    }}>
      <label className="form-label">股票代码<input autoFocus required placeholder="例如 000001" value={code} onChange={event => setCode(event.target.value)} disabled={busy} autoComplete="off" /></label>
      <small>支持六位代码，也可输入 sz.000001、sh.600519 等格式。</small>
      <div className="dialog-dates"><label className="form-label">开始日期<input required type="date" value={range.start} onChange={event => setRange({ ...range, start: event.target.value })} disabled={busy} /></label><label className="form-label">结束日期<input required type="date" value={range.end} onChange={event => setRange({ ...range, end: event.target.value })} disabled={busy} /></label></div>
      <div className="dialog-note">每日一条行情 · 不复权 · 采集后自动加入自选列表</div>
      {error && <div role="alert" className="inline-error">{error}</div>}
      <button className="button button-primary dialog-submit" type="submit" disabled={busy}>{busy ? <><span className="loading-ring" />正在采集…</> : <>采集并添加 <ArrowRight size={17} /></>}</button>
    </form>
  </dialog>
}
