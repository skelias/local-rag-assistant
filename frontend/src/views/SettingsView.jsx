import { useState, useEffect, useRef } from 'react'
import { t, setLang, getLang } from '../i18n'
import { api } from '../api/client'
import useStore from '../store'

const BG_PRESETS = [
  { key: 'preset:default', label: 'bg_default', color: '#0f1115' },
  { key: 'preset:black', label: 'bg_black', color: '#000000' },
  { key: 'preset:navy', label: 'bg_navy', color: '#0a0e1a' },
]

export default function SettingsView() {
  const [config, setConfig] = useState({})
  const [lang, setLangState] = useState(getLang())
  const profile = useStore((s) => s.profile)
  const setProfile = useStore((s) => s.setProfile)
  const bgRef = useRef(null)
  const userRef = useRef(null)
  const aiRef = useRef(null)

  useEffect(() => {
    api.getConfig().then(setConfig).catch(() => {})
  }, [])

  const toggle = (e) => {
    e.currentTarget.classList.toggle('on')
  }

  const handleLang = (e) => {
    const l = e.target.value === 'English' ? 'en' : 'zh'
    setLang(l)
    setLangState(l)
  }

  const handleSave = async () => {
    try {
      for (const [key, value] of Object.entries(config)) {
        await api.putConfig(key, value)
      }
    } catch {
      // backend not running
    }
  }

  const setBackground = (key) => setProfile({ ...profile, background: key })

  const uploadProfile = async (kind) => {
    const input = kind === 'background' ? bgRef : kind === 'avatar_user' ? userRef : aiRef
    const file = input.current?.files?.[0]
    if (!file) return
    try {
      const { url } = await api.uploadProfile(kind, file)
      const field = kind === 'background' ? 'background'
        : kind === 'avatar_user' ? 'avatar_user' : 'avatar_ai'
      setProfile({ ...profile, [field]: url })
    } catch (err) {
      console.error('Upload profile failed:', err)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto flex flex-col gap-5 px-6 py-5">
      {/* LLM */}
      <div className="glass-card rounded-card p-5 flex flex-col gap-4">
        <div className="text-sm font-semibold text-text-p mb-1">{t('model')}</div>
        <Row label={t('provider_primary')}>
          <select className="ctrl"><option>anthropic</option><option>deepseek</option><option>openai</option></select>
        </Row>
        <Row label={t('model_primary')}>
          <input className="ctrl" defaultValue="claude-sonnet-4-5" />
        </Row>
        <Row label={t('provider_fallback')}>
          <select className="ctrl"><option>deepseek</option><option>anthropic</option></select>
        </Row>
        <Row label={t('model_fallback')}>
          <input className="ctrl" defaultValue="deepseek-v4-flash" />
        </Row>
      </div>

      {/* Retrieval */}
      <div className="glass-card rounded-card p-5 flex flex-col gap-4">
        <div className="text-sm font-semibold text-text-p mb-1">{t('retrieval')}</div>
        <Row label={t('top_k')}>
          <input className="ctrl w-20 text-center" defaultValue="20" />
        </Row>
        <Row label={t('threshold')}>
          <input className="ctrl w-20 text-center" defaultValue="0.0" />
        </Row>
        <Row label={t('rerank')}>
          <div className="toggle on" onClick={toggle} />
        </Row>
      </div>

      {/* Interface */}
      <div className="glass-card rounded-card p-5 flex flex-col gap-4">
        <div className="text-sm font-semibold text-text-p mb-1">{t('interface')}</div>

        <Row label={t('language')}>
          <select className="ctrl" value={lang === 'en' ? 'English' : '中文'} onChange={handleLang}>
            <option>中文</option>
            <option>English</option>
          </select>
        </Row>

        <div className="py-1.5">
          <div className="text-[13px] text-text-s mb-2">{t('background')}</div>
          <div className="flex items-center gap-2 flex-wrap">
            {BG_PRESETS.map((p) => (
              <button key={p.key} onClick={() => setBackground(p.key)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-btn border text-[13px] cursor-pointer transition-all ${profile.background === p.key ? 'border-accent-cyan text-text-p bg-[rgba(153,200,255,0.12)]' : 'border-border-sub text-text-s hover:border-[rgba(255,255,255,0.2)]'}`}>
                <span className="w-3.5 h-3.5 rounded-[4px] border border-[rgba(255,255,255,0.15)]" style={{ background: p.color }} />
                {t(p.label)}
              </button>
            ))}
            <button onClick={() => bgRef.current?.click()}
              className="px-3 py-1.5 rounded-btn border border-border-sub text-text-s text-[13px] cursor-pointer hover:border-[rgba(255,255,255,0.2)] transition-all">
              {t('upload_bg')}
            </button>
            <input ref={bgRef} type="file" className="hidden" accept="image/png,image/jpeg,image/webp"
              onChange={() => uploadProfile('background')} />
          </div>
        </div>

        {[['avatar_user', userRef], ['avatar_ai', aiRef]].map(([kind, ref]) => (
          <Row key={kind} label={t(kind)}>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-[8px] overflow-hidden border border-border-sub bg-bg-card flex items-center justify-center text-xs text-text-t">
                {profile[kind]
                  ? <img src={profile[kind]} alt="" className="w-full h-full object-cover" />
                  : (kind === 'avatar_user' ? '我' : 'R')}
              </div>
              <button onClick={() => ref.current?.click()}
                className="px-3 py-1.5 rounded-btn border border-border-sub text-text-s text-[13px] cursor-pointer hover:border-[rgba(255,255,255,0.2)] transition-all">
                {t('upload_avatar')}
              </button>
              <input ref={ref} type="file" className="hidden" accept="image/png,image/jpeg,image/webp"
                onChange={() => uploadProfile(kind)} />
            </div>
          </Row>
        ))}
      </div>

      {/* Save */}
      <div className="flex justify-end pt-2">
        <button onClick={handleSave}
          className="px-[22px] py-2.5 rounded-btn bg-accent-cyan text-text-inv border-none text-[13px] font-semibold cursor-pointer transition-all hover:brightness-110">
          {t('save')}
        </button>
      </div>
    </div>
  )
}

function Row({ label, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1.5">
      <span className="text-[13px] text-text-s">{label}</span>
      {children}
    </div>
  )
}
