import React from 'react'

export default function CoachingCard({ coaching, loading }) {
  if (loading) return <div className="bg-card border border-border rounded-lg p-5 animate-pulse h-36" />

  if (!coaching) {
    return (
      <div className="bg-card border border-border rounded-lg p-5 text-gray-500 text-sm">
        No coaching data yet — analysis will appear after the next session.
      </div>
    )
  }

  return (
    <div className="bg-card border border-border rounded-lg p-5 space-y-4">
      <p className="text-blue-400 text-sm font-medium leading-snug">{coaching.headline}</p>
      <ol className="space-y-3">
        {coaching.tips.map((tip, i) => (
          <li key={i} className="flex gap-3">
            <span className="text-accent font-bold text-sm shrink-0 w-5">{i + 1}.</span>
            <div>
              <div className="text-white text-sm font-medium">{tip.title}</div>
              <div className="text-gray-400 text-xs mt-0.5 leading-relaxed">{tip.detail}</div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  )
}
