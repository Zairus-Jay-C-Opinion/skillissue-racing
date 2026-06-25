import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

function Icon({ name, className = '' }) {
  return <span className={`material-symbols-outlined select-none ${className}`}>{name}</span>
}

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
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">Sessions</h1>
        {data && (
          <span className="text-xs text-text-secondary font-mono">{data.total} total</span>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        {['car', 'track'].map(key => (
          <div key={key} className="relative">
            <Icon name="search" className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[14px] text-text-dim pointer-events-none" />
            <input
              placeholder={`Filter by ${key}…`}
              value={filters[key]}
              onChange={e => { setFilters(f => ({ ...f, [key]: e.target.value })); setPage(1) }}
              className="glass-low rounded px-3 py-2 pl-8 text-sm text-white placeholder-text-dim focus:outline-none focus:border-brand/50 border border-transparent focus:border-brand/40 transition-colors"
            />
          </div>
        ))}
      </div>

      {/* Table */}
      <div className="glass rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-glass-border">
              <th className="px-4 py-3 text-left text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Date</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Car</th>
              <th className="px-4 py-3 text-left text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Track</th>
              <th className="px-4 py-3 text-right text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Best lap</th>
              <th className="px-4 py-3 text-right text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Δ PB</th>
              <th className="px-4 py-3 text-right text-[10px] font-semibold text-text-secondary uppercase tracking-wider">Laps</th>
              <th className="px-4 py-3 w-8" />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center">
                  <span className="text-text-dim text-xs animate-pulse">Loading…</span>
                </td>
              </tr>
            )}
            {!loading && data?.items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-10 text-center">
                  <div className="flex flex-col items-center gap-2">
                    <Icon name="flag" className="text-[28px] text-text-dim" />
                    <span className="text-text-dim text-xs">No sessions found.</span>
                  </div>
                </td>
              </tr>
            )}
            {!loading && data?.items.map(s => {
              const delta = s.delta_to_pb
              const borderColor = delta == null
                ? 'border-l-text-dim/30'
                : delta < 0 ? 'border-l-teal' : 'border-l-negative'
              return (
                <tr
                  key={s.id}
                  className={`border-b border-glass-border/50 hover:bg-white/5 transition-colors border-l-2 ${borderColor} group`}
                >
                  <td className="px-4 py-3 text-text-dim text-xs font-mono">
                    {new Date(s.session_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })}
                  </td>
                  <td className="px-4 py-3 text-white text-sm">{s.car_name}</td>
                  <td className="px-4 py-3 text-text-secondary text-sm">{s.track_name}</td>
                  <td className="px-4 py-3 text-right font-mono text-white">{fmtTime(s.best_lap_time)}</td>
                  <td className={`px-4 py-3 text-right font-mono ${
                    delta == null ? 'text-text-dim' : delta < 0 ? 'text-teal' : 'text-negative'
                  }`}>
                    {delta == null ? '—' : `${delta >= 0 ? '+' : ''}${delta.toFixed(3)}s`}
                  </td>
                  <td className="px-4 py-3 text-right text-text-dim font-mono text-sm">{s.lap_count || '—'}</td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/sessions/${s.id}`}
                      className="text-text-dim group-hover:text-brand transition-colors"
                    >
                      <Icon name="chevron_right" className="text-[16px]" />
                    </Link>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center gap-2 justify-end text-xs">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="glass-low px-3 py-1.5 rounded text-text-secondary hover:text-white disabled:opacity-30 transition-colors"
          >
            <Icon name="chevron_left" className="text-[14px]" />
          </button>
          <span className="text-text-secondary font-mono px-2">{page} / {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="glass-low px-3 py-1.5 rounded text-text-secondary hover:text-white disabled:opacity-30 transition-colors"
          >
            <Icon name="chevron_right" className="text-[14px]" />
          </button>
        </div>
      )}
    </div>
  )
}
