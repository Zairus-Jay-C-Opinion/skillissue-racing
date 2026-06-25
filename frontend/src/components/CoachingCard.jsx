import React from 'react'

function WarningIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <path d="M12 3L21.5 20H2.5L12 3Z" stroke="#e85d04" strokeWidth="1.8" strokeLinejoin="round" />
      <line x1="12" y1="9" x2="12" y2="14" stroke="#e85d04" strokeWidth="2" strokeLinecap="round" />
      <circle cx="12" cy="17.5" r="1" fill="#e85d04" />
    </svg>
  )
}

function TyreIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="9.5" stroke="#41eec2" strokeWidth="1.8" />
      <circle cx="12" cy="12" r="4" stroke="#41eec2" strokeWidth="1.5" />
      <line x1="12" y1="2.5" x2="12" y2="5.5" stroke="#41eec2" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="12" y1="18.5" x2="12" y2="21.5" stroke="#41eec2" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="2.5" y1="12" x2="5.5" y2="12" stroke="#41eec2" strokeWidth="1.5" strokeLinecap="round" />
      <line x1="18.5" y1="12" x2="21.5" y2="12" stroke="#41eec2" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  )
}

function CarIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="9.5" stroke="#f5a623" strokeWidth="1.8" />
      <path d="M7.5 13.5h9" stroke="#f5a623" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M8 13.5l1.5-3.5h5l1.5 3.5" stroke="#f5a623" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="9.5" cy="15" r="1.2" fill="#f5a623" />
      <circle cx="14.5" cy="15" r="1.2" fill="#f5a623" />
    </svg>
  )
}

function AIIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
      <circle cx="12" cy="12" r="10" stroke="#41eec2" strokeWidth="1.5" strokeDasharray="2.5 2" />
      <rect x="7.5" y="7.5" width="9" height="9" rx="1.5" stroke="#41eec2" strokeWidth="1.5" />
      <text x="12" y="15.2" textAnchor="middle" fill="#41eec2" fontSize="5.5" fontWeight="700" fontFamily="monospace">AI</text>
      <line x1="10" y1="5.5" x2="10" y2="7.5" stroke="#41eec2" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="14" y1="5.5" x2="14" y2="7.5" stroke="#41eec2" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="10" y1="16.5" x2="10" y2="18.5" stroke="#41eec2" strokeWidth="1.2" strokeLinecap="round" />
      <line x1="14" y1="16.5" x2="14" y2="18.5" stroke="#41eec2" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  )
}

const TIP_ICONS = [WarningIcon, CarIcon, TyreIcon]

export default function CoachingCard({ coaching }) {
  if (!coaching) {
    return (
      <div className="glass rounded-lg p-5 flex flex-col gap-2 min-h-[180px] justify-center">
        <AIIcon size={32} />
        <p className="text-muted text-sm mt-1">
          No coaching yet — analysis will appear after the next session is processed.
        </p>
      </div>
    )
  }

  return (
    <div className="glass rounded-lg p-5 flex flex-col gap-4">
      {/* Header */}
      <h2 className="text-white font-semibold flex items-center gap-2">
        <AIIcon size={18} />
        Session Summary
      </h2>

      {/* Headline */}
      <p className="text-sm text-muted leading-relaxed">{coaching.headline}</p>

      {/* 3 tip cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {coaching.tips.map((tip, i) => {
          const Icon = TIP_ICONS[i] ?? WarningIcon
          return (
            <div key={i} className="glass-low rounded p-4 flex flex-col gap-2 hover:bg-white/5 transition-colors">
              <div className="flex items-center gap-2">
                <Icon size={16} />
                <span className="text-xs font-semibold text-white leading-tight">{tip.title}</span>
              </div>
              <p className="text-xs text-muted leading-relaxed">{tip.detail}</p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
