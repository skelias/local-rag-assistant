import { Bookmark, X, FileText } from 'lucide-react'
import useStore from '../store'
import { t } from '../i18n'

export default function SourceDrawer() {
  const { drawerOpen, closeDrawer, sources } = useStore()
  const data = sources.length ? sources : [
    { n: 1, file: 'fastapi-guide.md', page: 3, score: 0.92, text: 'FastAPI 是一个现代、快速的 Python Web 框架，支持异步接口。它用类型注解自动生成交互式文档 /docs（Swagger UI）...' },
    { n: 2, file: 'server-setup.md', page: null, score: 0.78, text: 'uvicorn 是 FastAPI 的推荐服务器，基于 uvloop 和 httptools 构建，性能极高。启动命令：uvicorn main:app --reload' },
  ]

  return (
    <>
      {/* trigger button */}
      <button
        onClick={() => useStore.getState().toggleDrawer()}
        className="absolute top-[76px] right-5 w-9 h-9 rounded-[10px] glass-card flex items-center justify-center cursor-pointer z-[5] transition-all hover:text-accent-violet hover:border-[rgba(167,139,250,0.25)]"
        title={t('sources')}
      >
        <Bookmark size={18} />
      </button>

      {/* drawer */}
      <aside
        className={`
          glass-drawer absolute top-[60px] right-0 bottom-0 z-10
          flex flex-col p-5 gap-3.5 overflow-y-auto
          transition-transform duration-300
          ${drawerOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
        style={{ width: 340, transitionTimingFunction: 'cubic-bezier(0.16,1,0.3,1)' }}
      >
        <div className="flex items-center justify-between text-[15px] font-semibold">
          <span>{t('sources')}</span>
          <button onClick={closeDrawer}
            className="w-7 h-7 rounded-lg bg-[rgba(255,255,255,0.06)] border-none text-text-s cursor-pointer flex items-center justify-center hover:bg-[rgba(255,255,255,0.1)] hover:text-text-p transition-all">
            <X size={16} />
          </button>
        </div>

        {data.map((s) => (
          <div key={s.n} className="glass-card rounded-card p-3.5 flex flex-col gap-2.5 transition-all hover:bg-bg-card-hover hover:border-[rgba(255,255,255,0.12)]">
            <div className="flex items-center gap-2.5">
              <div className="w-6 h-6 rounded-full bg-[rgba(167,139,250,0.15)] text-accent-violet flex items-center justify-center text-[11px] font-bold shrink-0">{s.n}</div>
              <div className="text-[13px] font-medium text-text-p truncate">{s.file}</div>
              {s.page && <div className="text-[11px] text-text-t ml-auto">p.{s.page}</div>}
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-[5px] rounded-full bg-[rgba(255,255,255,0.06)] overflow-hidden">
                <div className="h-full rounded-full"
                     style={{
                       width: `${Math.min(s.score * 100, 100)}%`,
                       background: 'linear-gradient(90deg, #4ecdc4, #a78bfa)',
                     }} />
              </div>
              <span className="text-[11px] text-accent-cyan font-semibold tabular-nums">{s.score.toFixed(2)}</span>
            </div>
            <div className="text-[12px] text-text-s leading-relaxed line-clamp-3"
                 style={{ WebkitLineClamp: 3, display: '-webkit-box', WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {s.text}
            </div>
          </div>
        ))}
      </aside>
    </>
  )
}
