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
    <div className="flex flex-col h-screen overflow-hidden relative">

      {/* ── Video background ── */}
      <div className="absolute inset-0 overflow-hidden">
        <video
          className="w-full h-full object-cover"
          autoPlay loop muted playsInline
        >
          <source src="/bg.mp4" type="video/mp4" />
        </video>
        <div className="absolute inset-0" style={{ background: 'rgba(10,10,15,0.72)' }} />
      </div>

      {/* ── UI (sits above video via relative stacking context) ── */}
      <div className="relative flex flex-col h-full">

      {/* Top header */}
      <header
        className="shrink-0 h-14 border-b border-glass-border flex items-center px-5 gap-6 z-10"
        style={{ background: 'rgba(10,10,15,0.85)' }}
      >
        {/* Branding */}
        <div className="flex flex-col leading-none">
          <span className="font-mono text-brand text-sm font-bold tracking-tight italic">SKILLISSUE</span>
          <span className="text-text-secondary text-[9px] font-semibold uppercase tracking-[0.25em] mt-0.5">Racing</span>
        </div>

      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — nav only */}
        <nav
          className="w-[180px] shrink-0 relative flex flex-col h-full border-r border-glass-border pt-3 px-2 space-y-0.5"
          style={{ background: 'rgba(10,10,15,0.82)' }}
        >
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

          {/* Status panel at bottom */}
          <div className="absolute bottom-0 left-0 right-0 px-3 pb-4 pt-3 border-t border-glass-border space-y-2">
            <div className="glass-low rounded p-3 space-y-2">
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-positive shrink-0" />
                <span className="text-[10px] text-text-secondary font-mono">Agent monitoring</span>
              </div>
              <div className="flex items-center gap-2">
                <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${iracing ? 'bg-teal shadow-[0_0_5px_#41eec2]' : 'bg-text-dim'}`} />
                <span className={`text-[10px] font-mono ${iracing ? 'text-teal' : 'text-text-dim'}`}>
                  iRacing {iracing ? 'Connected' : 'Offline'}
                </span>
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

      </div>{/* end UI wrapper */}
    </div>
  )
}
