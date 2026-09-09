import { t } from '../i18n'

export default function MessageBubble({ role, content, sources, time, model, onCiteClick }) {
  const isUser = role === 'user'

  return (
    <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`
          max-w-[76%] px-[18px] py-3.5 text-sm leading-relaxed animate-fade-up
          ${isUser
            ? 'bg-[linear-gradient(135deg,rgba(78,205,196,0.12),rgba(78,205,196,0.04))] border border-[rgba(78,205,196,0.15)] rounded-bubble-user text-text-p'
            : 'glass-card rounded-bubble-ai text-text-p hover:bg-bg-card-hover hover:border-[rgba(255,255,255,0.12)]'}
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
