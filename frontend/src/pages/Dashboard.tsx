import { useEffect, useState } from 'react'
import { fetchActiveSignals, fetchStatsOverview, triggerGenerate, fetchCurrentPrices } from '../api/client'
import SignalCard from '../components/SignalCard'
import './Dashboard.css'

export default function Dashboard() {
  const [active, setActive] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [timeLeft, setTimeLeft] = useState(300) // 5 minutes in seconds
  const [prices, setPrices] = useState<Record<string, number>>({})

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const [a, s] = await Promise.all([fetchActiveSignals(), fetchStatsOverview()])
      setActive(a)
      setStats(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Errore')
    } finally {
      setLoading(false)
    }
  }

  // Poll prices for active signals
  useEffect(() => {
    if (!active.length) return

    const updatePrices = async () => {
      const assets = Array.from(new Set(active.map(s => s.asset)))
      if (!assets.length) return
      const p = await fetchCurrentPrices(assets)
      setPrices(prev => ({ ...prev, ...p }))
    }

    updatePrices() // Immediate
    const timer = setInterval(updatePrices, 5000) // Every 5s
    return () => clearInterval(timer)
  }, [active])

  // Initial load
  useEffect(() => {
    load()
    const t = setInterval(load, 30000) // Refresh data every 30s
    return () => clearInterval(t)
  }, [])

  // Auto-scan timer
  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          handleGenerate()
          return 300 // Reset to 5 mins
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  const handleGenerate = async () => {
    if (generating) return
    setGenerating(true)
    setError(null)
    try {
      await triggerGenerate()
      await load()
      setTimeLeft(300) // Reset timer on manual or auto trigger
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Generate failed')
    } finally {
      setGenerating(false)
    }
  }

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  if (loading && !active.length) {
    return (
      <div className="page">
        <h1>Dashboard</h1>
        <p className="muted">Loading...</p>
      </div>
    )
  }

  return (
    <div className="page dashboard">
      <header className="page-header">
        <h1>Dashboard</h1>
        <div className="header-actions">
          <span className="scan-timer mono">Next scan: {formatTime(timeLeft)}</span>
          <button
            className="btn-primary"
            onClick={handleGenerate}
            disabled={generating}
          >
            {generating ? 'Generating...' : 'Manual Scan'}
          </button>
        </div>
      </header>
      {error && <div className="alert alert-error">{error}</div>}
      {stats != null && (
        <section className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{stats.total_closed}</span>
            <span className="stat-label">Closed Signals</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.win_rate_pct}%</span>
            <span className="stat-label">Win rate</span>
          </div>
          <div className="stat-card">
            <span className={`stat-value ${(stats.avg_pnl_pct ?? 0) >= 0 ? 'success' : 'danger'}`}>
              {(stats.avg_pnl_pct ?? 0) >= 0 ? '+' : ''}{stats.avg_pnl_pct ?? 0}%
            </span>
            <span className="stat-label">Avg PnL</span>
          </div>
          <div className="stat-card">
            <span className={`stat-value ${(stats.total_pnl_pct ?? 0) >= 0 ? 'success' : 'danger'}`}>
              {(stats.total_pnl_pct ?? 0) >= 0 ? '+' : ''}{stats.total_pnl_pct ?? 0}%
            </span>
            <span className="stat-label">Total PnL</span>
          </div>
        </section>
      )}
      <section className="section">
        <h2>Active Signals</h2>
        {active.length === 0 ? (
          generating ? (
            <div className="loader-container">
              <div className="hourglass"></div>
              <p className="muted">Analyzing markets...</p>
            </div>
          ) : (
            <p className="muted">No active signals. Click &quot;Manual Scan&quot; or wait for auto-scan.</p>
          )
        ) : (
          <div className="signal-grid">
            {active.map((s) => (
              <SignalCard
                key={s.id}
                signal={s}
                currentPrice={prices[s.asset] || prices[s.asset.split(':')[0]]}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
