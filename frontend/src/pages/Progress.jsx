import React, { useEffect, useState } from 'react'
import { api } from '../api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts'

function Icon({ name, className = '' }) {
  return <span className={`material-symbols-outlined select-none ${className}`}>{name}</span>
}

function fmtTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3).padStart(6, '0')
  return `${m}:${sec}`
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="glass rounded px-3 py-2 text-xs">
      <div className="text-text-secondary mb-0.5">{label}</div>
      <div className="text-white font-mono font-bold">{fmtTime(payload[0].value)}</div>
    </div>
  )
}

export default function Progress() {
  const [narratives, setNarratives] = useState([])
  const [generating, setGenerating] = useState(false)
  const [pbSessions, setPbSessions] = useState([])

  useEffect(() => {
    Promise.all([api.getNarratives(), api.getSessions({ limit: 100 })]).then(([n, s]) => {
      setNarratives(n)
      setPbSessions(s.items)
    })
  }, [])

  const handleGenerate = () => {
    setGenerating(true)
    api.generateNarrative()
      .then(() => api.getNarratives().then(setNarratives))
      .catch(e => alert(e.message))
      .finally(() => setGenerating(false))
  }

  const pbTrendData = React.useMemo(() => {
    const combos = {}
    pbSessions.forEach(s => {
      if (!s.best_lap_time) return
      const key = `${s.car_name} @ ${s.track_name}`
      if (!combos[key]) combos[key] = []
      combos[key].push({ date: s.session_date.slice(0, 10), time: s.best_lap_time })
    })
    const result = {}
    for (const [key, points] of Object.entries(combos)) {
      const byDay = {}
      points.forEach(p => {
        if (!byDay[p.date] || p.time < byDay[p.date]) byDay[p.date] = p.time
      })
      result[key] = Object.entries(byDay)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([d, t]) => ({ date: d, time: +t.toFixed(4) }))
    }
    return result
  }, [pbSessions])

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Progress</h1>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 text-xs px-4 py-2 bg-brand/90 hover:bg-brand rounded text-white disabled:opacity-40 transition-colors"
        >
          <Icon name="auto_awesome" className="text-[14px]" />
          {generating ? 'Generating…' : "This week's report"}
        </button>
      </div>

      {/* PB trend charts */}
      {Object.keys(pbTrendData).length === 0 && (
        <div className="glass rounded-lg p-8 flex flex-col items-center gap-3 text-center">
          <Icon name="query_stats" className="text-[36px] text-text-dim" />
          <p className="text-text-secondary text-sm">No trend data yet. Complete more sessions to see lap time improvements.</p>
        </div>
      )}
      {Object.entries(pbTrendData).slice(0, 3).map(([combo, points]) => (
        <div key={combo} className="glass rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-white text-sm font-medium">{combo}</div>
              <div className="text-text-secondary text-[10px] uppercase tracking-wider mt-0.5">Lap time trend</div>
            </div>
            {points.length >= 2 && (() => {
              const first = points[0].time
              const last = points[points.length - 1].time
              const diff = last - first
              return (
                <span className={`font-mono text-xs ${diff < 0 ? 'text-teal' : 'text-negative'}`}>
                  {diff < 0 ? '' : '+'}{diff.toFixed(3)}s overall
                </span>
              )
            })()}
          </div>
          {points.length < 2 ? (
            <p className="text-text-dim text-xs">Need at least 2 sessions to show a trend.</p>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={points} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="date"
                  tick={{ fill: '#888899', fontSize: 10 }}
                  axisLine={{ stroke: 'rgba(255,255,255,0.07)' }}
                  tickLine={false}
                />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fill: '#888899', fontSize: 10 }}
                  tickFormatter={v => fmtTime(v)}
                  width={68}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="time"
                  stroke="#e85d04"
                  dot={{ r: 3, fill: '#e85d04', strokeWidth: 0 }}
                  activeDot={{ r: 5, fill: '#e85d04', strokeWidth: 0 }}
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      ))}

      {/* Weekly narratives */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Icon name="history_edu" className="text-[16px] text-text-secondary" />
          <span className="text-xs text-text-secondary uppercase tracking-wider font-semibold">Weekly reports</span>
        </div>
        {narratives.length === 0 && (
          <div className="glass-low rounded-lg p-6 text-center">
            <p className="text-text-dim text-sm">No reports yet. Generate your first one above.</p>
          </div>
        )}
        {narratives.map(n => (
          <div key={n.id} className="glass rounded-lg p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs text-text-secondary font-mono">
                {new Date(n.week_start).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                {' – '}
                {new Date(n.week_end).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
              </div>
              {n.delta_seconds != null && (
                <span className={`text-xs font-mono ${n.delta_seconds < 0 ? 'text-teal' : 'text-negative'}`}>
                  {n.delta_seconds < 0 ? '' : '+'}{n.delta_seconds.toFixed(3)}s vs prev week
                </span>
              )}
            </div>
            <p className="text-text-secondary text-sm leading-relaxed">{n.narrative_text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
