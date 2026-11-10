import type { DateRange, Health, LogPage, QuotePage, Stock, SyncResult } from './types'

async function errorMessage(response: Response): Promise<string> {
  const data = await response.json().catch(() => null)
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return '输入格式不正确，请检查股票代码和日期。'
  return `请求失败（${response.status}），请检查后端服务。`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try { response = await fetch(`/api${path}`, init) }
  catch { throw new Error('无法连接服务，请确认后端已启动。') }
  if (!response.ok) throw new Error(await errorMessage(response))
  return response.json() as Promise<T>
}

function post<T>(path: string, body: unknown) {
  return request<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}

function query(symbol: string, range?: DateRange) {
  const params = new URLSearchParams({ symbol })
  if (range?.start) params.set('start_date', range.start)
  if (range?.end) params.set('end_date', range.end)
  return params
}

export const api = {
  health: (signal?: AbortSignal) => request<Health>('/health', { signal }),
  stocks: (signal?: AbortSignal) => request<Stock[]>('/stocks', { signal }),
  logs: (limit = 10, offset = 0, signal?: AbortSignal) => request<LogPage>(`/logs?limit=${limit}&offset=${offset}`, { signal }),
  quotes: (symbol: string, range: DateRange, limit: number, offset = 0, signal?: AbortSignal) => {
    const params = query(symbol, range)
    params.set('limit', String(limit)); params.set('offset', String(offset))
    return request<QuotePage>(`/quotes?${params}`, { signal })
  },
  collect: (symbol: string, range: DateRange) => post<SyncResult>('/collect', {
    symbol, start_date: range.start, end_date: range.end,
  }),
  update: (symbol: string, end: string) => post<SyncResult>('/update', { symbol, end_date: end }),
  tracking: (symbol: string, tracked: boolean) => request<Stock>(`/stocks/${encodeURIComponent(symbol)}/tracking`, {
    method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tracked }),
  }),
  export: async (symbol: string, range: DateRange) => {
    const response = await fetch(`/api/export?${query(symbol, range)}`)
    if (!response.ok) throw new Error(await errorMessage(response))
    const url = URL.createObjectURL(await response.blob())
    const anchor = document.createElement('a')
    anchor.href = url; anchor.download = `${symbol}_${range.start}_${range.end}.xlsx`
    document.body.append(anchor); anchor.click(); anchor.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  },
}
