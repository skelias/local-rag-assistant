# RAG AI 助手 — P0 执行计划 · 前端与分发（P0-9 ~ P0-12）

> **For Claude/编码 Agent:** 依赖后端执行计划 `docs/plans/2026-09-07-p0-execution-backend.md`（P0-1~P0-8）的 API 契约，见该文末"与前端计划的衔接"。设计定稿见 `docs/designs/liquidrag-style-v1.html`（本计划的样式 token 从该文件抽取）。
>
> 语言：JSX（React 18）+ Vite + TailwindCSS + Zustand。中文默认，i18n 骨架 zh/en（趁早，成本极低）。

**Goal:** 前端按 LiquidRAG"黑暗泻湖"风格落地四视图（对话/知识库/Agent 占位/设置），接通后端 API 形成端到端体验；产物可被 FastAPI 静态托管；根目录一键 setup/start 脚本。

---

## Task P0-9: 前端脚手架 + 设计 token + 布局骨架 + i18n 骨架

**Files:**
- Run: `cd "D:\RAG个人AI助手" && npm create vite@latest frontend -- --template react`
- Edit/Add: `frontend/package.json`(react>=18, zustand, tailwindcss@3, postcss, autoprefixer) · `frontend/vite.config.js`(proxy) · `frontend/tailwind.config.js` · `frontend/src/index.css` · `frontend/src/i18n.js` · `frontend/src/app/store.js` · `frontend/src/App.jsx` · 侧栏/布局组件

**Step 1: 脚手架 + 依赖**
```bash
cd "D:\RAG个人AI助手\frontend"
npm install
npm install zustand
npm install -D tailwindcss@3.4 postcss autoprefixer
npx tailwindcss init -p
```
**Step 2: `frontend/vite.config.js`**（开发代理到后端）
```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { outDir: 'dist', emptyOutDir: true },
})
```
**Step 3: 设计 token `frontend/tailwind.config.js`**（抽取自定稿原型，勿复刻第三方视觉，仅为自家实现）
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        obsidian: '#0A0A0F',
        'obsidian-light': '#0F0F16',
        aurora: { cyan: '#22d3ee', violet: '#a78bfa' },
        slatecool: '#94a3b8',
      },
      borderRadius: { 'bubble-user': '24px 24px 6px 24px', 'bubble-ai': '6px 24px 24px 24px' },
      boxShadow: {
        'glass': '0 0 0 1px rgba(255,255,255,.08), 0 12px 40px -12px rgba(0,0,0,.7)',
        'glow': '0 0 24px -6px rgba(167,139,250,.5)',
      },
      keyframes: {
        caustic: { '0%,100%': { transform: 'translate(0,0) scale(1)' },
                   '50%': { transform: 'translate(6%,4%) scale(1.15)' } },
        spinborder: { to: { '--border-angle': '360deg' } },
      },
      animation: { caustic: 'caustic 22s ease-in-out infinite', 'border-spin': 'spinborder 4s linear infinite' },
    },
  },
  plugins: [],
}
```
**Step 4: 全局样式与玻璃气泡 `frontend/src/index.css`**
```css
@tailwind base; @tailwind components; @tailwind utilities;

:root { color-scheme: dark; --border-angle: 0deg; }
body { @apply bg-obsidian text-slate-200 antialiased; }

/* 焦散光斑背景层 */
.caustic-bg { background: radial-gradient(60rem 30rem at 15% 10%, rgba(34,211,238,.07), transparent 60%),
                         radial-gradient(50rem 30rem at 85% 20%, rgba(167,139,250,.08), transparent 60%),
                         radial-gradient(40rem 26rem at 50% 90%, rgba(34,211,238,.05), transparent 60%); }

/* 3 层玻璃气泡：玻璃底座（亮度层）→ 渐变色彩层 → 噪点近似用渐变叠加 */
.glass-bubble { @apply backdrop-blur-xl rounded-3xl shadow-glass;
  background: linear-gradient(160deg, rgba(255,255,255,.10), rgba(255,255,255,.02) 45%, rgba(167,139,250,.06)); }
.glass-user { @apply glass-bubble rounded-bubble-user text-slate-50;
  background: linear-gradient(140deg, rgba(34,211,238,.10), rgba(167,139,250,.06)); }
.glass-ai { @apply glass-bubble rounded-bubble-ai; }

