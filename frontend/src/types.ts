export interface Stock {
  symbol: string; code: string; name: string; market: string; tracked: boolean;
  first_trade_date: string | null; latest_trade_date: string | null;
  total_rows: number | null; last_success_at: string | null;
}
export interface Quote {
  symbol: string; name: string; trade_date: string; open: number; close: number;
  high: number; low: number; volume: number; amount: number;
  amplitude: number | null; change_pct: number | null; change_amount: number | null;
  turnover: number | null; fetched_at: string;
}
export interface QuotePage { total: number; items: Quote[] }
export interface SyncLog {
  id: number; symbol: string; start_date: string; end_date: string;
  status: 'success' | 'no_data' | 'failed'; fetched_rows: number;
  inserted_rows: number; updated_rows: number; unchanged_rows: number;
  message: string; started_at: string; finished_at: string;
}
export interface LogPage { total: number; items: SyncLog[] }
export interface SyncResult {
  symbol: string; name: string; inserted: number; updated: number; unchanged: number;
  fetched: number; status: string; effective_end_date: string; requested_end_date: string;
}
export interface Health { status: string; daily_cutoff: string }
export interface DateRange { start: string; end: string }
