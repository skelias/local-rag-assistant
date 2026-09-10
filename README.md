# RAG AI 助手 v1.0.0

本地 RAG 知识库 + AI 助手：上传你的文档/代码 → 混合检索 → 云端大模型基于资料流式回答，并给可点击的来源引用。
数据全部留在本机（`data/` 整体拷贝即为备份），模型与密钥可在界面里直接配置。

> **状态：v1.0.0 定稿** — 后端 49 个自动化测试全绿，前端构建通过，真实端到端已验收（上传 → 向量化 → 检索 → 模型带引用回答）。
> 一键启动：`setup.bat` → `start.bat`（自动打开 `http://127.0.0.1:8000`）。

## 技术栈

| 层级 | 技术 |
|---|---|
| 后端 | Python 3.12+ / FastAPI / aiosqlite / Qdrant(本地文件模式) |
| 前端 | React 18 / Vite / TailwindCSS / Zustand / Lucide Icons |
| 检索 | 稠密向量(fastembed bge-small-zh 512d) + 稀疏 BM25 + RRF 融合，可选 Rerank |
| 模型 | Claude / DeepSeek / 智谱 GLM / Kimi / OpenAI(GPT) + **任意 OpenAI 兼容端点（自定义）** |
| 可观测 | 每次调用记录 token 与**缓存命中率**（不做金额计费） |

## 快速开始

```bash
# 方式 A：完全在界面里配置（推荐，不用碰 .env）
setup.bat        # 安装依赖（后端 venv + 前端 node_modules）
start.bat        # 启动并自动打开浏览器
# 打开 设置 → 模型/密钥：填 API Key、加模型名（可"拉取模型列表"）→ 保存

# 方式 B：用 .env 配密钥
cp .env.example .env   # 填 CLAUDE_API_KEY / DEEPSEEK_API_KEY 等
setup.bat && start.bat
```

浏览器打开 `http://127.0.0.1:8000`（单端口同时托管 API 与前端构建产物）。

### 手动启动（开发模式）

```bash
cd backend && pip install -r requirements.txt && python run.py
cd frontend && npm install && npm run dev     # http://localhost:5173（代理到 8000）
```

## 功能一览

- **对话**：SSE 流式回答、来源引用 `[n]` 可点开抽屉（文件/页码/分数/片段）、停止生成、低置信提示
- **知识库**：多库切换（全部知识库 / 代码库 / 笔记库）、上传（md/txt/代码…）→ 分段预览 → 确认入库、状态徽章、删除
- **检索调试**：命中测试面板，与对话**共用同一份检索参数**（单一参数源），展示混合得分构成
- **模型管理**：设置页直接填 API Key / Base URL / 模型名；一键"拉取模型列表"（端点 `/models`）；支持**添加自定义模型**（任意 OpenAI 兼容端点）；主力/降级自动切换；**保存即时生效，无需重启**
- **个性化**：界面语言（中/英）、背景（预设或上传图片）、用户与 AI 头像（上传图片）
- **工程**：单端口托管、一键脚本、数据单目录备份、49 个 pytest、前端构建校验

## 数据与备份

```
data/
  rag.db        # SQLite：文档/分块/会话/配置/用量
  qdrant/       # 向量索引
  uploads/      # 上传的原始文件
  media/        # 背景图与头像
```

**备份 / 迁移 = 整体拷贝 `data/` 目录。**

## 项目结构

```
backend/
  app/core/       config · llm_gateway(多 provider/降级/用量) · embedding · vector_store(混合检索)
  app/models/     database(7 表) · schemas
  app/services/   repositories · rag_engine · doc_pipeline
  app/api/        app · deps · routes(health/chat/knowledge/config/profile/llm)
  tests/          49 个测试
  scripts/        real_e2e / smoke_llm / smoke_profile / list_models / download_bge_m3
frontend/
  src/components/ Sidebar · TopBar · MessageBubble · SourceDrawer · LiquidInput · DocCard · ErrorBoundary
  src/views/      ChatView · KnowledgeView · AgentView · SettingsView
  src/api/        client.js        src/hooks/ useChatStream.js
data/            本地数据（git 不追踪）
docs/
  plans/          执行计划与路线
  research/       7 个成熟开源产品对标
  designs/        设计规格 / 皮肤映射 / 变体预览（含定稿 variant-e-dsh-style.html）
  learning/       19 课学习笔记 + 进度表
```

## 安全

- `.env`、`data/`、`venv/`、`node_modules/`、`frontend/dist/` 均不进入 Git
- API 密钥只存本地（`.env` 或本机 SQLite 设置表），代码不硬编码模型名/密钥
- 上传校验（类型白名单 + 大小上限 + 文件名清洗），引用来源结构化可追溯

## 已知限制 / 后续

- Agent 工作区为占位（多步推理与工具调用属下一阶段）
- 扫描件 PDF / OCR、原文高亮预览、会话列表管理等在产品化阶段（P1）
- 可选升级：本地 BGE-M3 嵌入（1024 维）替换当前轻量 fastembed（需下载较大模型）

## License

MIT
