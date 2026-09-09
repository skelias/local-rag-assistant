import { LayoutGrid } from 'lucide-react'
import { t } from '../i18n'

export default function AgentView() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-[18px] text-text-t">
      <div className="w-20 h-20 rounded-card glass-card flex items-center justify-center text-text-s">
        <LayoutGrid size={36} strokeWidth={1.2} />
      </div>
      <div className="text-base font-semibold text-text-s">{t('agent_title')}</div>
      <div className="text-[13px] text-center max-w-[340px] leading-relaxed">{t('agent_desc')}</div>
    </div>
  )
}
