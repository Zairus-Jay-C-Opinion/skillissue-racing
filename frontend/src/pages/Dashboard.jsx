import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import CoachingCard from '../components/CoachingCard'
import TyreCard from '../components/TyreCard'

function Icon({ name, className = '' }) {
  return <span className={`material-symbols-outlined select-none ${className}`}>{name}</span>
}

function fmtTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3).padStart(6, '0')
  return `${m}:${sec}`
}

function MetricCard({ label, value, icon, valueClass = 'text-white', sub }) {
  return (
    <div className="glass rounded-lg p-5 flex flex-col justify-between min-h-[96px]">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-widest">{label}</span>
        {icon && <Icon name={icon} className="text-[16px] text-text-dim" />}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className={`font-mono text-xl font-bold leading-none ${valueClass}`}>{value}</span>
        {sub && <span className="text-xs text-text-secondary font-mono">{sub}</span>}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [lastSession, setLastSession] = useState(null)
  const [coaching, setCoaching] = useState(null)
  const [tyres, setTyres] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getSessions({ limit: 1 }).then(res => {
      const s = res.items[0]
      if (!s) { setLoading(false); return }
      setLastSession(s)
      Promise.all([
        api.getCoaching(s.id).catch(() => null),
        api.getTyres(s.id).catch(() => null),
        api.getSessions({ car: s.car_name, track: s.track_name, limit: 100 }),
      ]).then(([c, t, comboSessions]) => {
        setCoaching(c)
        setTyres(t)
        setStats({ comboCount: comboSessions.total })
        setLoading(false)
      })
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return (
    <div className="p-6 space-y-4">
      {[1,2,3].map(i => <div key={i} className="glass rounded-lg h-24 animate-pulse" />)}
    </div>
  )

  if (!lastSession) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center p-6">
        <Icon name="flag" className="text-[48px] text-text-dim" />
        <p className="text-text-secondary text-sm max-w-xs">No sessions yet. Take some laps in iRacing with telemetry enabled (Alt+L).</p>
      </div>
    )
  }

  const delta = lastSession.delta_to_pb
  const sessionDate = new Date(lastSession.session_date)

  return (
    <div className="p-6 space-y-4">
      {/* Context header */}
      <header className="mb-2">
        <h1 className="text-2xl font-bold text-white leading-tight">
          {lastSession.car_name} <span className="text-text-secondary font-normal">|</span> {lastSession.track_name}
        </h1>
        <div className="flex items-center gap-4 mt-1.5 text-text-secondary text-xs font-mono">
          <span className="flex items-center gap-1">
            <Icon name="calendar_today" className="text-[13px]" />
            {sessionDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
            {' · '}
            {sessionDate.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
          </span>
          <Link to={`/sessions/${lastSession.id}`} className="flex items-center gap-1 text-brand hover:opacity-80 transition-opacity ml-auto">
            <Icon name="open_in_new" className="text-[13px]" />
            Full detail
          </Link>
        </div>
      </header>

      {/* 4 metric cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <MetricCard
          label="Best Lap"
          value={fmtTime(lastSession.best_lap_time)}
          icon="timer"
        />
        <MetricCard
          label="Delta to PB"
          value={delta == null ? '—' : `${delta >= 0 ? '+' : ''}${delta.toFixed(3)}s`}
          icon="compare_arrows"
          valueClass={delta == null ? 'text-text-dim' : delta < 0 ? 'text-teal' : 'text-negative'}
        />
        <MetricCard
          label="Laps"
          value={lastSession.lap_count || '—'}
          icon="repeat"
        />
        <MetricCard
          label="Sessions on combo"
          value={stats?.comboCount ?? '—'}
          icon="route"
          sub="this car + track"
        />
      </div>

      {/* Coaching + Tyres */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12 lg:col-span-8">
          <CoachingCard coaching={coaching} />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <TyreCard tyreData={tyres} />
        </div>
      </div>
    </div>
  )
}
