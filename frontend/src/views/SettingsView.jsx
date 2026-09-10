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
  const [options, setOptions] = useState(null)      // { providers, primary_*, fallback_* }
  const [pProvider, setPProvider] = useState('')
  const [pModel, setPModel] = useState('')
  const [fProvider, setFProvider] = useState('')
  const [fModel, setFModel] = useState('')
  const [keys, setKeys] = useState({})              // llm.<pid>_api_key 覆盖（空=用 .env）
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
        setOptions(opts)
        setPProvider(opts.primary_provider)
        setPModel(opts.primary_model)
        setFProvider(opts.fallback_provider)
        setFModel(opts.fallback_model)
        const k = {}
        for (const p of opts.providers) k[p.id] = cfg[`llm.${p.id}_api_key`] || ''
        setKeys(k)
        setTopK(String(cfg['kb.1.retrieval.top_k'] ?? 20))
        setThreshold(String(cfg['kb.1.retrieval.threshold'] ?? 0))
        setRerank(!!cfg['kb.1.retrieval.rerank_enabled'])
      } catch { /* backend 未启动时保持默认 */ }
    })()
  }, [])

  const handleLang = (e) => {
    const l = e.target.value === 'English' ? 'en' : 'zh'
    setLang(l)
    setLangState(l)
  }

  const handleSave = async () => {
    const put = (k, v) => api.putConfig(k, v)
    try {
      await put('llm.primary_provider', pProvider)
      await put('llm.primary_model', pModel.trim())
      await put('llm.fallback_provider', fProvider)
      await put('llm.fallback_model', fModel.trim())
      for (const [pid, val] of Object.entries(keys)) {
        if (val && val.trim()) await put(`llm.${pid}_api_key`, val.trim())
      }
      await put('kb.1.retrieval.top_k', Number(topK) || 20)
      await put('kb.1.retrieval.threshold', Number(threshold) || 0)
      await put('kb.1.retrieval.rerank_enabled', rerank)
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
      const field = kind === 'background' ? 'background'
        : kind === 'avatar_user' ? 'avatar_user' : 'avatar_ai'
      setProfile({ ...profile, [field]: url })
    } catch (err) {
      console.error('Upload profile failed:', err)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto flex flex-col gap-5 px-6 py-5">
      {/* LLM：真实可用，保存即生效（无需重启） */}
      <div className="glass-card rounded-card p-5 flex flex-col gap-4">
        <div className="text-sm font-semibold text-text-p mb-1">{t('model')}</div>
        <Row label={t('provider_primary')}>
          <select className="ctrl" value={pProvider} onChange={(e) => setPProvider(e.target.value)}>
            {(options?.providers || []).map((p) => (
              <option key={p.id} value={p.id}>{p.label}{p.configured ? '' : ' · 未配 Key'}</option>
            ))}
          </select>
        </Row>
        <Row label={t('model_primary')}>
          <input className="ctrl" value={pModel} onChange={(e) => setPModel(e.target.value)} />
        </Row>
        <Row label={t('provider_fallback')}>
          <select className="ctrl" value={fProvider} onChange={(e) => setFProvider(e.target.value)}>
            {(options?.providers || []).map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </Row>
        <Row label={t('model_fallback')}>
          <input className="ctrl" value={fModel} onChange={(e) => setFModel(e.target.value)} />
        </Row>

        <div className="text-[12px] text-text-t -mt-1">
          {t('key_hint')}
        </div>
        {(options?.providers || []).map((p) => (
          <Row key={p.id} label={p.label}>
            <div className="flex items-center gap-2.5">
              <span className={`w-2 h-2 rounded-full ${p.configured ? 'bg-accent-success' : 'bg-text-t'}`} />
              <input className="ctrl w-[240px]" type="password" placeholder={t('key_optional')}
                value={keys[p.id] || ''} onChange={(e) => setKeys({ ...keys, [p.id]: e.target.value })} />
            </div>
          </Row>
        ))}
      </div>

      {/* Retrieval：保存到 kb.1 检索配置，命中测试与对话同源生效 */}
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

      {/* Interface：语言 + 背景 + 头像 */}
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
