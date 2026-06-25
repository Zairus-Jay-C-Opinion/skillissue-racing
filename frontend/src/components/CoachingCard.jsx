import React from 'react'

function Icon({ name, className = '' }) {
  return <span className={`material-symbols-outlined select-none ${className}`}>{name}</span>
}

const TIP_ICONS = ['warning', 'speed', 'settings_backup_restore']
const TIP_ICON_COLORS = ['text-brand', 'text-teal', 'text-yellow-400']

export default function CoachingCard({ coaching }) {
  if (!coaching) {
    return (
      <div className="glass rounded-lg p-5 flex flex-col gap-2 min-h-[180px] justify-center">
        <Icon name="psychology" className="text-[32px] text-text-dim" />
        <p className="text-text-secondary text-sm mt-1">
          No coaching yet — analysis will appear after the next session is processed.
        </p>
      </div>
    )
  }

  return (
    <div className="glass rounded-lg p-5 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-white font-semibold flex items-center gap-2">
          <Icon name="psychology" className="text-[18px] text-teal" />
          Session Summary
        </h2>
        <span className="flex items-center gap-1 text-[10px] text-text-secondary bg-white/5 border border-glass-border px-2 py-1 rounded">
          <Icon name="auto_awesome" className="text-[12px] text-teal" />
          Gemini
        </span>
      </div>

      {/* Headline */}
      <p className="text-sm text-text-secondary leading-relaxed">{coaching.headline}</p>

      {/* 3 tip cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {coaching.tips.map((tip, i) => (
          <div key={i} className="glass-low rounded p-4 flex flex-col gap-2 hover:bg-white/5 transition-colors">
            <div className="flex items-center gap-2">
              <Icon name={TIP_ICONS[i] || 'lightbulb'} className={`text-[16px] ${TIP_ICON_COLORS[i] || 'text-brand'}`} />
              <span className="text-xs font-semibold text-white leading-tight">{tip.title}</span>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed">{tip.detail}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
