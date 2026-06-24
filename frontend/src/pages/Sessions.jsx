import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

function fmtTime(s) {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(3).padStart(6, '0')
  return `${m}:${sec}`
}

export default function Sessions() {
  const [data, setData] = useState(null)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ car: '', track: '' })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const params = { page, limit: 20 }
    if (filters.car) params.car = filters.car
    if (filters.track) params.track = filters.track
    api.getSessions(params).then(res => { setData(res); setLoading(false) })
  }, [page, filters])

  const totalPages = data ? Math.ceil(data.total / 20) : 1

  return (
    <div className="space-y-4 max-w-4xl">
      <h1 className="text-lg font-bold text-white">Sessions</h1>

      {/* Filters */}
      <div className="flex gap-3">
        {['car', 'track'].map(key => (
          <input
            key={key}
            placeholder={`Filter by ${key}…`}
            value={filters[key]}
            onChange={e => { setFilters(f => ({ ...f, [key]: e.target.value })); setPage(1) }}
            className="bg-card border border-border rounded px-3 py-1.5 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-accent"
          />
        ))}
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-gray-500 text-[10px] uppercase tracking-wider">
              <th className="px-4 py-2 text-left">Date</th>
              <th className="px-4 py-2 text-left">Car</th>
              <th className="px-4 py-2 text-left">Track</th>
              <th className="px-4 py-2 text-right">Best lap</th>
              <th className="px-4 py-2 text-right">Δ PB</th>
              <th className="px-4 py-2 text-right">Laps</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-600 text-xs">Loading…</td></tr>
            )}
            {!loading && data?.items.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-600 text-xs">No sessions found.</td></tr>
            )}
            {!loading && data?.items.map(s => {
              const delta = s.delta_to_pb
              return (
                <tr key={s.id} className="border-b border-border hover:bg-border/40 transition-colors">
                  <td className="px-4 py-2.5 text-gray-400 text-xs">
                    {new Date(s.session_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })}
                  </td>
                  <td className="px-4 py-2.5 text-white">{s.car_name}</td>
                  <td className="px-4 py-2.5 text-gray-300">{s.track_name}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{fmtTime(s.best_lap_time)}</td>
                  <td className={`px-4 py-2.5 text-right font-mono ${delta == null ? 'text-gray-600' : delta >= 0 ? 'text-red-400' : 'text-green-400'}`}>
                    {delta == null ? '—' : `${delta >= 0 ? '+' : ''}${delta.toFixed(3)}s`}
                  </td>
                  <td className="px-4 py-2.5 text-right text-gray-400">{s.lap_count || '—'}</td>
                  <td className="px-4 py-2.5">
                    <Link to={`/sessions/${s.id}`} className="text-accent text-xs hover:underline">→</Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex gap-2 justify-end text-xs">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-3 py-1 bg-card border border-border rounded disabled:opacity-40 hover:border-accent">
            ←
          </button>
          <span className="px-3 py-1 text-gray-500">{page} / {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="px-3 py-1 bg-card border border-border rounded disabled:opacity-40 hover:border-accent">
            →
          </button>
        </div>
      )}
    </div>
  )
}
