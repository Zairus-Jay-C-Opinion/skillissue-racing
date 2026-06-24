import React, { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import TelemetryChart from '../components/TelemetryChart'
import SectorDelta from '../components/SectorDelta'
import TyreCard from '../components/TyreCard'
import CoachingCard from '../components/CoachingCard'

function fmtTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3).padStart(6, '0')
  return `${m}:${sec}`
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

  if (!session) return <div className="text-gray-500 text-sm animate-pulse">Loading…</div>

  const s1Delta = session.sector_1_best && pb?.lap_telemetry ? null : null // placeholder
  const delta = session.delta_to_pb

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center gap-3">
        <Link to="/sessions" className="text-gray-500 hover:text-white text-sm">← Sessions</Link>
      </div>

      {/* Header */}
      <div className="bg-card border border-border rounded-lg p-5">
        <div className="flex justify-between items-start">
          <div>
            <div className="text-white font-bold text-base">{session.car_name}</div>
            <div className="text-gray-400 text-sm">{session.track_name}</div>
            <div className="text-gray-600 text-xs mt-1">
              {new Date(session.session_date).toLocaleString('en-GB')}
              {session.air_temp && ` · ${session.air_temp}°C air`}
              {session.track_temp && ` / ${session.track_temp}°C track`}
              {session.weather && ` · ${session.weather}`}
            </div>
          </div>
          <div className="text-right">
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">Best lap</div>
            <div className="text-white font-mono font-bold text-lg">{fmtTime(session.best_lap_time)}</div>
            {delta != null && (
              <div className={`font-mono text-sm ${delta >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                {delta >= 0 ? '+' : ''}{delta.toFixed(3)}s vs PB
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 border-t border-border mt-4 pt-4">
          <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">Average lap</div>
            <div className="text-white font-mono mt-1">{fmtTime(session.avg_lap_time)}</div>
          </div>
          <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">Laps completed</div>
            <div className="text-white font-mono mt-1">{session.lap_count || '—'}</div>
          </div>
          <div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wider">PB for combo</div>
            <div className="text-white font-mono mt-1">{fmtTime(pb?.best_lap_time)}</div>
          </div>
        </div>
      </div>

      {/* Telemetry chart */}
      <div className="bg-card border border-border rounded-lg p-5">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">Telemetry — throttle / brake / speed</div>
        <TelemetryChart rawData={session.raw_json} />
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Sector deltas */}
        <SectorDelta
          s1={session.sector_1_best && pb ? session.sector_1_best - (pb.sector_1_best ?? session.sector_1_best) : null}
          s2={session.sector_2_best && pb ? session.sector_2_best - (pb.sector_2_best ?? session.sector_2_best) : null}
          s3={session.sector_3_best && pb ? session.sector_3_best - (pb.sector_3_best ?? session.sector_3_best) : null}
        />

        {/* Tyre card */}
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Tyre temperatures</div>
          <TyreCard tyreData={tyres} />
        </div>
      </div>

      {/* Coaching */}
      <div>
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">AI Coaching</div>
        <CoachingCard coaching={coaching} />
      </div>
    </div>
  )
}
