import { SignalResponse } from '../api/client'
import { format } from 'date-fns'
import './SignalCard.css'

interface SignalCardProps {
  signal: SignalResponse
  currentPrice?: number
  onClose?: (id: string) => void
}

export default function SignalCard({ signal, currentPrice }: SignalCardProps) {
  const isLong = signal.direction.toUpperCase() === 'LONG'
  const assetShort = signal.asset.replace('/USDT:USDT', '').replace('/USDT', '')

  // Highlight logic
  const checkHit = (level: number, type: 'sl' | 'tp') => {
    if (!currentPrice) return ''
    if (isLong) {
      if (type === 'tp' && currentPrice >= level) return 'hit-success'
      if (type === 'sl' && currentPrice <= level) return 'hit-danger'
    } else {
      if (type === 'tp' && currentPrice <= level) return 'hit-success'
      if (type === 'sl' && currentPrice >= level) return 'hit-danger'
    }
    return ''
  }

  return (
    <article className="signal-card">
      <header className="signal-card-header">
        <span className="signal-asset mono">{assetShort}</span>
        <span className="signal-tf">{signal.timeframe}</span>
        <span className={`signal-direction ${isLong ? 'long' : 'short'}`}>
          {signal.direction}
        </span>
        <span className="signal-status">{signal.status}</span>
      </header>
      <div className="signal-card-body">
        <div className="signal-levels-container">
          <div className="level-row main-levels">
            {currentPrice != null ? (
              <div className="level">
                <span className="label">Current</span>
                <span className="value mono price-current">{currentPrice.toFixed(2)}</span>
              </div>
            ) : (
              <div className="level">
                <span className="label">Current</span>
                <span className="value mono muted">-</span>
              </div>
            )}
            <div className="level">
              <span className="label">Entry</span>
              <span className="value mono">{signal.entry_price.toFixed(2)}</span>
            </div>
            <div className={`level ${checkHit(signal.stop_loss, 'sl')}`}>
              <span className="label">SL</span>
              <span className={`value mono danger`}>{signal.stop_loss.toFixed(2)}</span>
            </div>
          </div>
          <div className="level-row tp-levels">
            <div className={`level ${checkHit(signal.take_profit_1, 'tp')}`}>
              <span className="label">TP1</span>
              <span className={`value mono success`}>{signal.take_profit_1.toFixed(2)}</span>
            </div>
            {signal.take_profit_2 != null && (
              <div className={`level ${checkHit(signal.take_profit_2, 'tp')}`}>
                <span className="label">TP2</span>
                <span className={`value mono success`}>{signal.take_profit_2.toFixed(2)}</span>
              </div>
            )}
            {signal.take_profit_3 != null && (
              <div className={`level ${checkHit(signal.take_profit_3, 'tp')}`}>
                <span className="label">TP3</span>
                <span className={`value mono success`}>{signal.take_profit_3.toFixed(2)}</span>
              </div>
            )}
          </div>
        </div>
        <div className="signal-meta">
          {signal.risk_reward != null && (
            <span className="meta">R:R {signal.risk_reward}</span>
          )}
          {signal.position_size_pct != null && (
            <span className="meta">Size {signal.position_size_pct}%</span>
          )}
          <span className="meta confidence">Confidence {signal.confidence_score}%</span>
        </div>
        {signal.explanation?.summary && (
          <p className="signal-summary">{signal.explanation.summary}</p>
        )}
        {signal.invalidation_conditions && (
          <p className="signal-invalidation">
            <strong>Invalidation:</strong> {signal.invalidation_conditions}
          </p>
        )}
        {signal.exit_price != null && (
          <div className="signal-exit">
            <span>Uscita: {signal.exit_price.toFixed(2)}</span>
            {signal.pnl_pct != null && (
              <span className={signal.pnl_pct >= 0 ? 'success' : 'danger'}>
                PnL {signal.pnl_pct >= 0 ? '+' : ''}{signal.pnl_pct.toFixed(2)}%
              </span>
            )}
          </div>
        )}
      </div>
      <footer className="signal-card-footer">
        <time className="mono">{format(new Date(signal.created_at), 'dd MMM yyyy HH:mm')}</time>
      </footer>
    </article>
  )
}
