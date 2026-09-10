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
  const [providers, setProviders] = useState([])   // [{id,label,base_url,builtin,configured,models:[]}]
  const [keys, setKeys] = useState({})             // id -> api_key
  const [pProvider, setPProvider] = useState('')
  const [pModel, setPModel] = useState('')
  const [fProvider, setFProvider] = useState('')
  const [fModel, setFModel] = useState('')
  const [newModel, setNewModel] = useState({})     // id -> 输入中的新模型名
  const [discovering, setDiscovering] = useState(false)

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
      } catch { /* 后端未启动 */ }
    })()
  }, [])

  const updateProvider = (id, patch) =>
    setProviders((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)))

  const providerModels = (id) => providers.find((p) => p.id === id)?.models || []

  const addCustom = () => {
    const id = `custom_${Date.now().toString(36)}`
    setProviders((prev) => [...prev, { id, label: '自定义模型', base_url: '', builtin: false, configured: false, models: [] }])
    setKeys((k) => ({ ...k, [id]: '' }))
  }

  const removeCustom = async (p) => {
    try { await api.deleteProvider(p.id) } catch {}
    setProviders((prev) => prev.filter((x) => x.id !== p.id))
  }

  const discover = async (p) => {
    if (!(p.base_url || '').trim()) { alert(t('need_base_url')); return }
    setDiscovering(true)
    try {
      const { models } = await api.discoverModels({ base_url: p.base_url, api_key: keys[p.id] || '' })
      updateProvider(p.id, { models: models.map((m) => m.id) })
    } catch (e) {
      alert(t('discover_failed') + '：' + (e.message || e))
    } finally {
      setDiscovering(false)
    }
  }

  const addModel = (p, name) => {
    const m = (name || '').trim()
    if (!m) return
    updateProvider(p.id, { models: [...new Set([...providerModels(p.id), m])] })
    setNewModel((s) => ({ ...s, [p.id]: '' }))
  }

  const removeModel = (p, m) =>
    updateProvider(p.id, { models: providerModels(p.id).filter((x) => x !== m) })

  const handleSave = async () => {
    try {
      await api.putConfig('llm.primary_provider', pProvider)
      await api.putConfig('llm.primary_model', pModel.trim())
      await api.putConfig('llm.fallback_provider', fProvider)
      await api.putConfig('llm.fallback_model', fModel.trim())
      for (const p of providers) {
        await api.saveProvider({
          id: p.id, label: p.label, base_url: p.base_url || '',
          api_key: (keys[p.id] || '').trim(), models: p.models || [],
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

  const handleLang = (e) => {
    const l = e.target.value === 'English' ? 'en' : 'zh'
    setLang(l); setLangState(l)
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
    } catch (err) { console.error('Upload profile failed:', err) }
  }

  return (
    <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-5 px-6 py-5">
      {/* LLM */}
      <div className="glass-card rounded-card p-5 flex flex-col gap-4">
        <div className="text-sm font-semibold text-text-p mb-1">{t('model')}</div>

        {/* 默认模型（主力 / 降级），模型名下拉由对应 provider 的模型列表提供 */}
        <Row label={t('provider_primary')}>
          <select className="ctrl" value={pProvider} onChange={(e) => setPProvider(e.target.value)}>
            {providers.map((p) => <option key={p.id} value={p.id}>{p.label}{p.configured ? '' : ' · 未配 Key'}</option>)}
          </select>
        </Row>
        <Row label={t('model_primary')}>
          <div className="flex items-center gap-2">
            <input className="ctrl" value={pModel} list="primary-models" onChange={(e) => setPModel(e.target.value)} />
            <datalist id="primary-models">
              {providerModels(pProvider).map((m) => <option key={m} value={m} />)}
            </datalist>
          </div>
        </Row>
        <Row label={t('provider_fallback')}>
          <select className="ctrl" value={fProvider} onChange={(e) => setFProvider(e.target.value)}>
            {providers.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
          </select>
        </Row>
        <Row label={t('model_fallback')}>
          <input className="ctrl" value={fModel} list="fallback-models" onChange={(e) => setFModel(e.target.value)} />
          <datalist id="fallback-models">
            {providerModels(fProvider).map((m) => <option key={m} value={m} />)}
          </datalist>
        </Row>
        <div className="text-[12px] text-text-t -mt-1">{t('model_hint')}</div>

        <div className="h-px bg-border-sub my-1" />

        {/* Provider 卡片：名称 / Base URL / API Key / 模型列表（手填为主，拉取可选） */}
        <div className="text-[13px] font-semibold text-text-s">{t('providers')}</div>
        {providers.map((p) => (
          <div key={p.id} className="rounded-card border border-border-sub p-3.5 flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full shrink-0 ${keys[p.id] && keys[p.id].trim() ? 'bg-accent-success' : 'bg-text-t'}`} />
              <span className="text-[12px] text-text-t w-[62px] shrink-0">{t('provider_name')}</span>
              <input className="ctrl w-[170px]" value={p.label} disabled={p.builtin}
                onChange={(e) => updateProvider(p.id, { label: e.target.value })} />
              {!p.builtin && (
                <button onClick={() => removeCustom(p)}
                  className="ml-auto px-2 py-1 rounded-btn border border-border-sub text-accent-danger text-[12px] cursor-pointer hover:border-accent-danger transition-all">
                  {t('remove')}
                </button>
              )}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[12px] text-text-t w-[62px] shrink-0">{t('base_url')}</span>
              <input className="ctrl flex-1" placeholder="https://api.example.com/v1" value={p.base_url || ''}
                onChange={(e) => updateProvider(p.id, { base_url: e.target.value })} />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[12px] text-text-t w-[62px] shrink-0">{t('api_key')}</span>
              <input className="ctrl flex-1" type="password" placeholder={t('key_env_hint')}
                value={keys[p.id] || ''} onChange={(e) => setKeys({ ...keys, [p.id]: e.target.value })} />
            </div>

            <div className="flex items-center gap-2 flex-wrap pt-1">
              <button onClick={() => discover(p)} disabled={discovering}
                className="px-3 py-1.5 rounded-btn border border-border-sub text-accent-cyan text-[12px] cursor-pointer hover:border-accent-cyan transition-all">
                {t('discover_models')}
              </button>
              <div className="flex items-center gap-1.5">
                <input className="ctrl w-[160px] !py-1.5 text-[12px]" placeholder={t('add_model')}
                  value={newModel[p.id] || ''}
                  onChange={(e) => setNewModel((s) => ({ ...s, [p.id]: e.target.value }))}
                  onKeyDown={(e) => e.key === 'Enter' && addModel(p, newModel[p.id])} />
                <button onClick={() => addModel(p, newModel[p.id])}
                  className="px-2.5 py-1.5 rounded-btn border border-border-sub text-text-s text-[12px] cursor-pointer hover:border-[rgba(255,255,255,0.2)] transition-all">
                  {t('add')}
                </button>
              </div>
            </div>

            {providerModels(p.id).length > 0 && (
              <div className="flex items-center gap-1.5 flex-wrap">
                {providerModels(p.id).map((m) => (
                  <span key={m} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-btn bg-[rgba(153,200,255,0.1)] border border-[rgba(153,200,255,0.25)] text-[12px] text-accent-cyan">
                    {m}
                    <button onClick={() => removeModel(p, m)} className="text-text-t hover:text-accent-danger cursor-pointer border-none bg-transparent px-0.5">×</button>
                  </span>
                ))}
              </div>
            )}
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
            <option>中文</option><option>English</option>
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
