import { useState, useEffect, useRef } from 'react'
import { Upload, Plus, Search } from 'lucide-react'
import DocCard from '../components/DocCard'
import { api } from '../api/client'
import { t } from '../i18n'
import useStore from '../store'

export default function KnowledgeView() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(false)
  const [hitQuery, setHitQuery] = useState('')
  const [hitResults, setHitResults] = useState(null)
  const fileRef = useRef(null)

  const loadDocs = async () => {
    try {
      setLoading(true)
      const list = await api.docs(1)
      setDocs(list)
    } catch {
      // backend not running — keep mock data
      setDocs([
        { id: 1, filename: 'fastapi-guide.md', file_type: '.md', size: 4200, chunk_count: 12, status: 'ready' },
        { id: 2, filename: 'qdrant-config.py', file_type: '.py', size: 2100, chunk_count: 8, status: 'parsed' },
        { id: 3, filename: 'rag-notes.md', file_type: '.md', size: 8700, chunk_count: 24, status: 'indexing' },
      ])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadDocs() }, [])

  const handleUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await api.upload(1, file)
      await loadDocs()
    } catch (err) {
      console.error('Upload failed:', err)
    }
  }

  const handleConfirm = async (doc) => {
    try {
      await api.confirm(1, doc.id)
      await loadDocs()
    } catch (err) {
      console.error('Confirm failed:', err)
    }
  }

  const handleHitTest = async () => {
    if (!hitQuery.trim()) return
    try {
      const result = await api.hitTest(1, hitQuery)
      setHitResults(result)
      useStore.getState().setSources(result.hits || [])
    } catch {
      // mock fallback
      setHitResults({ params: { top_k: 20, threshold: 0, rerank_enabled: false }, hits: [] })
    }
  }

  const handleAction = (type, doc) => {
    if (type === 'confirm') handleConfirm(doc)
    else if (type === 'delete') api.removeDoc(1, doc.id).then(loadDocs)
  }

  return (
    <div className="flex-1 overflow-y-auto flex flex-col gap-4 px-6 py-5">
      {/* header */}
      <div className="flex items-center justify-between">
        <div className="text-lg font-semibold">{t('nav_kb')}</div>
        <button onClick={() => fileRef.current?.click()}
          className="flex items-center gap-1.5 px-5 py-2.5 rounded-btn bg-accent-cyan text-text-inv border-none text-sm font-semibold cursor-pointer transition-all hover:brightness-110 hover:shadow-[0_0_20px_rgba(78,205,196,0.25)]">
          <Plus size={14} strokeWidth={3} />
          {t('upload')}
        </button>
        <input ref={fileRef} type="file" className="hidden" onChange={handleUpload}
          accept=".md,.txt,.py,.js,.ts,.tsx,.json,.yaml,.yml,.toml,.csv,.html,.css" />
      </div>

      {/* upload zone */}
      <div onClick={() => fileRef.current?.click()}
        className="border-2 border-dashed border-border-sub rounded-card py-8 px-6 text-center text-text-t transition-all cursor-pointer hover:border-border-glow hover:bg-[rgba(78,205,196,0.03)] hover:text-text-s">
        <Upload size={32} strokeWidth={1.5} className="mx-auto mb-2.5" />
        <div className="text-sm font-medium text-text-s">{t('drag_hint')}</div>
        <div className="text-xs mt-1">{t('upload_hint')}</div>
      </div>

      {/* hit test panel */}
      <div className="glass-card rounded-card p-4 flex flex-col gap-3">
        <div className="flex items-center gap-2 text-sm font-medium text-text-s">
          <Search size={16} />
          {t('hit_test')}
        </div>
        <div className="flex gap-2">
          <input value={hitQuery} onChange={(e) => setHitQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleHitTest()}
            placeholder="输入测试查询..."
            className="ctrl flex-1" />
          <button onClick={handleHitTest}
            className="px-4 py-2 rounded-btn bg-[rgba(78,205,196,0.12)] text-accent-cyan border border-[rgba(78,205,196,0.2)] text-sm cursor-pointer transition-all hover:bg-[rgba(78,205,196,0.2)]">
            {t('hit_test')}
          </button>
        </div>
        {hitResults && (
          <div className="text-xs text-text-t">
            top_k={hitResults.params?.top_k} threshold={hitResults.params?.threshold}
            {' '}rerank={String(hitResults.params?.rerank_enabled)}
            {' '}/ {hitResults.hits?.length ?? 0} hits
          </div>
        )}
      </div>

      {/* doc list */}
      <div className="text-sm font-semibold text-text-s">{t('kb_uploaded')}</div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-3.5">
        {docs.map((doc) => (
          <DocCard key={doc.id} doc={doc} onAction={handleAction} />
        ))}
      </div>
    </div>
  )
}
