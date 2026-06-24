import React, { useEffect, useState } from 'react'
import { api } from '../api'

function Field({ label, settingKey, value, onChange, type = 'text', description }) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-gray-400 uppercase tracking-wider">{label}</label>
      {description && <p className="text-[11px] text-gray-600">{description}</p>}
      <input
        type={type}
        value={value}
        onChange={e => onChange(settingKey, e.target.value)}
        className="w-full bg-surface border border-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-accent font-mono"
      />
    </div>
  )
}

export default function Settings() {
  const [settings, setSettings] = useState({})
  const [geminiKey, setGeminiKey] = useState('')
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getSettings().then(s => {
      setSettings(s)
    })
  }, [])

  const handleChange = (key, value) => {
    setSettings(s => ({ ...s, [key]: value }))
  }

  const handleSave = async () => {
    const keys = ['telemetry_folder', 'setups_watch_folder', 'overlay_position_x', 'overlay_position_y']
    await Promise.all(keys.map(k => settings[k] ? api.updateSetting(k, settings[k]) : null))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleSaveGeminiKey = async () => {
    if (!geminiKey) return
    await api.updateSetting('gemini_api_key', geminiKey)
    setGeminiKey('')
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleTestGemini = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      await api.testGeminiKey(geminiKey || 'current')
      setTestResult('valid')
    } catch {
      setTestResult('invalid')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="text-lg font-bold text-white">Settings</h1>

      <div className="bg-card border border-border rounded-lg p-5 space-y-4">
        <div className="text-xs text-gray-500 uppercase tracking-wider border-b border-border pb-2">Folder paths</div>

        <Field
          label="iRacing telemetry folder"
          settingKey="telemetry_folder"
          value={settings.telemetry_folder || ''}
          onChange={handleChange}
          description="Where iRacing writes .ibt files. Default: Documents/iRacing/telemetry"
        />
        <Field
          label="Setups watch folder"
          settingKey="setups_watch_folder"
          value={settings.setups_watch_folder || ''}
          onChange={handleChange}
          description="Drop .sto setup files here and they'll be auto-installed."
        />
      </div>

      <div className="bg-card border border-border rounded-lg p-5 space-y-4">
        <div className="text-xs text-gray-500 uppercase tracking-wider border-b border-border pb-2">Gemini API</div>

        <div className="space-y-1">
          <label className="text-xs text-gray-400 uppercase tracking-wider">API key</label>
          <p className="text-[11px] text-gray-600">
            Get a free key from <span className="text-accent">aistudio.google.com</span>. Free tier: 1,500 requests/day.
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              placeholder={settings.gemini_api_key === '••••••••' ? 'Key saved — enter a new one to replace' : 'Paste API key here'}
              value={geminiKey}
              onChange={e => setGeminiKey(e.target.value)}
              className="flex-1 bg-surface border border-border rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-accent font-mono"
            />
            <button
              onClick={handleTestGemini}
              disabled={testing || !geminiKey}
              className="px-3 py-2 bg-border rounded text-xs text-white hover:bg-gray-600 disabled:opacity-40 transition-colors"
            >
              {testing ? 'Testing…' : 'Test'}
            </button>
          </div>
          {testResult === 'valid' && <p className="text-green-400 text-xs">Key is valid.</p>}
          {testResult === 'invalid' && <p className="text-red-400 text-xs">Key is invalid or Gemini is unreachable.</p>}
          {geminiKey && (
            <button
              onClick={handleSaveGeminiKey}
              className="text-xs text-accent hover:underline"
            >
              Save key
            </button>
          )}
        </div>
      </div>

      <div className="bg-card border border-border rounded-lg p-5 space-y-4">
        <div className="text-xs text-gray-500 uppercase tracking-wider border-b border-border pb-2">Overlay position</div>
        <div className="flex gap-4">
          <Field label="X (px)" settingKey="overlay_position_x" value={settings.overlay_position_x || ''} onChange={handleChange} />
          <Field label="Y (px)" settingKey="overlay_position_y" value={settings.overlay_position_y || ''} onChange={handleChange} />
        </div>
      </div>

      <button
        onClick={handleSave}
        className="px-5 py-2 bg-accent rounded text-white text-sm hover:bg-blue-700 transition-colors"
      >
        {saved ? 'Saved ✓' : 'Save settings'}
      </button>
    </div>
  )
}
