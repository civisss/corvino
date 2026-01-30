import { useEffect, useState } from 'react'
import { fetchStatsOverview, fetchClosedSignals } from '../api/client'
import './Dashboard.css'
import './PnL.css'

export default function PnL() {
  const [stats, setStats] = useState<any>(null)
  const [closed, setClosed] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [s, c] = await Promise.all([fetchStatsOverview(), fetchClosedSignals(50)])
        if (!cancelled) {
          setStats(s)
          setClosed(c)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Errore')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) {
    return (
      <div className="page">
        <h1>Panoramica P&L</h1>
        <p className="muted">Caricamento...</p>
      </div>
    )
  }

  return (
    <div className="page dashboard">
      <h1>Panoramica P&L</h1>
      {error && <div className="alert alert-error">{error}</div>}
      {stats != null && (
        <>
          <section className="stats-grid pnl-stats">
            <div className="stat-card">
              <span className="stat-value">{stats.total_closed}</span>
              <span className="stat-label">Segnali chiusi</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.wins}</span>
              <span className="stat-label">Wins</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.losses}</span>
              <span className="stat-label">Losses</span>
            </div>
            <div className="stat-card">
              <span className="stat-value">{stats.win_rate_pct}%</span>
              <span className="stat-label">Win rate</span>
            </div>
            <div className="stat-card">
              <span className={`stat-value ${(stats.avg_pnl_pct ?? 0) >= 0 ? 'success' : 'danger'}`}>
                {(stats.avg_pnl_pct ?? 0) >= 0 ? '+' : ''}{stats.avg_pnl_pct ?? 0}%
              </span>
              <span className="stat-label">PnL medio</span>
            </div>
            <div className="stat-card">
              <span className={`stat-value ${(stats.total_pnl_pct ?? 0) >= 0 ? 'success' : 'danger'}`}>
                {(stats.total_pnl_pct ?? 0) >= 0 ? '+' : ''}{stats.total_pnl_pct ?? 0}%
              </span>
              <span className="stat-label">PnL totale</span>
            </div>
          </section>
          <section className="section">
            <h2>Ultimi chiusi</h2>
            {closed.length === 0 ? (
              <p className="muted">Nessun segnale chiuso.</p>
            ) : (
              <div className="pnl-table-wrap">
                <table className="pnl-table">
                  <thead>
                    <tr>
                      <th>Asset</th>
                      <th>TF</th>
                      <th>Direzione</th>
                      <th>Entry</th>
                      <th>Exit</th>
                      <th>PnL %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {closed.map((s) => (
                      <tr key={s.id}>
                        <td className="mono">{s.asset.replace('/USDT:USDT', '').replace('/USDT', '')}</td>
                        <td>{s.timeframe}</td>
                        <td className={s.direction === 'LONG' ? 'success' : 'danger'}>{s.direction}</td>
                        <td className="mono">{s.entry_price?.toFixed(2)}</td>
                        <td className="mono">{s.exit_price?.toFixed(2) ?? '-'}</td>
                        <td className={`mono ${(s.pnl_pct ?? 0) >= 0 ? 'success' : 'danger'}`}>
                          {(s.pnl_pct ?? 0) >= 0 ? '+' : ''}{s.pnl_pct?.toFixed(2) ?? '-'}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
