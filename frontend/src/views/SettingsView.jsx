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
  // ---- LLM ----
  const [providers, setProviders] = useState([])   // [{id,label,base_url,builtin,configured}]
  const [keys, setKeys] = useState({})             // id -> api_key（留空=用 .env）
  const [pProvider, setPProvider] = useState('')
  const [pModel, setPModel] = useState('')
  const [fProvider, setFProvider] = useState('')
  const [fModel, setFModel] = useState('')

  // ---- retrieval ----
  const [topK, setTopK] = useState('20')
  const [threshold, setThreshold] = useState('0')
  const [rerank, setRerank] = useState(false)

  const [lang, setLangState] = useState(getLang())
  const profile = useStore((s) => s.profile)
  const setProfile = useStore((s) => s.setProfile)
  const bgRef = useRef(null)
  const userRef = useRef(null)
  const aiRef = useRef(null)

  useEffect(() => {
    ;(async () => {
      try {
        const [opts, cfg] = await Promise.all([api.llmOptions(), api.getConfig()])
        setProviders(opts.providers || [])
        setPProvider(opts.primary_provider)
        setPModel(opts.primary_model)
        setFProvider(opts.fallback_provider)
        setFModel(opts.fallback_model)
        const k = {}
        for (const p of (opts.providers || [])) k[p.id] = cfg[`llm.${p.id}_api_key`] || ''
        setKeys(k)
        setTopK(String(cfg['kb.1.retrieval.top_k'] ?? 20))
        setThreshold(String(cfg['kb.1.retrieval.threshold'] ?? 0))
        setRerank(!!cfg['kb.1.retrieval.rerank_enabled'])
      } catch { /* 后端未启动时保持默认 */ }
    })()
  }, [])

  const handleLang = (e) => {
    const l = e.target.value === 'English' ? 'en' : 'zh'
    setLang(l)
    setLangState(l)
  }

  const updateProvider = (id, patch) =>
    setProviders((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)))

  const addCustom = () => {
    const id = `custom_${Date.now().toString(36)}`
    setProviders((prev) => [...prev, { id, label: '自定义模型', base_url: '', builtin: false, configured: false }])
    setKeys((k) => ({ ...k, [id]: '' }))
  }

  const removeCustom = async (p) => {
    try { await api.deleteProvider(p.id) } catch {}
    setProviders((prev) => prev.filter((x) => x.id !== p.id))
  }

  const handleSave = async () => {
    try {
      await api.putConfig('llm.primary_provider', pProvider)
      await api.putConfig('llm.primary_model', pModel.trim())
      await api.putConfig('llm.fallback_provider', fProvider)
      await api.putConfig('llm.fallback_model', fModel.trim())
      for (const p of providers) {
        await api.saveProvider({
          id: p.id,
          label: p.label,
          base_url: p.base_url || '',
          api_key: (keys[p.id] || '').trim(),
        })
      }
      await api.putConfig('kb.1.retrieval.top_k', Number(topK) || 20)
      await api.putConfig('kb.1.retrieval.threshold', Number(threshold) || 0)
      await api.putConfig('kb.1.retrieval.rerank_enabled', rerank)
      alert(t('saved'))
    } catch {
      alert(t('save_failed'))
    }
  }

  const setBackground = (key) => setProfile({ ...profile, background: key })

  const uploadProfile = async (kind) => {
    const input = kind === 'background' ? bgRef : kind === 'avatar_user' ? userRef : aiRef
    const file = input.current?.files?.[0]
    if (!file) return
    try {
      const { url } = await api.uploadProfile(kind, file)
      const field = kind === 'background' ? 'background' : kind === 'avatar_user' ? 'avatar_user' : 'avatar_ai'
      setProfile({ ...profile, [field]: url })
    } catch (err) {
      console.error('Upload profile failed:', err)
    }
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-5 px-6 py-5">
      {/* LLM：真实可用，保存即生效 */}
      <div className="glass-card rounded-card p-5 flex flex-col gap-4">
        <div className="text-sm font-semibold text-text-p mb-1">{t('model')}</div>

        <Row label={t('provider_primary')}>
          <select className="ctrl" value={pProvider} onChange={(e) => setPProvider(e.target.value)}>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>{p.label}{p.configured ? '' : ' · 未配 Key'}</option>
            ))}
          </select>
        </Row>
        <Row label={t('model_primary')}>
          <input className="ctrl" value={pModel} onChange={(e) => setPModel(e.target.value)} />
        </Row>
        <Row label={t('provider_fallback')}>
          <select className="ctrl" value={fProvider} onChange={(e) => setFProvider(e.target.value)}>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </Row>
        <Row label={t('model_fallback')}>
          <input className="ctrl" value={fModel} onChange={(e) => setFModel(e.target.value)} />
        </Row>

        <div className="h-px bg-border-sub my-1" />

        {/* 模型/密钥直接编辑区：可直接填 Key、改 Base URL、添加自定义模型 */}
        <div className="text-[13px] font-semibold text-text-s">{t('providers')}</div>
        {providers.map((p) => (
          <div key={p.id} className="flex flex-col gap-1.5 py-1.5 border-b border-border-sub last:border-0">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full shrink-0 ${keys[p.id] && keys[p.id].trim() ? 'bg-accent-success' : 'bg-text-t'}`} />
              <input className="ctrl w-[180px]" value={p.label} disabled={p.builtin}
                onChange={(e) => updateProvider(p.id, { label: e.target.value })} />
              <input className="ctrl flex-1" placeholder={t('base_url')} value={p.base_url || ''}
                onChange={(e) => updateProvider(p.id, { base_url: e.target.value })} />
              {!p.builtin && (
                <button onClick={() => removeCustom(p)}
                  className="px-2 py-1 rounded-btn border border-border-sub text-accent-danger text-[12px] cursor-pointer hover:border-accent-danger transition-all">
                  {t('remove')}
                </button>
              )}
            </div>
            <input className="ctrl w-full" type="password" placeholder={t('key_optional')}
              value={keys[p.id] || ''} onChange={(e) => setKeys({ ...keys, [p.id]: e.target.value })} />
          </div>
        ))}

        <button onClick={addCustom}
          className="self-start px-4 py-2 rounded-btn border border-border-sub text-accent-cyan text-[13px] cursor-pointer hover:border-accent-cyan transition-all">
          + {t('add_custom')}
        </button>
        <div className="text-[12px] text-text-t -mt-1">{t('key_hint')}</div>
      </div>

      {/* Retrieval */}
      <div className="glass-card rounded-card p-5 flex flex-col gap-4">
        <div className="text-sm font-semibold text-text-p mb-1">{t('retrieval')}</div>
        <Row label={t('top_k')}>
          <input className="ctrl w-20 text-center" value={topK} onChange={(e) => setTopK(e.target.value)} />
        </Row>
        <Row label={t('threshold')}>
          <input className="ctrl w-20 text-center" value={threshold} onChange={(e) => setThreshold(e.target.value)} />
        </Row>
        <Row label={t('rerank')}>
          <div className={`toggle ${rerank ? 'on' : ''}`} onClick={() => setRerank(!rerank)} />
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
