import { useId, useState } from 'react'
import { ChartNoAxesCombined } from 'lucide-react'
import type { Quote } from './types'

export default function PriceChart({ rows, total, loading }: { rows: Quote[]; total: number; loading: boolean }) {
  const [mode, setMode] = useState<'price' | 'volume'>('price')
  const [hover, setHover] = useState<number | null>(null)
  const gradient = useId().replaceAll(':', '')
  const width = 1000, height = 245, left = 62, right = 20, top = 20, bottom = 35
  const values = rows.map(row => mode === 'price' ? row.close : row.volume)
  const min = mode === 'volume' ? 0 : Math.min(...values)
  const max = Math.max(...values)
  const pad = (max - min || max * 0.02 || 1) * 0.18
  const low = mode === 'volume' ? 0 : min - pad, high = max + pad
  const x = (index: number) => left + index / Math.max(rows.length - 1, 1) * (width - left - right)
  const y = (value: number) => top + (high - value) / (high - low || 1) * (height - top - bottom)
  const path = rows.map((_, index) => `${index ? 'L' : 'M'}${x(index)},${y(values[index])}`).join(' ')
  const active = hover !== null && rows[hover] ? rows[hover] : null
  const tickIndexes = [...new Set([0, Math.floor((rows.length - 1) / 3), Math.floor((rows.length - 1) * 2 / 3), rows.length - 1])]

  return <section className="panel chart-panel" aria-labelledby="chart-title">
    <div className="panel-heading">
      <div><h2 id="chart-title">行情走势 <span className="subtle-label">DAILY TREND</span></h2><p>所选日期范围 · 不复权日线</p></div>
      <div className="segmented" aria-label="图表指标">
        <button aria-pressed={mode === 'price'} onClick={() => { setMode('price'); setHover(null) }}>收盘价</button>
        <button aria-pressed={mode === 'volume'} onClick={() => { setMode('volume'); setHover(null) }}>成交量</button>
      </div>
    </div>
    {loading ? <div className="chart-empty"><span className="loading-ring" />正在加载行情…</div>
      : !rows.length ? <div className="chart-empty"><ChartNoAxesCombined size={34} /><span>所选范围暂无行情</span><small>采集日线或调整日期后，走势将显示在这里。</small></div>
      : <div className="chart-body">
        <div className="chart-legend"><i />{mode === 'price' ? '收盘价（元）' : '成交量（手）'}<span>{rows.length} 个交易日{total > rows.length ? `，共${total}条，仅展示前${rows.length}条` : ''}</span></div>
        {active && <div className="chart-tooltip">{active.trade_date}<strong>{mode === 'price' ? active.close.toFixed(2) + ' 元' : active.volume.toLocaleString() + ' 手'}</strong></div>}
        <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${mode === 'price' ? '收盘价' : '成交量'}走势图，共${rows.length}个交易日，详细数值见下方行情表。`}
          onPointerLeave={() => setHover(null)}
          onPointerMove={event => {
            const rect = event.currentTarget.getBoundingClientRect()
            const coordinate = (event.clientX - rect.left) / rect.width * width
            setHover(Math.max(0, Math.min(rows.length - 1, Math.round((coordinate - left) / (width - left - right) * (rows.length - 1)))))
          }}>
          <defs><linearGradient id={gradient} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#238b7e" stopOpacity="0.17" /><stop offset="100%" stopColor="#238b7e" stopOpacity="0.01" /></linearGradient></defs>
          {[0, 1, 2, 3, 4].map(tick => {
            const value = low + (high - low) * tick / 4
            return <g key={tick}><line x1={left} x2={width - right} y1={y(value)} y2={y(value)} stroke="#e7edef" strokeDasharray="4 5" />
              <text x={left - 12} y={y(value) + 4} textAnchor="end" className="axis-label">{mode === 'price' ? value.toFixed(2) : value >= 10000 ? (value / 10000).toFixed(0) + '万' : value.toFixed(0)}</text></g>
          })}
          {mode === 'price' ? <><path d={`${path} L${x(rows.length - 1)},${height - bottom} L${x(0)},${height - bottom} Z`} fill={`url(#${gradient})`} />
            <path d={path} fill="none" stroke="#238b7e" strokeWidth="2.8" strokeLinejoin="round" strokeLinecap="round" />
            {rows.length <= 31 && rows.map((row, index) => <circle key={row.trade_date} cx={x(index)} cy={y(row.close)} r="3.5" fill="#fff" stroke="#238b7e" strokeWidth="2" />)}</>
            : rows.map((row, index) => <rect key={row.trade_date} x={x(index) - Math.min(15, (width - left - right) / rows.length * 0.3)} y={y(row.volume)} width={Math.min(30, (width - left - right) / rows.length * 0.6)} height={height - bottom - y(row.volume)} rx="2" fill="#59a99b" />)}
          {active && hover !== null && <g><line x1={x(hover)} x2={x(hover)} y1={top} y2={height - bottom} stroke="#9ab8b2" strokeDasharray="4 4" /><circle cx={x(hover)} cy={y(values[hover])} r="5" fill="#238b7e" stroke="#fff" strokeWidth="2" /></g>}
          {tickIndexes.map(index => <text key={index} x={x(index)} y={height - 10} textAnchor={index === 0 ? 'start' : index === rows.length - 1 ? 'end' : 'middle'} className="axis-label">{rows[index].trade_date}</text>)}
        </svg>
      </div>}
  </section>
}
