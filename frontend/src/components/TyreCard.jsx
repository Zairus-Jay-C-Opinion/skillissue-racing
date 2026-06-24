import React from 'react'

function tempColor(temp) {
  if (temp == null) return 'bg-gray-700 text-gray-400'
  if (temp < 70) return 'bg-blue-900 text-blue-300'
  if (temp < 75) return 'bg-blue-700 text-blue-100'
  if (temp <= 105) return 'bg-green-800 text-green-200'
  if (temp <= 115) return 'bg-amber-700 text-amber-100'
  return 'bg-red-800 text-red-200'
}

function Corner({ label, temp }) {
  return (
    <div className={`rounded p-3 text-center ${tempColor(temp)}`}>
      <div className="text-[10px] uppercase tracking-wider opacity-70">{label}</div>
      <div className="text-xl font-bold mt-1">{temp != null ? `${temp.toFixed(1)}°` : '—'}</div>
    </div>
  )
}

export default function TyreCard({ tyreData }) {
  // Use the last lap's data for a session summary view
  const last = Array.isArray(tyreData) ? tyreData[tyreData.length - 1] : tyreData
  if (!last) {
    return (
      <div className="bg-card border border-border rounded-lg p-5 text-gray-500 text-sm">
        No tyre data available.
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-lg p-5 space-y-3">
      <div className="grid grid-cols-2 gap-2">
        <Corner label="FL" temp={last.fl_avg_temp} />
        <Corner label="FR" temp={last.fr_avg_temp} />
        <Corner label="RL" temp={last.rl_avg_temp} />
        <Corner label="RR" temp={last.rr_avg_temp} />
      </div>
      {last.recommendation && (
        <p className="text-xs text-gray-400 leading-relaxed border-t border-border pt-3">
          {last.recommendation}
        </p>
      )}
    </div>
  )
}
