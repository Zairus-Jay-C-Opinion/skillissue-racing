import React, { useMemo } from 'react'
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

export default function TelemetryChart({ rawData }) {
  // rawData is the subsampled array from raw_json
  const data = useMemo(() => {
    if (!rawData) return []
    return rawData.map(f => ({
      t: f.t,
      throttle: f.throttle != null ? +(f.throttle * 100).toFixed(1) : null,
      brake: f.brake != null ? +(f.brake * 100).toFixed(1) : null,
      speed: f.speed,
      gear: f.gear,
    }))
  }, [rawData])

  if (!data.length) {
    return <div className="text-gray-500 text-sm py-8 text-center">No telemetry data.</div>
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a2d3e" />
        <XAxis
          dataKey="t"
          tick={{ fill: '#6b7280', fontSize: 10 }}
          label={{ value: 'Session time (s)', position: 'insideBottomRight', fill: '#6b7280', fontSize: 10 }}
        />
        <YAxis
          yAxisId="pct"
          domain={[0, 100]}
          tick={{ fill: '#6b7280', fontSize: 10 }}
          width={30}
        />
        <YAxis
          yAxisId="speed"
          orientation="right"
          tick={{ fill: '#6b7280', fontSize: 10 }}
          width={36}
        />
        <Tooltip
          contentStyle={{ background: '#1a1d2e', border: '1px solid #2a2d3e', fontSize: 11 }}
          labelStyle={{ color: '#9ca3af' }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Area
          yAxisId="pct"
          type="monotone"
          dataKey="throttle"
          stroke="#22c55e"
          fill="#166534"
          fillOpacity={0.3}
          dot={false}
          name="Throttle %"
          strokeWidth={1.5}
        />
        <Area
          yAxisId="pct"
          type="monotone"
          dataKey="brake"
          stroke="#ef4444"
          fill="#7f1d1d"
          fillOpacity={0.3}
          dot={false}
          name="Brake %"
          strokeWidth={1.5}
        />
        <Line
          yAxisId="speed"
          type="monotone"
          dataKey="speed"
          stroke="#3b82f6"
          dot={false}
          name="Speed kph"
          strokeWidth={1.5}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
