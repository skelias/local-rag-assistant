import useStore from '../store'

export default function MessageBubble({ role, content, sources, time, model, onCiteClick }) {
  const isUser = role === 'user'
  const profile = useStore((s) => s.profile)
  const avatarUrl = isUser ? profile.avatar_user : profile.avatar_ai

  return (
    <div className={`flex w-full gap-2.5 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* 头像：自定义图 或 字母徽章 */}
      <div className={`shrink-0 w-8 h-8 rounded-[8px] flex items-center justify-center text-xs font-semibold overflow-hidden ${isUser ? 'bg-[rgba(153,200,255,0.14)] text-accent-cyan border border-[rgba(153,200,255,0.3)]' : 'bg-bg-card border border-border-sub text-text-t'}`}>
        {avatarUrl
          ? <img src={avatarUrl} alt="" className="w-full h-full object-cover" />
          : (isUser ? '我' : 'R')}
      </div>

      <div
        className={`
          max-w-[76%] px-[18px] py-3.5 text-sm leading-relaxed animate-fade-up
          ${isUser
            ? 'bg-[rgba(153,200,255,0.10)] border border-[rgba(153,200,255,0.25)] rounded-bubble-user text-text-p'
            : 'glass-card rounded-bubble-ai text-text-p hover:bg-bg-card-hover hover:border-[rgba(255,255,255,0.14)]'}
        `}
      >
        <div dangerouslySetInnerHTML={{ __html: content }} />

        {!isUser && sources && sources.length > 0 && (
          <div className="mt-2.5 flex gap-1.5 flex-wrap">
            {sources.map((s) => (
              <span key={s.n} className="cite-tag" onClick={() => onCiteClick?.(s)}>
                [{s.n}] {s.file}
              </span>
            ))}
          </div>
        )}

        <div className="text-[11px] text-text-t mt-1.5 flex gap-2 items-center">
          <span>{time}</span>
          {!isUser && model && <span>/ {model}</span>}
        </div>
      </div>
    </div>
  )
}
