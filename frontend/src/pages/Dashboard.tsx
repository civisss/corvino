import { useEffect, useState } from 'react'
import { fetchActiveSignals, fetchStatsOverview, triggerGenerate, fetchCurrentPrices, fetchConfig, closeSignal, updateSignalHits } from '../api/client'
import SignalCard from '../components/SignalCard'
import './Dashboard.css'

export default function Dashboard() {
  const [active, setActive] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [timeLeft, setTimeLeft] = useState(600) // 10 minutes in seconds
  const [prices, setPrices] = useState<Record<string, number>>({})
  const [decimalsMap, setDecimalsMap] = useState<Record<string, number>>({})

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

  // Check if SL or TP is hit and auto-close
  const checkAndCloseSignals = async (signalList: any[], priceMap: Record<string, number>) => {
    for (const s of signalList) {
      const price = priceMap[s.asset] || priceMap[s.asset.split(':')[0]]
      if (!price) continue

      const isLong = s.direction.toUpperCase() === 'LONG'
      let shouldClose = false
      let exitPrice = price

      // Check SL hit
      if (isLong && price <= s.stop_loss) {
        shouldClose = true
        exitPrice = s.stop_loss
      } else if (!isLong && price >= s.stop_loss) {
        shouldClose = true
        exitPrice = s.stop_loss
      }

      // Check TP hits and persist them
      const hits: any = {}
      if (isLong) {
        if (!s.tp1_hit && price >= s.take_profit_1) hits.tp1 = true
        if (!s.tp2_hit && s.take_profit_2 && price >= s.take_profit_2) hits.tp2 = true
        if (!s.tp3_hit && s.take_profit_3 && price >= s.take_profit_3) hits.tp3 = true
      } else {
        if (!s.tp1_hit && price <= s.take_profit_1) hits.tp1 = true
        if (!s.tp2_hit && s.take_profit_2 && price <= s.take_profit_2) hits.tp2 = true
        if (!s.tp3_hit && s.take_profit_3 && price <= s.take_profit_3) hits.tp3 = true
      }

      if (Object.keys(hits).length > 0) {
        try {
          console.log(`Updating TP hits for signal ${s.id}:`, hits)
          await updateSignalHits(s.id, hits)
          // We don't call load() immediately to avoid too many refreshes,
          // it will be refreshed on next interval or we can update local state.
          // For immediate UI update, we could update the 'active' state locally.
          setActive(prev => prev.map(item => item.id === s.id ? { ...item, ...hits.tp1 && { tp1_hit: true }, ...hits.tp2 && { tp2_hit: true }, ...hits.tp3 && { tp3_hit: true } } : item))
        } catch (err) {
          console.error('Failed to update TP hits:', err)
        }
      }

      // Check TP3 hit (full take profit) -> trigger close
      if (s.take_profit_3) {
        if (isLong && price >= s.take_profit_3) {
          shouldClose = true
          exitPrice = s.take_profit_3
        } else if (!isLong && price <= s.take_profit_3) {
          shouldClose = true
          exitPrice = s.take_profit_3
        }
      }

      if (shouldClose) {
        try {
          console.log(`Auto-closing signal ${s.id} at ${exitPrice}`)
          await closeSignal(s.id, exitPrice)
          load() // Refresh signals
        } catch (err) {
          console.error('Failed to auto-close signal:', err)
        }
      }
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

      // Check for auto-close
      checkAndCloseSignals(active, { ...prices, ...p })
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
    fetchConfig().then(cfg => {
      const map: Record<string, number> = {}
      if (cfg.assets) {
        Object.keys(cfg.assets).forEach(k => {
          map[k] = cfg.assets[k].decimals
        })
      }
      setDecimalsMap(map)
    }).catch(console.error)

    // Immediate scan check
    // If no signals and we just loaded, maybe trigger?
    // User requested: "immediate scan on load"
    // We can set timeLeft to 1 if we want it to trigger via the interval,
    // OR just call handleGenerate() if we know we want it.
    // Let's set timeLeft to 1 to force trigger via existing effect if we want,
    // BUT existing effect runs every 1s.

    // Better: separate effect for immediate trigger
    handleGenerate()

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          handleGenerate()
          return 600 // Reset to 10 mins
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
      setTimeLeft(600) // Reset timer on manual or auto trigger
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
                decimals={decimalsMap[s.asset] || decimalsMap[s.asset.split(':')[0]] || 2}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
