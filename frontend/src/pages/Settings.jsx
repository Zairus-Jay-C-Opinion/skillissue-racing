import React, { useEffect, useState } from 'react'
import { api } from '../api'

function Icon({ name, className = '' }) {
  return <span className={`material-symbols-outlined select-none ${className}`}>{name}</span>
}

function Field({ label, settingKey, value, onChange, type = 'text', description, placeholder }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">{label}</label>
      {description && <p className="text-[11px] text-text-dim leading-relaxed">{description}</p>}
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={e => onChange(settingKey, e.target.value)}
        className="w-full glass-low rounded px-3 py-2.5 text-sm text-white focus:outline-none border border-transparent focus:border-brand/40 font-mono transition-colors placeholder-text-dim"
      />
    </div>
  )
}

function Section({ icon, title, children }) {
  return (
    <div className="glass rounded-lg p-5 space-y-4">
      <div className="flex items-center gap-2 border-b border-glass-border pb-3">
        <Icon name={icon} className="text-[16px] text-text-secondary" />
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">{title}</span>
      </div>
      {children}
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
    api.getSettings().then(s => setSettings(s))
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
    setTestResult(null)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleTestGemini = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      await api.testGeminiKey(geminiKey)
      setTestResult({ ok: true })
    } catch (e) {
      setTestResult({ ok: false, error: e.message })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="p-6 space-y-5 max-w-2xl">
      <h1 className="text-xl font-bold text-white">Settings</h1>

      <Section icon="folder_open" title="Folder paths">
        <Field
          label="iRacing telemetry folder"
          settingKey="telemetry_folder"
          value={settings.telemetry_folder || ''}
          onChange={handleChange}
          placeholder="C:\Users\...\Documents\iRacing\telemetry"
          description="Where iRacing writes .ibt files. Default: Documents/iRacing/telemetry"
        />
        <Field
          label="Setups watch folder"
          settingKey="setups_watch_folder"
          value={settings.setups_watch_folder || ''}
          onChange={handleChange}
          placeholder="Leave blank to disable"
          description="Drop .sto setup files here and they'll be auto-installed."
        />
      </Section>

      <Section icon="auto_awesome" title="Gemini API">
        <div className="space-y-2">
          <label className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider">API key</label>
          <p className="text-[11px] text-text-dim leading-relaxed">
            Get a free key from <span className="text-brand">aistudio.google.com</span>. Free tier: 1,500 requests/day.
          </p>
          <div className="flex gap-2">
            <input
              type="password"
              placeholder={settings.gemini_api_key === '••••••••' ? 'Key saved — enter new to replace' : 'Paste API key here'}
              value={geminiKey}
              onChange={e => { setGeminiKey(e.target.value); setTestResult(null) }}
              className="flex-1 glass-low rounded px-3 py-2.5 text-sm text-white focus:outline-none border border-transparent focus:border-brand/40 font-mono transition-colors placeholder-text-dim"
            />
            <button
              onClick={handleTestGemini}
              disabled={testing || !geminiKey}
              className="px-4 py-2.5 glass-low rounded text-xs text-text-secondary hover:text-white disabled:opacity-30 transition-colors border border-glass-border"
            >
              {testing ? 'Testing…' : 'Test'}
            </button>
          </div>
          {testResult?.ok && (
            <p className="flex items-center gap-1.5 text-teal text-xs">
              <Icon name="check_circle" className="text-[14px]" />
              Key is valid.
            </p>
          )}
          {testResult?.ok === false && (
            <p className="flex items-start gap-1.5 text-negative text-xs font-mono break-all">
              <Icon name="error" className="text-[14px] shrink-0 mt-0.5" />
              {testResult.error}
            </p>
          )}
          {geminiKey && (
            <button onClick={handleSaveGeminiKey} className="text-xs text-brand hover:opacity-80 transition-opacity">
              Save key
            </button>
          )}
        </div>
      </Section>

      <Section icon="open_in_new" title="Overlay position">
        <div className="flex gap-4">
          <Field label="X (px)" settingKey="overlay_position_x" value={settings.overlay_position_x || ''} onChange={handleChange} placeholder="0" />
          <Field label="Y (px)" settingKey="overlay_position_y" value={settings.overlay_position_y || ''} onChange={handleChange} placeholder="0" />
        </div>
      </Section>

      <button
        onClick={handleSave}
        className="flex items-center gap-2 px-5 py-2.5 bg-brand/90 hover:bg-brand rounded text-white text-sm transition-colors"
      >
        <Icon name={saved ? 'check' : 'save'} className="text-[16px]" />
        {saved ? 'Saved' : 'Save settings'}
      </button>
    </div>
  )
}
