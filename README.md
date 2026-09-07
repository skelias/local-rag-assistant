# RAG 个人 AI 助手

本地 RAG 知识库 + AI 助手系统，基于检索增强生成和多步推理 Agent。

> **状态：路线已确认（2026-09-07）** —— 采用"方案二"（LangChain + LangGraph + Qdrant 本地 + FastAPI + React），
> 经 7 个成熟开源产品对标后按**修订版 P0** 执行（`docs/plans/2026-09-07-mature-product-spec-and-p0.md`）。
> 设计期完成，代码尚未开工。

## 技术栈

- **后端**: Python 3.12+ · FastAPI · LangChain · LangGraph · Qdrant(本地) · SQLite
- **前端**: React 18 · Vite · TailwindCSS · Zustand
- **模型**: Claude API (主力) · DeepSeek API (降级备选)（全部云端，Key 本地保存）
- **Embedding**: BGE-M3 (本地) · text-embedding-3-small (API 备选)

## 目标结构（修订 P0 蓝图）

```
├── backend/                  # FastAPI 后端
│   ├── run.py
│   ├── app/
│   │   ├── core/             # config / llm_gateway(provider 数据化) / embedding / vector_store
│   │   ├── models/           # database(kb_id/status/jobs/config/usage) + schemas
│   │   ├── services/         # repositories / rag_engine / doc_pipeline(Parser·Splitter·Indexer 契约) / hit-test
│   │   └── api/              # app / deps / routes: health·chat·knowledge·hit-test·config
│   └── tests/
├── frontend/                 # React（LiquidRAG 风格，见 docs/designs/）
├── data/                     # 本地数据：rag.db + qdrant/ + uploads/（git 不追踪）
├── docs/
│   ├── plans/                # 实施计划与路线
│   ├── research/             # 成熟产品对标
│   └── designs/              # 前端设计定稿（4 版原型）
├── .env                      # API 密钥（git 不追踪）
└── .env.example              # 密钥格式参考（提交）
```

**备份/迁移 = 拷贝 `data/` 目录整体。**（单目录数据模型）

## 文档索引

| 文档 | 内容 |
|---|---|
| `docs/plans/2026-09-07-mature-product-spec-and-p0.md` | **执行蓝图**：成熟化规格 + 修订 P0（P0-0~P0-12） |
| `docs/research/2026-09-07-mature-benchmark.md` | 7 项目对标深化 + 许可矩阵 |
| `docs/plans/2026-08-02-benchmark-and-roadmap.md` | 8 项目调研 + P0/P1/P2 路线（历史） |
| `docs/plans/2026-07-22-backend-phase1.md` | 原 Phase1 8 Tasks（被修订 P0 吸收，历史参考） |
| `docs/designs/README.md` | 前端定稿索引与风格要点 |

## 快速开始（P0 落地后生效）

```bash
# 1. 配置密钥
cp .env.example .env   # 编辑填入 API Key

# 2. 启动后端
cd backend
pip install -r requirements.txt
python run.py          # 或 uvicorn app.api.app:app --reload

# 3. 启动前端
cd frontend
npm install
npm run dev
```

## 安全

- `.env`、`data/`、`.superpowers/` 不进入 Git
- API 密钥只存本地，通过环境变量或 SQLite 配置表读取；模型名以配置为准（不硬编码）
- 知识库对话引用来源结构化（score/file/page/chunk），命中测试与对话共用检索参数
