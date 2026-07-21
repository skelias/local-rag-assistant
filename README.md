# RAG AI 助手

本地 RAG 知识库 + AI 助手系统，基于检索增强生成和多步推理 Agent。

## 技术栈

- **后端**: Python · FastAPI · LangChain · LangGraph · Qdrant
- **前端**: React 18 · Vite · TailwindCSS · Zustand
- **模型**: Claude API (主力) · DeepSeek API (降级备选)
- **Embedding**: BGE-M3 (本地) · text-embedding-3-small (API 备选)

## 项目结构

```
rag/
├── backend/              # FastAPI 后端
│   ├── api/              # 路由、中间件、依赖注入
│   ├── core/             # RAG Engine + Agent Core + LLM Gateway
│   ├── models/           # 数据模型
│   └── services/         # 业务逻辑
├── frontend/             # React 前端
├── data/                 # SQLite + Qdrant 本地数据 (git 不追踪)
├── .env                  # API 密钥 (git 不追踪)
└── .env.example          # 密钥格式参考
```

## 快速开始

```bash
# 1. 配置密钥
cp .env.example .env
# 编辑 .env 填入 API Key

# 2. 启动后端
cd backend
pip install -r requirements.txt
uvicorn api.app:app --reload

# 3. 启动前端
cd frontend
npm install
npm run dev
```

## 安全

- `.env` 和 `data/` 目录不进入 Git
- API 密钥只存本地，通过环境变量或 SQLite 配置表读取
- 切换到新电脑只需重配密钥
