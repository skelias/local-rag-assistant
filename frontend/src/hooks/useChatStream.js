import { useState, useRef } from 'react'

/**
 * SSE streaming hook for /api/chat/stream
 *
 * Event protocol:
 *   event: sources   data: [{n,file,score,...}]
 *   event: token     data: {"t":"..."}
 *   event: done      data: {"conversation_id":N}
 */
export function useChatStream() {
  const [running, setRunning] = useState(false)
  const abortRef = useRef(null)

  const run = async ({ kbId, query, conversationId, onSources, onToken, onDone }) => {
    if (running) return
    setRunning(true)
    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      const resp = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kb_id: kbId, conversation_id: conversationId, query }),
        signal: ctrl.signal,
      })

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })

        /// Split on double newline (SSE frame boundary)
        let idx
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const raw = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          parseSSEFrame(raw, onSources, onToken, onDone)
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') console.error('SSE error:', e)
    } finally {
      setRunning(false)
      abortRef.current = null
    }
  }

  const stop = () => abortRef.current?.abort()

  return { run, stop, running }
}

function parseSSEFrame(raw, onSources, onToken, onDone) {
  let eventType = ''
  let dataStr = ''

  for (const line of raw.split('\n')) {
    if (line.startsWith('event:')) eventType = line.slice(6).trim()
    else if (line.startsWith('data:')) dataStr += line.slice(5).trim()
  }

  if (!dataStr) return

  try {
    const data = JSON.parse(dataStr)
    if (eventType === 'sources') onSources?.(data)
    else if (eventType === 'token') onToken?.(data.t)
    else if (eventType === 'done') onDone?.(data)
  } catch {
    // ignore malformed
  }
}
