import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import SignalsActive from './pages/SignalsActive'
import SignalsClosed from './pages/SignalsClosed'
import SignalsHistory from './pages/SignalsHistory'
import PnL from './pages/PnL'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="nav">
          <div className="nav-brand">Corvino</div>
          <div className="nav-links">
            <NavLink to="/" end>Dashboard</NavLink>
            <NavLink to="/signals/active">Attivi</NavLink>
            <NavLink to="/signals/closed">Chiusi</NavLink>
            <NavLink to="/signals/history">Storico</NavLink>
            <NavLink to="/pnl">P&L</NavLink>
          </div>
        </nav>
        <main className="main">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/signals/active" element={<SignalsActive />} />
            <Route path="/signals/closed" element={<SignalsClosed />} />
            <Route path="/signals/history" element={<SignalsHistory />} />
            <Route path="/pnl" element={<PnL />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
