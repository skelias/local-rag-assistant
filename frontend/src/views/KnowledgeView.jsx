import { Upload, Plus } from 'lucide-react'
import DocCard from '../components/DocCard'
import { t } from '../i18n'

const mockDocs = [
  { id: 1, filename: 'fastapi-guide.md', file_type: '.md', size: 4200, chunk_count: 12, status: 'ready' },
  { id: 2, filename: 'qdrant-config.py', file_type: '.py', size: 2100, chunk_count: 8, status: 'parsed' },
  { id: 3, filename: 'rag-notes.md', file_type: '.md', size: 8700, chunk_count: 24, status: 'indexing' },
  { id: 4, filename: 'legacy.pdf', file_type: '.pdf', size: 1200000, chunk_count: 0, status: 'failed' },
  { id: 5, filename: 'utils.ts', file_type: '.ts', size: 3400, chunk_count: 6, status: 'ready' },
  { id: 6, filename: 'README.md', file_type: '.md', size: 5600, chunk_count: 15, status: 'ready' },
]

export default function KnowledgeView() {
  const handleAction = (type, doc) => {
    console.log('action:', type, doc)
  }

  return (
    <div className="flex-1 overflow-y-auto flex flex-col gap-4 px-6 py-5">
      {/* header */}
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold">{t('nav_kb')}</div>
        <button className="flex items-center gap-1.5 px-5 py-2.5 rounded-btn bg-accent-cyan text-text-inv border-none text-sm font-semibold cursor-pointer transition-all hover:brightness-110 hover:shadow-[0_0_20px_rgba(78,205,196,0.25)]">
          <Plus size={14} strokeWidth={3} />
          {t('upload')}
        </button>
      </div>

      {/* upload zone */}
      <div className="border-2 border-dashed border-border-sub rounded-card py-8 px-6 text-center text-text-t transition-all cursor-pointer hover:border-border-glow hover:bg-[rgba(78,205,196,0.03)] hover:text-text-s">
        <Upload size={32} strokeWidth={1.5} className="mx-auto mb-2.5" />
        <div className="text-sm font-medium text-text-s">{t('drag_hint')}</div>
        <div className="text-xs mt-1">{t('upload_hint')}</div>
      </div>

      {/* doc list label */}
      <div className="text-sm font-semibold text-text-s mt-2">{t('kb_uploaded')}</div>

      {/* doc grid */}
      <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-3.5">
        {mockDocs.map((doc) => (
          <DocCard key={doc.id} doc={doc} onAction={handleAction} />
        ))}
      </div>
    </div>
  )
}
