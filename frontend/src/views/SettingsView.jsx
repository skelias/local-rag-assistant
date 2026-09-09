import { t } from '../i18n'

export default function SettingsView() {
  const toggle = (e) => {
    e.currentTarget.classList.toggle('on')
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
          <select className="ctrl"><option>中文</option><option>English</option></select>
        </Row>
      </div>

      {/* Save */}
      <div className="flex justify-end pt-2">
        <button className="px-[22px] py-2.5 rounded-btn bg-accent-cyan text-text-inv border-none text-[13px] font-semibold cursor-pointer transition-all hover:brightness-110 hover:shadow-[0_0_20px_rgba(78,205,196,0.25)]">
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
