import React, { useState } from 'react'
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
  const [testing, setTesting] = useState(false)

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
            <div key={i} className={`h-1 flex-1 rounded-full transition-colors ${i <= step ? 'bg-brand' : 'bg-border'}`} />
          ))}
        </div>

        <div className="bg-card border border-border rounded-lg p-8 space-y-6">
          <h2 className="text-xl font-bold text-white">{current.title}</h2>

          {/* Welcome */}
          {step === 0 && (
            <div className="space-y-3 text-sm text-gray-400">
              <p>Skill Issue Racing runs alongside <strong className="text-white">Garage 61</strong> — it doesn't replace it.</p>
              <p>It reads the same iRacing telemetry files and adds features Garage 61 doesn't have:</p>
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
              <p className="text-sm text-gray-400">
                Where does iRacing save .ibt telemetry files? The default path is shown below — only change it if you've moved your iRacing documents folder.
              </p>
              <input
                type="text"
                placeholder="C:\Users\You\Documents\iRacing\telemetry"
                value={telemetryFolder}
                onChange={e => setTelemetryFolder(e.target.value)}
                className="w-full bg-surface border border-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand font-mono"
              />
              <p className="text-[11px] text-gray-600">Leave blank to use the default (Documents/iRacing/telemetry).</p>
            </div>
          )}

          {/* Setups folder */}
          {step === 2 && (
            <div className="space-y-3">
              <p className="text-sm text-gray-400">
                Choose a folder to drop <code className="text-white">.sto</code> setup files into. The agent will automatically copy them to the correct iRacing setups folder.
              </p>
              <input
                type="text"
                placeholder="C:\Users\You\Downloads\iRacing-setups"
                value={setupsFolder}
                onChange={e => setSetupFolder(e.target.value)}
                className="w-full bg-surface border border-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand font-mono"
              />
            </div>
          )}

          {/* Gemini key */}
          {step === 3 && (
            <div className="space-y-3">
              <p className="text-sm text-gray-400">
                Skill Issue Racing uses Gemini 2.0 Flash for AI coaching. Get a free API key at{' '}
                <span className="text-brand">aistudio.google.com</span> — free tier is 1,500 requests/day.
              </p>
              <div className="flex gap-2">
                <input
                  type="password"
                  placeholder="AIza…"
                  value={geminiKey}
                  onChange={e => { setGeminiKey(e.target.value); setGeminiStatus(null) }}
                  className="flex-1 bg-surface border border-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-brand font-mono"
                />
                <button
                  onClick={testGemini}
                  disabled={testing || !geminiKey}
                  className="px-3 py-2 bg-border rounded text-xs text-white hover:bg-gray-600 disabled:opacity-40"
                >
                  {testing ? '…' : 'Test'}
                </button>
              </div>
              {geminiStatus?.ok && <p className="text-green-400 text-xs">Key is valid — you're good to go.</p>}
              {geminiStatus?.ok === false && (
                <p className="text-red-400 text-xs font-mono break-all">{geminiStatus.error}</p>
              )}
              <p className="text-[11px] text-gray-600">You can skip this and add the key later in Settings.</p>
            </div>
          )}

          {/* iRacing check */}
          {step === 4 && (
            <div className="space-y-3 text-sm text-gray-400">
              <p>Before continuing, make sure telemetry is enabled in iRacing:</p>
              <ol className="space-y-2 pl-4">
                <li className="text-white">1. Launch iRacing and enter a session (practice is fine)</li>
                <li className="text-white">2. Press <code className="bg-border px-1 rounded">Alt + L</code> to enable telemetry logging</li>
                <li className="text-white">3. Complete a few laps, then exit the session</li>
              </ol>
              <p>The agent will automatically detect and process your .ibt file when you return.</p>
            </div>
          )}

          {/* Done */}
          {step === 5 && (
            <div className="space-y-3 text-sm text-gray-400">
              <p className="text-white font-medium">Setup complete.</p>
              <p>The agent is watching your telemetry folder. After your next iRacing session, coaching and tyre data will appear automatically on the dashboard.</p>
              <p>The overlay will activate when iRacing is running.</p>
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
              <button onClick={next} className="px-5 py-2 bg-brand rounded text-white text-sm hover:bg-blue-700">
                Continue →
              </button>
            ) : (
              <button onClick={finish} className="px-5 py-2 bg-green-700 rounded text-white text-sm hover:bg-green-600">
                Open Dashboard →
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
