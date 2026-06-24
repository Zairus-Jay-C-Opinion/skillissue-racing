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
  { to: '/', label: 'Dashboard' },
  { to: '/sessions', label: 'Sessions' },
  { to: '/progress', label: 'Progress' },
  { to: '/settings', label: 'Settings' },
]

export default function App() {
  const [onboarded, setOnboarded] = useState(null)
  const location = useLocation()

  useEffect(() => {
    api.getSettings()
      .then(s => setOnboarded(s.onboarding_complete === 'true'))
      .catch(() => setOnboarded(true)) // if backend unreachable, skip onboarding
  }, [])

  if (onboarded === null) return null // loading

  if (!onboarded && location.pathname !== '/onboarding') {
    return <Onboarding onComplete={() => setOnboarded(true)} />
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <nav className="w-48 shrink-0 bg-card border-r border-border flex flex-col pt-6 gap-1 px-3">
        <div className="text-xs font-bold text-blue-400 uppercase tracking-widest mb-4 px-2">
          Sim Companion
        </div>
        {NAV.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `px-3 py-2 rounded text-sm transition-colors ${
                isActive
                  ? 'bg-accent text-white'
                  : 'text-gray-400 hover:text-white hover:bg-border'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </nav>

      <main className="flex-1 overflow-y-auto p-6">
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
