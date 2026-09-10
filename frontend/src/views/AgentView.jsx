import { LayoutGrid, MessageSquare, BookOpen, Settings } from 'lucide-react'
import { t } from '../i18n'
import useStore from '../store'

export default function AgentView() {
  const setNav = useStore((s) => s.setNav)

  const items = [
    { icon: MessageSquare, label: 'nav_chat', desc: 'cap_chat' },
    { icon: BookOpen, label: 'nav_kb', desc: 'cap_kb' },
    { icon: Settings, label: 'nav_settings', desc: 'cap_settings' },
  ]

  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-5 px-6 text-text-s">
      <div className="w-20 h-20 rounded-card glass-card flex items-center justify-center text-text-s">
        <LayoutGrid size={36} strokeWidth={1.2} />
      </div>
      <div className="text-base font-semibold text-text-s">{t('agent_title')}</div>
      <div className="text-[13px] text-center max-w-[380px] leading-relaxed text-text-t">{t('agent_desc')}</div>

      <div className="grid grid-cols-3 gap-3 mt-2 max-w-[560px] w-full">
        {items.map(({ icon: Icon, label, desc }) => (
          <button key={label} onClick={() => setNav(label === 'nav_chat' ? 'chat' : label === 'nav_kb' ? 'kb' : 'settings')}
            className="glass-card rounded-card p-4 flex flex-col items-center gap-2 cursor-pointer transition-all hover:border-[rgba(255,255,255,0.18)]">
            <Icon size={22} strokeWidth={1.6} className="text-accent-cyan" />
            <span className="text-[13px] font-medium text-text-p">{t(label)}</span>
            <span className="text-[11px] text-text-t text-center">{t(desc)}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
