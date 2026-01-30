import { useEffect, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData } from 'lightweight-charts'
import { SignalResponse } from '../api/client'

interface SignalChartProps {
  signal: SignalResponse
  ohlcv?: { time: string; open: number; high: number; low: number; close: number }[]
}

export default function SignalChart({ signal, ohlcv }: SignalChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<IChartApi | null>(null)
  const candleSeries = useRef<ISeriesApi<'Candlestick'> | null>(null)

  useEffect(() => {
    if (!chartRef.current || !signal) return

    const chart = createChart(chartRef.current, {
      layout: {
        background: { color: '#0a0a0a' },
        textColor: '#737373',
      },
      grid: {
        vertLines: { color: '#1a1a1a' },
        horzLines: { color: '#1a1a1a' },
      },
      rightPriceScale: { borderColor: '#1a1a1a' },
      timeScale: { borderColor: '#1a1a1a', timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: '#4afffc' }, horzLine: { color: '#4afffc' } },
    })

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
    })

    if (ohlcv && ohlcv.length > 0) {
      const data: CandlestickData[] = ohlcv.map((c) => ({
        time: c.time as any,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
      candlestickSeries.setData(data)
    } else {
      const t = new Date().toISOString().slice(0, 10)
      candlestickSeries.setData([
        { time: t, open: signal.entry_price, high: signal.take_profit_1, low: signal.stop_loss, close: signal.entry_price },
      ])
    }

    candlestickSeries.createPriceLine({ price: signal.entry_price, color: '#4afffc', lineWidth: 2, title: 'Entry' })
    candlestickSeries.createPriceLine({ price: signal.stop_loss, color: '#ef4444', lineWidth: 1, title: 'SL' })
    candlestickSeries.createPriceLine({ price: signal.take_profit_1, color: '#22c55e', lineWidth: 1, title: 'TP1' })
    if (signal.take_profit_2 != null) {
      candlestickSeries.createPriceLine({ price: signal.take_profit_2, color: '#22c55e', lineWidth: 1, title: 'TP2' })
    }
    if (signal.take_profit_3 != null) {
      candlestickSeries.createPriceLine({ price: signal.take_profit_3, color: '#22c55e', lineWidth: 1, title: 'TP3' })
    }

    chartInstance.current = chart
    candleSeries.current = candlestickSeries

    return () => {
      chart.remove()
      chartInstance.current = null
      candleSeries.current = null
    }
  }, [signal, ohlcv])

  return <div ref={chartRef} className="signal-chart" style={{ height: 320, width: '100%' }} />
}
