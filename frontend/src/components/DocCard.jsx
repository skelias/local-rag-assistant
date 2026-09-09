import { FileText, MoreHorizontal } from 'lucide-react'
import { t } from '../i18n'

const typeColors = {
  '.md': { bg: 'rgba(153,200,255,0.1)', fg: '#99c8ff' },
  '.py': { bg: 'rgba(153,200,255,0.1)', fg: '#99c8ff' },
  '.txt': { bg: 'rgba(126,162,255,0.1)', fg: '#7ea2ff' },
}

const statusMap = {
  ready: 'badge-ready',
  parsed: 'badge-parsed',
  failed: 'badge-failed',
  indexing: 'badge-indexing',
}
const statusLabel = {
  ready: 'status_ready',
  parsed: 'status_parsed',
  failed: 'status_failed',
  indexing: 'status_indexing',
}

export default function DocCard({ doc, onAction }) {
  const ext = doc.file_type || '.md'
  const color = typeColors[ext] || { bg: 'rgba(255,255,255,0.06)', fg: '#a0a0b0' }

  return (
    <div className="glass-card rounded-card p-[18px] flex flex-col gap-3.5 cursor-pointer transition-all hover:-translate-y-0.5">
      <div className="flex items-start justify-between gap-2">
        <div className="w-10 h-10 rounded-[12px] flex items-center justify-center shrink-0"
             style={{ background: color.bg, color: color.fg }}>
          <FileText size={20} />
        </div>
        <button onClick={() => onAction?.('menu', doc)}
          className="w-7 h-7 rounded-lg bg-transparent border-none text-text-t flex items-center justify-center cursor-pointer hover:bg-[rgba(255,255,255,0.06)] hover:text-text-s transition-all">
          <MoreHorizontal size={16} />
        </button>
      </div>
      <div className="text-sm font-medium text-text-p break-all leading-snug">{doc.filename}</div>
      <div className="text-xs text-text-t">
        {doc.chunk_count} {t('chunks')} / {(doc.size / 1024).toFixed(1)} KB
      </div>
      <span className={`badge ${statusMap[doc.status] || 'badge-parsed'}`}>
        {t(statusLabel[doc.status] || 'status_parsed')}
      </span>
    </div>
  )
}
