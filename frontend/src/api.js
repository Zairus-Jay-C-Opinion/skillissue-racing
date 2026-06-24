const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const api = {
  getSessions: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return req(`/sessions${qs ? '?' + qs : ''}`)
  },
  getSession: (id) => req(`/sessions/${id}`),
  getCoaching: (id) => req(`/sessions/${id}/coaching`),
  getTyres: (id) => req(`/sessions/${id}/tyres`),

  getPBs: () => req('/pbs'),
  getPB: (car, track) => req(`/pbs/${encodeURIComponent(car)}/${encodeURIComponent(track)}`),

  getNarratives: () => req('/progress/narrative'),
  generateNarrative: () => req('/progress/generate', { method: 'POST' }),

  getSettings: () => req('/settings'),
  updateSetting: (key, value) => req(`/settings/${key}`, {
    method: 'PUT',
    body: JSON.stringify({ value }),
  }),

  getStatus: () => req('/status'),
  testGeminiKey: (key) => req('/gemini/test', {
    method: 'POST',
    body: JSON.stringify({ key }),
  }),
}
