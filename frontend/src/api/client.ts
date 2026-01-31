const API_BASE = '/api'

export interface SignalResponse {
  id: string
  asset: string
  timeframe: string
  direction: string
  entry_price: number
  stop_loss: number
  take_profit_1: number
  take_profit_2?: number
  take_profit_3?: number
  position_size_pct?: number
  risk_reward?: number
  invalidation_conditions?: string
  confidence_score: number
  explanation?: {
    summary?: string
    technical_reasoning?: string[]
    pattern_reasoning?: string[]
    risk_factors?: string[]
    invalidation_conditions?: string[]
  }
  tp1_hit?: boolean
  tp2_hit?: boolean
  tp3_hit?: boolean
  status: string
  exit_price?: number
  pnl_pct?: number
  closed_at?: string
  created_at: string
  updated_at: string
}

export interface StatsOverview {
  total_closed: number
  wins: number
  losses: number
  win_rate_pct: number
  avg_pnl_pct: number
  total_pnl_pct: number
}

export async function fetchSignals(params?: {
  status?: string
  asset?: string
  timeframe?: string
  limit?: number
}): Promise<SignalResponse[]> {
  const sp = new URLSearchParams()
  if (params?.status) sp.set('status', params.status)
  if (params?.asset) sp.set('asset', params.asset)
  if (params?.timeframe) sp.set('timeframe', params.timeframe)
  if (params?.limit) sp.set('limit', String(params.limit))
  const q = sp.toString()
  const res = await fetch(`${API_BASE}/signals${q ? `?${q}` : ''}`)
  if (!res.ok) throw new Error('Failed to fetch signals')
  return res.json()
}

export async function fetchActiveSignals(): Promise<SignalResponse[]> {
  const res = await fetch(`${API_BASE}/signals/active`)
  if (!res.ok) throw new Error('Failed to fetch active signals')
  return res.json()
}

export async function fetchClosedSignals(limit = 100): Promise<SignalResponse[]> {
  const res = await fetch(`${API_BASE}/signals/closed?limit=${limit}`)
  if (!res.ok) throw new Error('Failed to fetch closed signals')
  return res.json()
}

export async function fetchSignal(id: string): Promise<SignalResponse> {
  const res = await fetch(`${API_BASE}/signals/${id}`)
  if (!res.ok) throw new Error('Signal not found')
  return res.json()
}

export async function fetchStatsOverview(): Promise<StatsOverview> {
  const res = await fetch(`${API_BASE}/signals/stats/overview`)
  if (!res.ok) throw new Error('Failed to fetch stats')
  return res.json()
}

export async function triggerGenerate(): Promise<{ created: number; signal_ids: string[] }> {
  const res = await fetch(`${API_BASE}/generate`, { method: 'POST' })
  if (!res.ok) throw new Error('Generate failed')
  return res.json()
}

export async function fetchCurrentPrices(symbols: string[]): Promise<Record<string, number>> {
  if (!symbols.length) return {}
  const q = symbols.join(',')
  const res = await fetch(`${API_BASE}/prices?symbols=${encodeURIComponent(q)}`)
  if (!res.ok) {
    // Don't throw, just return empty so polling continues
    console.error('Failed to fetch prices')
    return {}
  }
  return res.json()
  return res.json()
}

export async function fetchConfig(): Promise<{ assets: Record<string, { decimals: number }>, scan_interval: number }> {
  try {
    const res = await fetch(`${API_BASE}/config`)
    if (!res.ok) return { assets: {}, scan_interval: 600 }
    return res.json()
  } catch (e) {
    return { assets: {}, scan_interval: 600 }
  }
}

export async function closeSignal(signalId: string, exitPrice: number): Promise<SignalResponse> {
  const res = await fetch(`${API_BASE}/signals/${signalId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      status: 'closed',
      exit_price: exitPrice,
      closed_at: new Date().toISOString()
    })
  })
  if (!res.ok) throw new Error('Failed to close signal')
  return res.json()
}

export async function updateSignalHits(signalId: string, hits: { tp1?: boolean, tp2?: boolean, tp3?: boolean }): Promise<SignalResponse> {
  const payload: any = {}
  if (hits.tp1 !== undefined) payload.tp1_hit = hits.tp1
  if (hits.tp2 !== undefined) payload.tp2_hit = hits.tp2
  if (hits.tp3 !== undefined) payload.tp3_hit = hits.tp3

  const res = await fetch(`${API_BASE}/signals/${signalId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  if (!res.ok) throw new Error('Failed to update signal hits')
  return res.json()
}

