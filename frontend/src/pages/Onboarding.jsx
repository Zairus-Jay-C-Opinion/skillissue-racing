import React, { useState, useEffect } from 'react'
import { api } from '../api'

const STEPS = [
  { id: 'welcome', title: 'Welcome to Skill Issue Racing' },
  { id: 'telemetry', title: 'Telemetry folder' },
  { id: 'setups', title: 'Setups watch folder' },
  { id: 'gemini', title: 'Gemini API key' },
  { id: 'iracing', title: 'iRacing check' },
  { id: 'done', title: 'You\'re all set' },
]

export default function Onboarding({ onComplete }) {
  const [step, setStep] = useState(0)
  const [telemetryFolder, setTelemetryFolder] = useState('')
  const [setupsFolder, setSetupFolder] = useState('')
  const [geminiKey, setGeminiKey] = useState('')
  const [geminiStatus, setGeminiStatus] = useState(null)
  const [geminiPreConfigured, setGeminiPreConfigured] = useState(false)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    api.getGeminiStatus().then(s => setGeminiPreConfigured(s.configured)).catch(() => {})
  }, [])

  const next = () => setStep(s => Math.min(s + 1, STEPS.length - 1))

  const testGemini = async () => {
    setTesting(true)
    try {
      await api.testGeminiKey(geminiKey)
      await api.updateSetting('gemini_api_key', geminiKey)
      setGeminiStatus({ ok: true })
    } catch (e) {
      setGeminiStatus({ ok: false, error: e.message })
    } finally {
      setTesting(false)
    }
  }

  const finish = async () => {
    if (telemetryFolder) await api.updateSetting('telemetry_folder', telemetryFolder)
    if (setupsFolder) await api.updateSetting('setups_watch_folder', setupsFolder)
    await api.updateSetting('onboarding_complete', 'true')
    onComplete()
  }

  const current = STEPS[step]

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface p-6">
      <div className="w-full max-w-lg space-y-6">
        {/* Step indicator */}
        <div className="flex gap-1.5">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i <= step ? 'bg-brand' : 'bg-white/10'}`} />
          ))}
        </div>

        <div className="glass rounded-lg p-8 space-y-6">
          <h2 className="text-xl font-bold text-white">{current.title}</h2>

          {/* Welcome */}
          {step === 0 && (
            <div className="space-y-3 text-sm text-text-secondary">
              <p>Skill Issue Racing reads your iRacing telemetry files and adds AI-powered coaching and a real-time overlay.</p>
              <p>What you get:</p>
              <ul className="space-y-1.5 pl-4">
                {['AI post-session coaching (Gemini)', 'Real-time delta overlay', 'Tyre temperature advisor', 'Auto setup installer', 'Weekly progress narrative'].map(f => (
                  <li key={f} className="text-white text-sm">→ {f}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Telemetry folder */}
          {step === 1 && (
            <div className="space-y-3">
              <p className="text-sm text-text-secondary">
                Where does iRacing save .ibt telemetry files? Only change this if you've moved your iRacing documents folder.
              </p>
              <input
                type="text"
                placeholder="C:\Users\You\Documents\iRacing\telemetry"
                value={telemetryFolder}
                onChange={e => setTelemetryFolder(e.target.value)}
                className="w-full glass-low border border-glass-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand font-mono"
              />
              <p className="text-[11px] text-text-dim">Leave blank to use the default (Documents/iRacing/telemetry).</p>
            </div>
          )}

          {/* Setups folder */}
          {step === 2 && (
            <div className="space-y-3">
              <p className="text-sm text-text-secondary">
                Choose a folder to drop <code className="text-white">.sto</code> setup files into. The agent will automatically copy them to the correct iRacing setups folder.
              </p>
              <input
                type="text"
                placeholder="C:\Users\You\Downloads\iRacing-setups"
                value={setupsFolder}
                onChange={e => setSetupFolder(e.target.value)}
                className="w-full glass-low border border-glass-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand font-mono"
              />
            </div>
          )}

          {/* Gemini key */}
          {step === 3 && (
            <div className="space-y-3">
              {geminiPreConfigured ? (
                <div className="flex items-center gap-2 glass-low rounded-lg px-4 py-3 border border-teal/20">
                  <span className="text-teal text-sm">✓</span>
                  <p className="text-sm text-text-secondary">API key is already configured. You're good to go — or paste a new key below to replace it.</p>
                </div>
              ) : (
                <p className="text-sm text-text-secondary">
                  Skill Issue Racing uses Gemini 2.0 Flash for AI coaching. Get a free API key at{' '}
                  <span className="text-brand">aistudio.google.com</span> — free tier is 1,500 requests/day.
                </p>
              )}
              <div className="flex gap-2">
                <input
                  type="password"
                  placeholder="AIza…"
                  value={geminiKey}
                  onChange={e => { setGeminiKey(e.target.value); setGeminiStatus(null) }}
                  className="flex-1 glass-low border border-glass-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand font-mono"
                />
                <button
                  onClick={testGemini}
                  disabled={testing || !geminiKey}
                  className="px-3 py-2 glass-low border border-glass-border rounded text-xs text-text-secondary hover:text-white disabled:opacity-40"
                >
                  {testing ? '…' : 'Test'}
                </button>
              </div>
              {geminiStatus?.ok && <p className="text-teal text-xs">Key is valid — you're good to go.</p>}
              {geminiStatus?.ok === false && (
                <p className="text-negative text-xs font-mono break-all">{geminiStatus.error}</p>
              )}
              <p className="text-[11px] text-text-dim">You can skip this and add the key later in Settings.</p>
            </div>
          )}

          {/* iRacing check */}
          {step === 4 && (
            <div className="space-y-3 text-sm text-text-secondary">
              <p>Before continuing, make sure telemetry is enabled in iRacing:</p>
              <ol className="space-y-2 pl-4">
                <li className="text-white">1. Launch iRacing and enter a session (practice is fine)</li>
                <li className="text-white">2. Press <code className="glass-low px-1.5 py-0.5 rounded font-mono text-xs">Alt + L</code> to enable telemetry logging</li>
                <li className="text-white">3. Complete a few laps, then exit the session</li>
              </ol>
              <p>The agent will automatically detect and process your .ibt file when you return.</p>
            </div>
          )}

          {/* Done */}
          {step === 5 && (
            <div className="space-y-3 text-sm text-text-secondary">
              <p className="text-white font-medium">Setup complete.</p>
              <p>The agent is watching your telemetry folder. After your next iRacing session, coaching and tyre data will appear automatically on the dashboard.</p>
              <p>The overlay will activate when iRacing is running. Run it in <span className="text-white">Borderless Windowed</span> mode for best overlay compatibility.</p>
            </div>
          )}

          {/* Navigation */}
          <div className="flex justify-between pt-2">
            <button
              onClick={() => setStep(s => Math.max(0, s - 1))}
              disabled={step === 0}
              className="text-xs text-gray-500 hover:text-white disabled:opacity-0 transition-colors"
            >
              ← Back
            </button>
            {step < STEPS.length - 1 ? (
              <button onClick={next} className="px-5 py-2 bg-brand hover:opacity-90 rounded text-white text-sm transition-opacity">
                Continue →
              </button>
            ) : (
              <button onClick={finish} className="px-5 py-2 bg-teal hover:opacity-90 rounded text-surface text-sm font-semibold transition-opacity">
                Open Dashboard →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
