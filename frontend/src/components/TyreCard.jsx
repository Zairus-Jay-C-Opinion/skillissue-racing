import React from 'react'

function Icon({ name, className = '' }) {
  return <span className={`material-symbols-outlined select-none ${className}`}>{name}</span>
}

function tyreFillColor(temp) {
  if (temp == null) return { border: 'border-text-dim', fill: 'bg-white/10', text: 'text-text-dim' }
  if (temp < 70)  return { border: 'border-blue-400',   fill: 'bg-blue-400/20',   text: 'text-blue-300' }
  if (temp < 80)  return { border: 'border-blue-300',   fill: 'bg-blue-300/25',   text: 'text-blue-200' }
  if (temp <= 105) return { border: 'border-teal',      fill: 'bg-teal/20',       text: 'text-teal' }
  if (temp <= 115) return { border: 'border-warning',   fill: 'bg-warning/20',    text: 'text-warning' }
  return { border: 'border-negative', fill: 'bg-negative/20', text: 'text-negative' }
}

function tyreFillPct(temp) {
  if (temp == null) return 0
  return Math.min(Math.max((temp / 130) * 100, 10), 100)
}

function TyreCorner({ label, temp }) {
  const { border, fill, text } = tyreFillColor(temp)
  const pct = tyreFillPct(temp)
  return (
    <div className="glass-low rounded p-3 flex flex-col items-center gap-2 relative">
      <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider self-start">{label}</span>
      <div className={`w-12 h-16 border-2 ${border} rounded flex items-center justify-center relative overflow-hidden`}>
        <div
          className={`absolute bottom-0 w-full ${fill} transition-all duration-500`}
          style={{ height: `${pct}%` }}
        />
        <span className={`font-mono text-xs font-bold relative z-10 ${text}`}>
          {temp != null ? `${temp.toFixed(0)}°` : '—'}
        </span>
      </div>
    </div>
  )
}

export default function TyreCard({ tyreData }) {
  const last = Array.isArray(tyreData) ? tyreData[tyreData.length - 1] : tyreData

  if (!last) {
    return (
      <div className="glass rounded-lg p-5 flex flex-col gap-2 min-h-[180px] justify-center">
        <Icon name="tire_repair" className="text-[32px] text-text-dim" />
        <p className="text-muted text-sm mt-1">No tyre data for this session.</p>
      </div>
    )
  }

  return (
    <div className="glass rounded-lg p-5 flex flex-col gap-4 h-full">
      <h2 className="text-white font-semibold flex items-center gap-2">
        <Icon name="tire_repair" className="text-[18px] text-text-secondary" />
        Tyre Status
      </h2>

      <div className="grid grid-cols-2 gap-3 flex-1">
        <TyreCorner label="FL" temp={last.fl_avg_temp} />
        <TyreCorner label="FR" temp={last.fr_avg_temp} />
        <TyreCorner label="RL" temp={last.rl_avg_temp} />
        <TyreCorner label="RR" temp={last.rr_avg_temp} />
      </div>

      {last.recommendation && (
        <div className="border-l-2 border-warning bg-warning/5 px-3 py-2 rounded-r">
          <p className="text-xs text-muted leading-relaxed">
            <span className="text-warning font-semibold">Rec: </span>
            {last.recommendation}
          </p>
        </div>
      )}
    </div>
  )
}
