import { useEffect, useState } from 'react'
import { fetchSignals } from '../api/client'
import SignalCard from '../components/SignalCard'
import './Dashboard.css'
import './SignalsHistory.css'

export default function SignalsHistory() {
  const [signals, setSignals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [asset, setAsset] = useState('')
  const [timeframe, setTimeframe] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await fetchSignals({
          asset: asset || undefined,
          timeframe: timeframe || undefined,
          limit: 200,
        })
        if (!cancelled) setSignals(data)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Errore')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
  }, [asset, timeframe])

  if (loading && !signals.length) {
    return (
      <div className="page">
        <h1>Storico segnali</h1>
        <p className="muted">Caricamento...</p>
      </div>
    )
  }

  return (
    <div className="page dashboard">
      <h1>Storico segnali</h1>
      <div className="filters">
        <select
          value={asset}
          onChange={(e) => setAsset(e.target.value)}
          className="filter-select"
        >
          <option value="">Tutti gli asset</option>
          <option value="BTC/USDT:USDT">BTC</option>
          <option value="ETH/USDT:USDT">ETH</option>
          <option value="SOL/USDT:USDT">SOL</option>
          <option value="XRP/USDT:USDT">SOL</option>
        </select>
        <select
          value={timeframe}
          onChange={(e) => setTimeframe(e.target.value)}
          className="filter-select"
        >
          <option value="">Tutti i timeframe</option>
          <option value="1h">1h</option>
          <option value="2h">2h</option>
          <option value="4h">4h</option>
          <option value="1d">1d</option>
        </select>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {signals.length === 0 ? (
        <p className="muted">Nessun segnale trovato.</p>
      ) : (
        <div className="signal-grid">
          {signals.map((s) => (
            <SignalCard key={s.id} signal={s} />
          ))}
        </div>
      )}
    </div>
  )
}
