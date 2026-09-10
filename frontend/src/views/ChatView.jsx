import { useState, useRef, useEffect } from 'react'
import MessageBubble from '../components/MessageBubble'
import LiquidInput from '../components/LiquidInput'
import SourceDrawer from '../components/SourceDrawer'
import { useChatStream } from '../hooks/useChatStream'
import useStore from '../store'

export default function ChatView() {
  const [messages, setMessages] = useState([])
  const [convId, setConvId] = useState(null)
  const scrollRef = useRef(null)
  const { openDrawer, setSources } = useStore()
  const kbId = useStore((s) => s.kbId)
  const { run, stop, running } = useChatStream()

  // auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  const handleSend = (query) => {
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    setMessages((prev) => [...prev, { role: 'user', content: query, time, model: null, sources: [] }])

    let fullText = ''
    let sourcesData = []

    run({
      kbId,
      query,
      conversationId: convId,
      onSources: (sources) => {
        sourcesData = sources
        setSources(sources)
      },
      onToken: (t) => {
        fullText += t
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.role === 'assistant' && last._streaming) {
            return [...prev.slice(0, -1), { ...last, content: fullText }]
          }
          return [...prev, {
            role: 'assistant',
            content: fullText,
            time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
            model: '',
            sources: sourcesData,
            _streaming: true,
          }]
        })
      },
      onDone: (data) => {
        if (data?.conversation_id) setConvId(data.conversation_id)
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?._streaming) {
            return [...prev.slice(0, -1), { ...last, _streaming: false, sources: sourcesData }]
          }
          return prev
        })
      },
    })
  }

  const handleCiteClick = (source) => {
    setSources([source])
    openDrawer()
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 relative">
      <div ref={scrollRef} className="flex-1 overflow-y-auto flex flex-col gap-[18px] px-6 py-5 pr-8">
        {messages.length === 0 && (
          <div className="flex-1 flex items-center justify-center text-text-t text-sm">
            输入问题开始对话
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} {...msg} onCiteClick={handleCiteClick} />
        ))}
        {running && messages[messages.length - 1]?.role !== 'assistant' && (
          <div className="flex justify-start">
            <div className="glass-card rounded-bubble-ai px-4 py-3 text-sm text-text-s animate-pulse">
              思考中...
            </div>
          </div>
        )}
      </div>

      <div className="px-6 pb-2">
        <LiquidInput onSend={handleSend} running={running} onStop={stop} />
      </div>

      <SourceDrawer />
    </div>
  )
}
