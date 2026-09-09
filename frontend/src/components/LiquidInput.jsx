import { Send, Square, Paperclip } from 'lucide-react'
import { useState, useRef } from 'react'
import { t } from '../i18n'

export default function LiquidInput({ onSend, running, onStop }) {
  const [value, setValue] = useState('')
  const inputRef = useRef(null)

  const handleSend = () => {
    const q = value.trim()
    if (!q) return
    onSend(q)
    setValue('')
    inputRef.current?.focus()
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="h-16 shrink-0 flex items-center gap-3 px-1">
      <button className="w-9 h-9 rounded-full bg-transparent border-none text-text-t flex items-center justify-center cursor-pointer transition-all hover:text-text-s hover:bg-[rgba(255,255,255,0.05)] shrink-0"
              title="Attach">
        <Paperclip size={18} strokeWidth={1.8} />
      </button>
      <div className="flex-1 h-[52px] glass-card rounded-pill flex items-center px-5 gap-3 input-glow transition-all"
           style={{ background: 'rgba(255,255,255,0.04)' }}>
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder={t('input_ph')}
          className="flex-1 bg-transparent border-none outline-none text-text-p text-sm font-inherit"
        />
        <button
          onClick={running ? onStop : handleSend}
          className={`
            w-10 h-10 rounded-full border-none flex items-center justify-center cursor-pointer shrink-0 transition-all
            ${running
              ? 'bg-accent-danger text-white hover:scale-105'
              : 'bg-accent-cyan text-text-inv hover:scale-105 hover:shadow-[0_0_16px_rgba(153,200,255,0.35)]'}
          `}
          title={running ? t('stop') : t('send')}
        >
          {running ? <Square size={16} strokeWidth={2.5} /> : <Send size={18} strokeWidth={2.2} />}
        </button>
      </div>
    </div>
  )
}