/* Liquid Edge 输入栏：聚焦时 conic 边框旋转 */
.liquid-edge { position: relative; }
.liquid-edge::before { content: ''; position: absolute; inset: -1px; border-radius: inherit; padding: 1px;
  background: conic-gradient(from var(--border-angle), transparent 0%, rgba(34,211,238,.7) 20%, rgba(167,139,250,.7) 40%, transparent 60%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude; opacity: 0; transition: opacity .3s; }
.liquid-edge:focus-within::before { opacity: 1; animation: border-spin 4s linear infinite; }

/* 2px 玻璃滚动条 */
*::-webkit-scrollbar { width: 2px; height: 2px; }
*::-webkit-scrollbar-thumb { background: rgba(148,163,184,.3); border-radius: 9999px; }
*::-webkit-scrollbar-track { background: transparent; }

/* 来源引用标签 */
.cite-tag { @apply inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs cursor-pointer
  text-cyan-200/90 hover:bg-cyan-400/10; }
```
**Step 5: i18n 骨架 `frontend/src/i18n.js`**
```js
const dict = {
  zh: { nav_chat: '对话', nav_kb: '知识库', nav_agent: 'Agent', nav_settings: '设置',
        input_ph: '输入问题…', send: '发送', stop: '停止', sources: '来源', upload: '上传文档',
        preview: '分段预览', confirm: '确认入库', status_ready: '可用', status_parsed: '待确认',
        status_failed: '失败', hit_test: '命中测试', low_confidence: '知识库可能未覆盖此问题',
        settings_title: '设置', model: '模型', api_key: 'API Key' },
  en: { nav_chat: 'Chat', nav_kb: 'Knowledge', nav_agent: 'Agent', nav_settings: 'Settings',
        input_ph: 'Ask anything…', send: 'Send', stop: 'Stop', sources: 'Sources', upload: 'Upload',
        preview: 'Chunk preview', confirm: 'Index', status_ready: 'Ready', status_parsed: 'Awaiting',
        status_failed: 'Failed', hit_test: 'Hit test', low_confidence: 'May not be covered by KB',
        settings_title: 'Settings', model: 'Model', api_key: 'API Key' },
}
let lang = localStorage.getItem('lang') || 'zh'
export const t = (k) => dict[lang][k] ?? k
export const setLang = (l) => { lang = l; localStorage.setItem('lang', l) }
export const getLang = () => lang
```
> 执行说明：i18n 以 t() 起步即可，字典后续按组件补齐；本轮仅骨架 + 导航/常用词。

**Step 6: 布局骨架**
- `src/App.jsx`：`.caustic-bg fixed inset-0 -z-10` + 左侧边栏 + 主区（按 nav 状态切 4 个视图占位）。
- `src/components/Sidebar.jsx`：Logo、四项导航（`dialog`/`knowledge`/`agent`/`settings`）、历史会话列表（P1 完善，P0 显示占位）。
- `src/store.js`（Zustand）：`{nav, setNav, lang, toggleLang}`。

**Step 7: 验证**
```bash
cd frontend && npm run build     # 必须零错误
npm run dev                      # 浏览器 http://localhost:5173 看黑曜石背景+玻璃侧栏
```
**Step 8: 提交** `git add frontend/ && git commit -m "feat(p0-9): frontend scaffold with liquidrag tokens, layout, i18n zh/en"`

---

## Task P0-10: 四视图骨架（对话/知识库/Agent 占位/设置）— mock 先行

**Files:**
- Add: `src/views/ChatView.jsx`、`KnowledgeView.jsx`、`AgentView.jsx`、`SettingsView.jsx`
- Add: `src/components/MessageBubble.jsx`、`SourceDrawer.jsx`、`LiquidInput.jsx`、`ChatHistoryItem.jsx`、`DocRow.jsx`、`HitTestPanel.jsx`（后两个可先占位）
- Add: `src/api/mock.js`（开关：`useMock` 为 true 时返回假流/假文档，便于先调 UI）

**Step 1: mock 层 `src/api/mock.js`**（先于后端联调）
```js
export const useMock = true
export const mockDocs = [
  { id: 1, filename: 'guide.md', status: 'ready', chunk_count: 12 },
  { id: 2, filename: 'api.md', status: 'parsed', chunk_count: 8 },
]
export async function mockChatStream(query, onEvent) {
  onEvent({ event: 'sources', data: [{ n: 1, file: 'guide.md', score: 0.81, text: '…' }] })
  for (const ch of Array.from('这是 mock 回答。')) { await new Promise(r => setTimeout(r, 30)); onEvent({ event: 'token', data: { t: ch } }) }
  onEvent({ event: 'done', data: { conversation_id: 1 } })
}
```

**Step 2: 对话视图要点（LiquidRAG 交互）**
- `ChatView.jsx`：消息列表（用户 → `glass-user` 右对齐；AI → `glass-ai` 左对齐 + 折叠思考区占位）+ `SourceDrawer`（右滑毛玻璃：每条来源含 file/score/置信度水填充条/text 摘要）+ `LiquidInput`（发送/停止）。
- 气泡内 Markdown 渲染：`react-markdown` + 代码块深色容器 + 复制按钮（P0 用 `<pre>` 简单高亮即可，P1 换 shiki/prism）。
- 置信度条：来源 `score` 映射 `w = min(score*100,100)%`。

**Step 3: 知识库视图要点**
- 上传（拖拽/选择）→ 调 mock 返回 `status:'parsed'` → 弹"分段预览"抽屉（只读列表：序号+text 前 200 字+meta）→ 点"确认入库"→ 状态变 ready。交互路径先通，后端 P0-11 换真。
- 文档列表 `DocRow`：文件名、状态徽章（parsed=待确认/ready=可用/failed=失败+错误）、删除。

**Step 4: Agent / 设置占位**
- `AgentView.jsx`：空态说明 +（P2 落地）占位卡片。
- `SettingsView.jsx`：三组表单（LLM：provider/模型/Key；检索：top_k/阈值/rerank 开关；语言切换），本地 localStorage 先存，P0-11 接 `/api/config`。

**Step 5: 验证**（mock 模式）：四视图可切换；对话 mock 流式渲染、引用可打开来源抽屉；上传→预览→确认状态流转。
**Step 6: 提交** `git commit -m "feat(p0-10): four liquidrag views with mock data flow"`

---

## Task P0-11: 接入真实 API（SSE 流 + 上传/预览/确认/命中测试/配置）+ i18n 补全

**Files:**
- Add: `src/api/client.js`（fetch 封装，`useMock=false` 切换）
- Add: `src/hooks/useChatStream.js`（SSE 解析：sources → token → done）
- Edit: 各 view 把 mock 调用替换为 client/hook；`SettingsView` 接 `/api/config`
- Add: `frontend/vite.config.js` 已含 proxy（见 P0-9）

**Step 1: SSE hook `src/hooks/useChatStream.js`**
```js
import { useState } from 'react'

export function useChatStream() {
  const [running, setRunning] = useState(false)
  const abortRef = { ctrl: null }

  const run = async ({ kbId, query, conversationId, onToken, onSources, onDone }) => {
    if (running) return
    setRunning(true)
    const ctrl = new AbortController(); abortRef.ctrl = ctrl
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
        let idx
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const raw = buf.slice(0, idx); buf = buf.slice(idx + 2)
          const data = raw.split('\n').filter(l => l.startsWith('data:')).map(l => l.slice(5)).join('')
          if (!data) continue
          const msg = JSON.parse(data)
          if (msg.event === 'sources') onSources?.(msg.data)
          else if (msg.event === 'token') onToken?.(msg.data.t)
          else if (msg.event === 'done') onDone?.(msg.data)
        }
      }
    } finally { setRunning(false) }
  }
  const stop = () => abortRef.ctrl?.abort()
  return { run, stop, running }
}
```
> 说明：后端 `EventSourceResponse` 输出 `event: <type>\ndata: <json>`。若解析与后端格式不符，以实测为准微调（事件间用空行分隔）。

**Step 2: API client `src/api/client.js`**
```js
const j = async (url, opts) => { const r = await fetch(url, opts); if (!r.ok) throw new Error((await r.text()) || r.status); return r.json() }
export const api = {
  upload: (kbId, file) => { const f = new FormData(); f.append('file', file); return j(`/api/knowledge/${kbId}/documents`, { method: 'POST', body: f }) },
  docs: (kbId) => j(`/api/knowledge/${kbId}/documents`),
  preview: (kbId, id) => j(`/api/knowledge/${kbId}/documents/${id}/preview`),
  confirm: (kbId, id) => j(`/api/knowledge/${kbId}/documents/${id}/confirm`, { method: 'POST' }),
  removeDoc: (kbId, id) => j(`/api/knowledge/${kbId}/documents/${id}`, { method: 'DELETE' }),
  hitTest: (kbId, query) => j(`/api/knowledge/${kbId}/hit-test`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ query }) }),
  getConfig: () => j('/api/config'),
  putConfig: (key, value) => j('/api/config', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key, value }) }),
}
```

**Step 3: 视图接线**
- `ChatView`：`useChatStream`；AI 回答追加 `sources`（`SourceDrawer`）；低置信（hits 为空或最高 score<0.3）时提示 `low_confidence`。
- `KnowledgeView`：上传→`api.upload`→预览抽屉（读 `api.preview` 列表，只读）→`api.confirm`（返回 indexing/ready，P0 轮询 `api.docs` 至 ready）→列表刷新；删除 `api.removeDoc`。
- 视图内新增"命中测试"小面板：输入问题→`api.hitTest`→列出 hits（file/score_breakdown/阈值标记 passed）——与对话检索同源验证。
- `SettingsView`：读 `api.getConfig()` 渲染 `llm.primary_model`、`llm.primary_provider`、`kb.1.retrieval.top_k/threshold/rerank_enabled` 等；保存 `api.putConfig`；语言切换 `setLang`。

**Step 4: 联调验证**
```bash
# 终端1（后端）  终端2（前端）
venv\Scripts\python -m uvicorn app.api.app:app --port 8000     # 在 backend/
npm run dev                                                     # 在 frontend/
```
手工：上传 `guide.md` → 预览分段 → 确认 → 提问"Qdrant 如何融合"→ 流式回答 + 可点来源；切 DeepSeek 降级正常；设置改 top_k 后命中测试立即生效（同一参数源）。

**Step 5: 提交** `git commit -m "feat(p0-11): wire real API with SSE stream, preview/confirm, hit-test, config"`

---

## Task P0-12: 单端口托管 + 一键脚本 + README 收尾

**Files:**
- Edit: `backend/app/api/app.py`（条件挂载 `frontend/dist`）
- Add: `backend/app/api/static_router.py` 或直接在 create_app 末尾挂载
- Add: `setup.bat`、`start.bat`（仓库根）
- Edit: `README.md`（双语小节、备份约定、快速开始用脚本）

**Step 1: FastAPI 托管构建产物（存在 dist 时）`backend/app/api/app.py` 追加**
```python
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

