import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import TelemetryChart from '../components/TelemetryChart'
import SectorDelta from '../components/SectorDelta'
import TyreCard from '../components/TyreCard'
import CoachingCard from '../components/CoachingCard'

function Icon({ name, className = '' }) {
  return <span className={`material-symbols-outlined select-none ${className}`}>{name}</span>
}

function fmtTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3).padStart(6, '0')
  return `${m}:${sec}`
}

function Stat({ label, value, mono = true, valueClass = 'text-white' }) {
  return (
    <div>
      <div className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider mb-1">{label}</div>
      <div className={`${mono ? 'font-mono' : ''} text-sm ${valueClass}`}>{value}</div>
    </div>
  )
}

export default function SessionDetail() {
  const { id } = useParams()
  const [session, setSession] = useState(null)
  const [coaching, setCoaching] = useState(null)
  const [tyres, setTyres] = useState(null)
  const [pb, setPb] = useState(null)

  useEffect(() => {
    api.getSession(id).then(s => {
      setSession(s)
      Promise.all([
        api.getCoaching(id).catch(() => null),
        api.getTyres(id).catch(() => null),
        api.getPB(s.car_name, s.track_name).catch(() => null),
      ]).then(([c, t, p]) => {
        setCoaching(c)
        setTyres(t)
        setPb(p)
      })
    })
  }, [id])

  if (!session) return (
    <div className="p-6 space-y-4">
      {[1, 2, 3].map(i => <div key={i} className="glass rounded-lg h-24 animate-pulse" />)}
    </div>
  )

  const delta = session.delta_to_pb

  return (
    <div className="p-6 space-y-5">
      {/* Back nav */}
      <Link to="/sessions" className="inline-flex items-center gap-1 text-text-secondary hover:text-white text-sm transition-colors">
        <Icon name="arrow_back" className="text-[16px]" />
        Sessions
      </Link>

      {/* Header card */}
      <div className="glass rounded-lg p-5">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-white font-bold text-lg leading-tight">{session.car_name}</h1>
            <div className="text-text-secondary text-sm mt-0.5">{session.track_name}</div>
            <div className="text-text-dim text-xs font-mono mt-1.5 flex flex-wrap gap-x-3">
              <span>{new Date(session.session_date).toLocaleString('en-GB')}</span>
              {session.air_temp && <span>{session.air_temp}°C air</span>}
              {session.track_temp && <span>{session.track_temp}°C track</span>}
              {session.weather && <span>{session.weather}</span>}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider mb-1">Best lap</div>
            <div className="text-white font-mono font-bold text-2xl">{fmtTime(session.best_lap_time)}</div>
            {delta != null && (
              <div className={`font-mono text-sm mt-0.5 ${delta >= 0 ? 'text-negative' : 'text-teal'}`}>
                {delta >= 0 ? '+' : ''}{delta.toFixed(3)}s vs PB
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 border-t border-glass-border mt-4 pt-4">
          <Stat label="Average lap" value={fmtTime(session.avg_lap_time)} />
          <Stat label="Laps completed" value={session.lap_count || '—'} />
          <Stat label="PB for combo" value={fmtTime(pb?.best_lap_time)} />
        </div>
      </div>

      {/* AI Coaching */}
      <CoachingCard coaching={coaching} />

      {/* Sector deltas + Tyres */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div>
          <div className="text-[10px] font-semibold text-text-dim uppercase tracking-widest mb-2">Sector deltas</div>
          <SectorDelta
            s1={session.sector_1_best && pb?.sector_1_best != null ? session.sector_1_best - pb.sector_1_best : null}
            s2={session.sector_2_best && pb?.sector_2_best != null ? session.sector_2_best - pb.sector_2_best : null}
            s3={session.sector_3_best && pb?.sector_3_best != null ? session.sector_3_best - pb.sector_3_best : null}
          />
        </div>
        <div>
          <div className="text-[10px] font-semibold text-text-dim uppercase tracking-widest mb-2">Tyre temperatures</div>
          <TyreCard tyreData={tyres} />
        </div>
      </div>

      {/* Telemetry chart */}
      <div className="glass rounded-lg p-5">
        <div className="text-[10px] font-semibold text-text-dim uppercase tracking-widest mb-4">Telemetry — throttle / brake / speed</div>
        <TelemetryChart rawData={session.raw_json} />
      </div>
    </div>
  )
}
