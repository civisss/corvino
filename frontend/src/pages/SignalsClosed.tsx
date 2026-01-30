import { useEffect, useState } from 'react'
import { fetchClosedSignals } from '../api/client'
import SignalCard from '../components/SignalCard'
import './Dashboard.css'

export default function SignalsClosed() {
  const [signals, setSignals] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const data = await fetchClosedSignals(100)
        if (!cancelled) setSignals(data)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Errore')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
  }, [])

  if (loading && !signals.length) {
    return (
      <div className="page">
        <h1>Segnali chiusi</h1>
        <p className="muted">Caricamento...</p>
      </div>
    )
  }

  return (
    <div className="page dashboard">
      <h1>Segnali chiusi</h1>
      {error && <div className="alert alert-error">{error}</div>}
      {signals.length === 0 ? (
        <p className="muted">Nessun segnale chiuso.</p>
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
