# RAG AI 助手

本地 RAG 知识库 + AI 助手，基于检索增强生成（RAG）与多步推理 Agent。

> **状态：P0 全线完成** — 后端（P0-1~P0-8）+ 前端（P0-9~P0-12）均已落地。
> 运行 `setup.bat` → `start.bat` 即可一键启动。

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / aiosqlite / Qdrant(本地) |
| 前端 | React 18 / Vite / TailwindCSS / Zustand / Lucide Icons |
| LLM | Claude API (主力) / DeepSeek API (降级) / GLM / Kimi / OpenAI |
| Embedding | fastembed (bge-small-zh 512d + BM25 sparse) / BGE-M3 (待升级) |

## 快速开始

```bash
# 1. 配置密钥
cp .env.example .env        # 编辑填入 API Key

# 2. 一键安装
setup.bat

# 3. 一键启动（自动开浏览器）
start.bat
```

浏览器打开 `http://127.0.0.1:8000` 即可使用。

### 手动启动（开发模式）

```bash
# 后端
cd backend
pip install -r requirements.txt
python run.py

# 前端（另开终端）
cd frontend
npm install
npm run dev          # http://localhost:5173
```

## 功能

- 上传文档（Markdown / 文本 / 代码文件）→ 解析分块 → 预览确认 → 向量化入库
- 混合检索（稠密向量 + BM25 稀疏 + RRF 融合）
- 流式对话（SSE），答案带可点击来源引用 `[n]`
- 命中测试面板（与对话共用检索参数，单一参数源）
- 主力/降级 Provider 自动切换（Claude → DeepSeek）
- 多知识库预留（kb_id）
- Glassmorphism 风格 UI，中文/英文双语

## 数据与备份

所有数据收拢在 `data/` 目录：

```
data/
  rag.db         # SQLite：元数据/会话/配置/用量
  qdrant/        # 向量索引
  uploads/       # 原始文件
```

**备份/迁移 = 整体拷贝 `data/` 目录。**

## 项目结构

```
backend/           # FastAPI 后端
  app/
    core/          # config / llm_gateway / embedding / vector_store
    models/        # database + schemas
    services/      # repositories / rag_engine / doc_pipeline
    api/           # app + deps + routes
  tests/           # 43 个自动化测试
frontend/          # React 前端
  src/
    components/    # Sidebar / TopBar / MessageBubble / SourceDrawer / LiquidInput / DocCard
    views/         # ChatView / KnowledgeView / AgentView / SettingsView
    api/           # client.js (REST)
    hooks/         # useChatStream.js (SSE)
data/              # 本地数据（git 不追踪）
docs/
  plans/           # 执行计划
  research/        # 对标调研
  designs/         # 前端设计定稿 + 静态预览
  learning/        # 学习笔记 1-18 课
```

## 安全

- `.env`、`data/` 不进入 Git
- API 密钥只存本地，模型名以配置为准（不硬编码）
- 知识库对话引用来源结构化（score / file / page / chunk）
- 上传校验：类型白名单 + 大小上限 + 文件名清洗

## License

MIT
