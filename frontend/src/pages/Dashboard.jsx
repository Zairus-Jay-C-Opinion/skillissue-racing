import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import CoachingCard from '../components/CoachingCard'
import TyreCard from '../components/TyreCard'

function fmtTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3).padStart(6, '0')
  return `${m}:${sec}`
}

function fmtDelta(d) {
  if (d == null) return null
  const sign = d >= 0 ? '+' : ''
  return `${sign}${d.toFixed(3)}s`
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
        api.getSessions({ limit: 100 }),
      ]).then(([c, t, allSessions]) => {
        setCoaching(c)
        setTyres(t)
        const sessionsThisWeek = allSessions.items.filter(sess => {
          const d = new Date(sess.session_date)
          const now = new Date()
          const weekAgo = new Date(now - 7 * 86400000)
          return d >= weekAgo
        })
        const totalLaps = allSessions.items.reduce((acc, s) => acc + (s.lap_count || 0), 0)
        setStats({
          sessionsThisWeek: sessionsThisWeek.length,
          totalLaps,
          totalSessions: allSessions.total,
        })
        setLoading(false)
      })
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="text-gray-500 text-sm animate-pulse">Loading...</div>

  if (!lastSession) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="text-4xl">🏁</div>
        <p className="text-gray-400 text-sm">No sessions yet. Take some laps in iRacing with telemetry enabled (Alt+L).</p>
      </div>
    )
  }

  const delta = fmtDelta(lastSession.delta_to_pb)

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-lg font-bold text-white">Dashboard</h1>

      {/* Last session summary */}
      <div className="bg-card border border-border rounded-lg p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-white font-medium">{lastSession.car_name}</div>
            <div className="text-gray-400 text-sm">{lastSession.track_name}</div>
            <div className="text-gray-600 text-xs mt-1">
              {new Date(lastSession.session_date).toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' })}
            </div>
          </div>
          <Link to={`/sessions/${lastSession.id}`} className="text-xs text-accent hover:underline">
            Full detail →
          </Link>
        </div>
        <div className="grid grid-cols-3 gap-4 border-t border-border pt-4">
          <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">Best lap</div>
            <div className="text-white font-mono font-bold mt-1">{fmtTime(lastSession.best_lap_time)}</div>
          </div>
          <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">Delta to PB</div>
            <div className={`font-mono font-bold mt-1 ${delta === null ? 'text-gray-500' : lastSession.delta_to_pb >= 0 ? 'text-red-400' : 'text-green-400'}`}>
              {delta || '—'}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">Laps</div>
            <div className="text-white font-mono font-bold mt-1">{lastSession.lap_count || '—'}</div>
          </div>
        </div>
      </div>

      {/* Quick stats */}
      {stats && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Sessions this week', val: stats.sessionsThisWeek },
            { label: 'Total laps', val: stats.totalLaps },
            { label: 'Total sessions', val: stats.totalSessions },
          ].map(({ label, val }) => (
            <div key={label} className="bg-card border border-border rounded-lg p-4">
              <div className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</div>
              <div className="text-2xl font-bold text-white mt-1">{val}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-5">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">AI Coaching</div>
          <CoachingCard coaching={coaching} />
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Tyre Temps</div>
          <TyreCard tyreData={tyres} />
        </div>
      </div>
    </div>
  )
}
