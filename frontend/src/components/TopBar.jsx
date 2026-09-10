import { t } from '../i18n'
import useStore from '../store'

const KB_TABS = [
  { key: 'kb_all', id: 1 },
  { key: 'kb_code', id: 2 },
  { key: 'kb_notes', id: 3 },
]

export default function TopBar() {
  const nav = useStore((s) => s.nav)
  const kbId = useStore((s) => s.kbId)
  const setKbId = useStore((s) => s.setKbId)
  const avatar = useStore((s) => s.profile.avatar_user)

  const pageTitle = {
    chat: 'nav_chat',
    agent: 'nav_agent',
    settings: 'nav_settings',
  }[nav] || 'nav_chat'

  return (
    <header className="h-[60px] border-b border-border-sub flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-1.5">
        {nav === 'kb' ? (
          // 知识库 tab 只在知识库页出现
          KB_TABS.map((t) => (
            <span key={t.id}
              onClick={() => setKbId(t.id)}
              className={`
                px-4 py-[7px] rounded-pill text-[13px] font-medium cursor-pointer transition-all select-none
                ${kbId === t.id
                  ? 'bg-[rgba(255,255,255,0.1)] text-text-p'
                  : 'text-text-s hover:text-text-p hover:bg-[rgba(255,255,255,0.04)]'}
              `}
            >
              {t(t.key)}
            </span>
          ))
        ) : (
          <span className="text-[15px] font-semibold text-text-p">{t(pageTitle)}</span>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-[12px] text-text-t">v0.1.0</span>
        <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold text-text-inv overflow-hidden"
             style={{ background: '#99c8ff' }}>
          {avatar ? <img src={avatar} alt="" className="w-full h-full object-cover" /> : '我'}
        </div>
      </div>
    </header>
  )
}
