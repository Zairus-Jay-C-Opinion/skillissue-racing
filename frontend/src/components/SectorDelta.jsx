import React from 'react'

function Bar({ label, delta }) {
  const isNull = delta == null
  const positive = delta > 0 // positive = slower than PB
  const pct = Math.min(Math.abs(delta || 0) * 200, 100) // scale: 0.5s = full bar

  return (
    <div className="flex items-center gap-3">
      <span className="text-gray-400 text-xs w-6">{label}</span>
      <div className="flex-1 h-5 bg-border rounded overflow-hidden relative">
        {!isNull && (
          <div
            className={`h-full rounded transition-all ${positive ? 'bg-red-dim' : 'bg-green-dim'}`}
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
      <span className={`text-xs font-mono w-16 text-right ${isNull ? 'text-gray-600' : positive ? 'text-red-400' : 'text-green-400'}`}>
        {isNull ? '—' : `${delta > 0 ? '+' : ''}${delta.toFixed(3)}s`}
      </span>
    </div>
  )
}

export default function SectorDelta({ s1, s2, s3 }) {
  return (
    <div className="bg-card border border-border rounded-lg p-5 space-y-3">
      <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Sector deltas vs PB</div>
      <Bar label="S1" delta={s1} />
      <Bar label="S2" delta={s2} />
      <Bar label="S3" delta={s3} />
    </div>
  )
}
