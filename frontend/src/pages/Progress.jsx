import React, { useEffect, useState } from 'react'
import { api } from '../api'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'

function fmtTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3).padStart(6, '0')
  return `${m}:${sec}`
}

export default function Progress() {
  const [narratives, setNarratives] = useState([])
  const [pbs, setPbs] = useState([])
  const [generating, setGenerating] = useState(false)
  const [pbSessions, setPbSessions] = useState([])

  useEffect(() => {
    Promise.all([api.getNarratives(), api.getPBs(), api.getSessions({ limit: 200 })]).then(([n, p, s]) => {
      setNarratives(n)
      setPbs(p)
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

  // Build PB trend data per car+track combo
  const pbTrendData = React.useMemo(() => {
    const combos = {}
    pbSessions.forEach(s => {
      if (!s.best_lap_time) return
      const key = `${s.car_name} @ ${s.track_name}`
      if (!combos[key]) combos[key] = []
      combos[key].push({ date: s.session_date.slice(0, 10), time: s.best_lap_time })
    })
    // Keep the best per day per combo
    const result = {}
    for (const [key, points] of Object.entries(combos)) {
      const byDay = {}
      points.forEach(p => {
        if (!byDay[p.date] || p.time < byDay[p.date]) byDay[p.date] = p.time
      })
      result[key] = Object.entries(byDay).sort((a, b) => a[0].localeCompare(b[0])).map(([d, t]) => ({ date: d, time: +t.toFixed(4) }))
    }
    return result
  }, [pbSessions])

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-white">Progress</h1>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="text-xs px-3 py-1.5 bg-accent rounded text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {generating ? 'Generating…' : 'Generate this week\'s report'}
        </button>
      </div>

      {/* PB trend charts */}
      {Object.entries(pbTrendData).slice(0, 3).map(([combo, points]) => (
        <div key={combo} className="bg-card border border-border rounded-lg p-5">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-3">{combo} — lap time trend</div>
          {points.length < 2 ? (
            <div className="text-gray-600 text-xs">Need at least 2 sessions to show a trend.</div>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <LineChart data={points} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
                <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 10 }} />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  tickFormatter={v => fmtTime(v)}
                  width={52}
                />
                <Tooltip
                  contentStyle={{ background: '#1a1d2e', border: '1px solid #2a2d3e', fontSize: 11 }}
                  formatter={v => [fmtTime(v), 'Best lap']}
                />
                <Line type="monotone" dataKey="time" stroke="#3b82f6" dot={{ r: 3 }} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      ))}

      {/* Weekly narratives */}
      <div className="space-y-3">
        <div className="text-xs text-gray-500 uppercase tracking-wider">Weekly reports</div>
        {narratives.length === 0 && (
          <div className="text-gray-600 text-sm">No reports yet. Generate your first one above.</div>
        )}
        {narratives.map(n => (
          <div key={n.id} className="bg-card border border-border rounded-lg p-5">
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-gray-500">
                {new Date(n.week_start).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                {' – '}
                {new Date(n.week_end).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
              </div>
              {n.delta_seconds != null && (
                <div className={`text-xs font-mono ${n.delta_seconds < 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {n.delta_seconds < 0 ? '' : '+'}{n.delta_seconds.toFixed(3)}s vs prev week
                </div>
              )}
            </div>
            <p className="text-gray-300 text-sm leading-relaxed">{n.narrative_text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
