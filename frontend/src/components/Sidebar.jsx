import { MessageSquare, BookOpen, LayoutGrid, Settings } from 'lucide-react'
import useStore from '../store'
import { t } from '../i18n'

const icons = {
  chat: MessageSquare,
  kb: BookOpen,
  agent: LayoutGrid,
  settings: Settings,
}
const labels = ['nav_chat', 'nav_kb', 'nav_agent', 'nav_settings']
const keys = ['chat', 'kb', 'agent', 'settings']

export default function Sidebar() {
  const { nav, setNav } = useStore()

  return (
    <nav className="glass-nav relative z-30 flex flex-col items-center py-4 gap-2.5 shrink-0"
        style={{ width: 64, borderRadius: 16 }}>
      {keys.slice(0, 3).map((k, i) => {
        const Icon = icons[k]
        const active = nav === k
        return (
          <button key={k}
            onClick={() => setNav(k)}
            className={`
              relative w-11 h-11 rounded-[12px] flex items-center justify-center
              transition-all duration-200 outline-none border-none cursor-pointer
              ${active
                ? 'bg-[rgba(153,200,255,0.12)] text-accent-cyan'
                : 'bg-transparent text-text-t hover:bg-[rgba(255,255,255,0.06)] hover:text-text-s'}
            `}
            title={t(labels[i])}
          >
            {active && (
              <span className="absolute -left-[10px] top-1/2 -translate-y-1/2 w-[3px] h-[18px] bg-accent-cyan rounded-r-[3px]" />
            )}
            <Icon size={20} strokeWidth={1.8} />
            <span className="nav-tip">{t(labels[i])}</span>
          </button>
        )
      })}

      <div className="flex-1" />

      <button
        onClick={() => setNav('settings')}
        className={`
          relative w-11 h-11 rounded-[12px] flex items-center justify-center
          transition-all duration-200 outline-none border-none cursor-pointer
          ${nav === 'settings'
            ? 'bg-[rgba(153,200,255,0.12)] text-accent-cyan'
            : 'bg-transparent text-text-t hover:bg-[rgba(255,255,255,0.06)] hover:text-text-s'}
        `}
        title={t('nav_settings')}
      >
        {nav === 'settings' && (
          <span className="absolute -left-[10px] top-1/2 -translate-y-1/2 w-[3px] h-[18px] bg-accent-cyan rounded-r-[3px]" />
        )}
        <Settings size={20} strokeWidth={1.8} />
        <span className="nav-tip">{t('nav_settings')}</span>
      </button>
    </nav>
  )
}
