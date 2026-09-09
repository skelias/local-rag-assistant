/** API client — all backend calls go through here. */
const j = async (url, opts) => {
  const r = await fetch(url, opts)
  if (!r.ok) throw new Error((await r.text()) || `HTTP ${r.status}`)
  return r.json()
}

export const api = {
  upload: (kbId, file) => {
    const f = new FormData()
    f.append('file', file)
    return j(`/api/knowledge/${kbId}/documents`, { method: 'POST', body: f })
  },
  docs: (kbId) => j(`/api/knowledge/${kbId}/documents`),
  preview: (kbId, id) => j(`/api/knowledge/${kbId}/documents/${id}/preview`),
  confirm: (kbId, id) => j(`/api/knowledge/${kbId}/documents/${id}/confirm`, { method: 'POST' }),
  removeDoc: (kbId, id) => j(`/api/knowledge/${kbId}/documents/${id}`, { method: 'DELETE' }),
  hitTest: (kbId, query, opts = {}) =>
    j(`/api/knowledge/${kbId}/hit-test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, ...opts }),
    }),
  getConfig: () => j('/api/config'),
  putConfig: (key, value) =>
    j('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, value }),
    }),
}
