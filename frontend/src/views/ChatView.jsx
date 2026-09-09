import { useState } from 'react'
import MessageBubble from '../components/MessageBubble'
import LiquidInput from '../components/LiquidInput'
import SourceDrawer from '../components/SourceDrawer'
import useStore from '../store'

const mockMessages = [
  { role: 'user', content: 'FastAPI 怎么生成自动文档？用什么服务器跑它？', time: '10:42', model: null, sources: [] },
  {
    role: 'assistant',
    content: 'FastAPI 通过类型注解自动生成交互式文档，访问 <code style="background:rgba(255,255,255,0.08);padding:2px 6px;border-radius:4px;font-size:12px">/docs</code> 即可看到 Swagger UI。推荐使用 uvicorn 作为 ASGI 服务器来运行它。',
    time: '10:42',
    model: 'DeepSeek',
    sources: [
      { n: 1, file: 'fastapi-guide.md', page: 3, score: 0.92, text: 'FastAPI 是一个现代、快速的 Python Web 框架，支持异步接口。它用类型注解自动生成交互式文档 /docs（Swagger UI）...' },
      { n: 2, file: 'server-setup.md', page: null, score: 0.78, text: 'uvicorn 是 FastAPI 的推荐服务器，基于 uvloop 和 httptools 构建，性能极高。启动命令：uvicorn main:app --reload' },
    ],
  },
  { role: 'user', content: 'Qdrant 的混合检索是什么意思？', time: '10:45', model: null, sources: [] },
  {
    role: 'assistant',
    content: '混合检索（Hybrid Search）指同时走两路召回，再融合结果：<br><br><strong>1. 稠密向量</strong>：用 BGE 模型把文本转成向量，按语义相似度找最接近的段落。<br><strong>2. 稀疏向量（BM25）</strong>：按关键词词频精确匹配，弥补向量对专有名词/编号不够准的问题。<br><br>Qdrant 把两路的 topK 结果用 <strong>RRF</strong>（倒数排名融合）合并成最终排序。',
    time: '10:45',
    model: 'DeepSeek',
    sources: [
      { n: 1, file: 'qdrant-guide.md', page: 1, score: 0.85, text: 'Qdrant 支持混合检索：同时使用稠密向量(语义相似)和稀疏向量(BM25关键词匹配)，通过 RRF 倒数排名融合两路结果...' },
    ],
  },
]

export default function ChatView() {
  const [messages, setMessages] = useState(mockMessages)
  const [running, setRunning] = useState(false)
  const { openDrawer, setSources } = useStore()

  const handleSend = (query) => {
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: query, time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }), model: null, sources: [] },
    ])
    setRunning(true)
    // mock stream
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '这是一段 mock 回答。真实接入后将通过 SSE 流式获取模型生成内容。',
          time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }),
          model: 'DeepSeek',
          sources: [{ n: 1, file: 'mock-source.md', page: null, score: 0.66, text: '这是一个模拟的引用来源片段...' }],
        },
      ])
      setRunning(false)
    }, 1200)
  }

  const handleCiteClick = (source) => {
    setSources([source])
    openDrawer()
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 relative">
      <div className="flex-1 overflow-y-auto flex flex-col gap-[18px] px-6 py-5 pr-8">
        {messages.map((msg, i) => (
          <MessageBubble key={i} {...msg} onCiteClick={handleCiteClick} />
        ))}
        {running && (
          <div className="flex justify-start">
            <div className="glass-card rounded-bubble-ai px-4 py-3 text-sm text-text-s animate-pulse">
              思考中...
            </div>
          </div>
        )}
      </div>

      <div className="px-6 pb-2">
        <LiquidInput onSend={handleSend} running={running} onStop={() => setRunning(false)} />
      </div>

      <SourceDrawer />
    </div>
  )
}
