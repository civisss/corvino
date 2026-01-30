import { useEffect, useState } from 'react'
import { fetchActiveSignals } from '../api/client'
import SignalCard from '../components/SignalCard'
import './Dashboard.css'

export default function SignalsActive() {
  const [signals, setSignals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await fetchActiveSignals()
        if (!cancelled) setSignals(data)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Errore')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    const t = setInterval(load, 20000)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [])

  if (loading && !signals.length) {
    return (
      <div className="page">
        <h1>Segnali attivi</h1>
        <p className="muted">Caricamento...</p>
      </div>
    )
  }

  return (
    <div className="page dashboard">
      <h1>Segnali attivi</h1>
      {error && <div className="alert alert-error">{error}</div>}
      {signals.length === 0 ? (
        <p className="muted">Nessun segnale attivo.</p>
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
