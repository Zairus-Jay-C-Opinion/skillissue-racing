import React, { useEffect, useState } from 'react'
import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Sessions from './pages/Sessions'
import SessionDetail from './pages/SessionDetail'
import Progress from './pages/Progress'
import Settings from './pages/Settings'
import Onboarding from './pages/Onboarding'
import { api } from './api'

const NAV = [
  { to: '/', label: 'Dashboard', icon: 'dashboard' },
  { to: '/sessions', label: 'Sessions', icon: 'timer' },
  { to: '/progress', label: 'Progress', icon: 'query_stats' },
  { to: '/settings', label: 'Settings', icon: 'settings' },
]

function Icon({ name, className = '' }) {
  return <span className={`material-symbols-outlined select-none ${className}`}>{name}</span>
}

export default function App() {
  const [onboarded, setOnboarded] = useState(null)
  const [iracing, setIracing] = useState(false)
  const location = useLocation()

  useEffect(() => {
    api.getSettings()
      .then(s => setOnboarded(s.onboarding_complete === 'true'))
      .catch(() => setOnboarded(true))
  }, [])

  useEffect(() => {
    const check = () => api.getStatus().then(s => setIracing(s.iracing_running)).catch(() => {})
    check()
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
  }, [])

  if (onboarded === null) return null

  if (!onboarded && location.pathname !== '/onboarding') {
    return <Onboarding onComplete={() => setOnboarded(true)} />
  }

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <nav className="w-[220px] shrink-0 flex flex-col h-screen border-r border-glass-border" style={{ background: 'rgba(10,10,15,0.95)' }}>
        {/* Branding */}
        <div className="px-5 pt-6 pb-5 border-b border-glass-border">
          <div className="font-mono text-brand text-sm font-bold tracking-tight italic leading-tight">SKILL ISSUE</div>
          <div className="text-text-secondary text-[10px] font-semibold uppercase tracking-[0.2em] mt-0.5">Racing</div>
        </div>

        {/* Nav links */}
        <div className="flex-1 py-3 space-y-0.5 px-2">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded text-sm font-medium transition-all duration-150 border-l-2 ${
                  isActive
                    ? 'border-brand text-white bg-white/5'
                    : 'border-transparent text-text-secondary hover:text-text-primary hover:bg-white/5'
                }`
              }
            >
              <Icon name={icon} className="text-[18px]" />
              {label}
            </NavLink>
          ))}
        </div>

        {/* Status panels */}
        <div className="px-3 pb-4 space-y-2 border-t border-glass-border pt-4">
          <div className="glass-low rounded p-3 flex items-center gap-3">
            <span className={`w-2 h-2 rounded-full shrink-0 ${iracing ? 'bg-teal shadow-[0_0_6px_#41eec2]' : 'bg-text-dim'}`} />
            <div>
              <div className="text-[10px] text-text-secondary uppercase tracking-wider">iRacing</div>
              <div className={`text-xs font-mono font-medium mt-0.5 ${iracing ? 'text-teal' : 'text-text-dim'}`}>
                {iracing ? 'Connected' : 'Offline'}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/sessions" element={<Sessions />} />
          <Route path="/sessions/:id" element={<SessionDetail />} />
          <Route path="/progress" element={<Progress />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
