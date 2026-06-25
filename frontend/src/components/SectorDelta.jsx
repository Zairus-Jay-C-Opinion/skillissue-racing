import React from 'react'

function Bar({ label, delta }) {
  const isNull = delta == null
  const positive = delta > 0 // positive = slower than PB
  const pct = Math.min(Math.abs(delta || 0) * 200, 100) // scale: 0.5s = full bar

  return (
    <div className="flex items-center gap-3">
      <span className="text-text-secondary text-xs font-mono w-6">{label}</span>
      <div className="flex-1 h-4 glass-low rounded overflow-hidden relative">
        {!isNull && (
          <div
            className={`h-full rounded transition-all duration-500 ${positive ? 'bg-negative/30' : 'bg-teal/25'}`}
            style={{ width: `${pct}%` }}
          />
        )}
      </div>
      <span className={`text-xs font-mono w-16 text-right ${
        isNull ? 'text-text-dim' : positive ? 'text-negative' : 'text-teal'
      }`}>
        {isNull ? '—' : `${delta > 0 ? '+' : ''}${delta.toFixed(3)}s`}
      </span>
    </div>
  )
}

export default function SectorDelta({ s1, s2, s3 }) {
  return (
    <div className="glass rounded-lg p-5 space-y-3 h-full">
      <div className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">vs PB</div>
      <Bar label="S1" delta={s1} />
      <Bar label="S2" delta={s2} />
      <Bar label="S3" delta={s3} />
    </div>
  )
}