DIST = Path(__file__).resolve().parent.parent.parent.parent.parent / "frontend" / "dist"

def mount_frontend(app: FastAPI) -> None:
    if not DIST.exists():
        return  # 未构建时不挂载（开发分离）
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        target = DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        return FileResponse(DIST / "index.html")  # SPA fallback
```
> 注意：静态托管在 `api/*` 路由之后追加（FastAPI 路由匹配顺序先注册先匹配）；`create_app` 末尾调用 `mount_frontend(app)`。

**Step 2: 一键脚本 `setup.bat`（仓库根）**
```bat
@echo off
chcp 65001 >nul
echo === RAG AI 助手 环境配置 ===
cd /d "%~dp0"
if not exist .env copy .env.example .env >nul & echo [提示] 已生成 .env，请填入 API Key
if not exist backend\venv (
  cd backend
  python -m venv venv || (echo 请先安装 Python 3.12+ & pause & exit /b 1)
  venv\Scripts\pip install -U pip
  venv\Scripts\pip install -r requirements.txt || (echo 依赖安装失败 & pause & exit /b 1)
  cd ..
)
if not exist frontend\node_modules (
  cd frontend
  call npm install || (echo npm install 失败 & pause & exit /b 1)
  cd ..
)
echo 配置完成：编辑 .env 后运行 start.bat
pause
```
**Step 3: `start.bat`**
```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist backend\venv ( echo 请先运行 setup.bat & pause & exit /b 1 )
if not exist frontend\dist ( echo 构建前端中… & cd frontend & call npm run build & cd .. )
start "" http://127.0.0.1:8000
cd backend
venv\Scripts\python -m uvicorn app.api.app:app --host 127.0.0.1 --port 8000
```
**Step 4: README 双语收尾**：快速开始改为 `setup.bat` → `start.bat`；补充"备份/迁移 = 拷贝 data/"；英文标题与链接（i18n 已在 UI）。
**Step 5: 验证**：`npm run build` → `start.bat` → 浏览器自动打开 8000 → 全流程跑通。
**Step 6: 提交** `git commit -m "feat(p0-12): single-port static hosting, setup/start scripts, readme wrap-up"`

---

## P0 前端验收（与后端合起来）

全新用户：`setup.bat`（Key 已填）→ `start.bat` → 浏览器打开 → 上传 md/code 文件 → 分段预览确认 → 提问 → 流式回答 + 可点击来源（file/score/置信度条）；知识库视图"命中测试"与对话结果参数一致；设置改模型/阈值即时生效；`data/` 拷贝即迁移。

## 明确不做（P1/P2）

OCR、命中→改分块、证据多分数面板、原文高亮预览、库 zip 导出、消息编辑/分支、文件级检索范围、多模型对比、MCP、记忆/定时任务、代码执行。
