import { t } from '../i18n'

const tabs = ['kb_all', 'kb_code', 'kb_notes']

export default function TopBar() {
  return (
    <header className="h-[60px] border-b border-border-sub flex items-center justify-between px-6 shrink-0">
      <div className="flex gap-1.5">
        {tabs.map((key, i) => (
          <span key={key}
            className={`
              px-4 py-[7px] rounded-pill text-[13px] font-medium cursor-pointer transition-all select-none
              ${i === 0
                ? 'bg-[rgba(255,255,255,0.1)] text-text-p'
                : 'text-text-s hover:text-text-p hover:bg-[rgba(255,255,255,0.04)]'}
            `}
          >
            {t(key)}
          </span>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[12px] text-text-t">v0.1.0</span>
        <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-text-inv"
             style={{ background: 'linear-gradient(135deg, #4ecdc4, #a78bfa)' }}>CA</div>
      </div>
    </header>
  )
}
