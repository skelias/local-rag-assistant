# 项目进度追踪

> P0-1 ~ P0-8 后端（执行计划：`docs/plans/2026-09-07-p0-execution-backend.md`）
> P0-9 ~ P0-12 前端（执行计划：`docs/plans/2026-09-07-p0-execution-frontend.md`）

## 后端

- [x] **P0-1 脚手架**（第 3-4 课）—— 配置模块 + 首个 pytest 绿
- [x] **P0-2 Storage** — SQLite 建表 + Repository（第 5-7 课，12 测试绿）
- [x] **P0-3 LLM Gateway** — 调云端模型（第 8-10 课，真调用冒烟通过）
- [x] **P0-4 Embedding + Qdrant** — 向量化 + 混合检索
- [x] **P0-5 RAG Engine** — 检索→上下文→流式生成（第 12 课；HTTP 接线在 P0-7）
- [x] **P0-6 文档管线** — 解析/分块/上传落盘/预览/确认（第 13-14 课）
- [x] **P0-7 API Gateway** — FastAPI 路由 + SSE（第 15-17 课）
- [x] **P0-8 端到端** — 全链路测试 + 真实 MVP 验收（第 18 课，fastembed + DeepSeek）

## 前端

- [x] **P0-9 脚手架 + 样式 token** — Vite + React + Tailwind + Glassmorphism 风格 + i18n 骨架
- [x] **P0-10 四视图** — 对话(流式+来源抽屉) / 知识库(上传+卡片+命中测试) / Agent / 设置
- [x] **P0-11 接真实 API + i18n** — SSE hook / REST client / 命中测试面板 / 语言切换
- [x] **P0-12 分发** — setup.bat / start.bat / 单端口静态托管 / README 收尾

## 已提交里程碑

| commit | 内容 |
|---|---|
| b537b71 | 项目脚手架（gitignore/README/.env.example） |
| 238e58a / 7333fb6 | 对标调研 + 规格 + 修订 P0 + 设计资产 |
| 7fc227a | 后端/前端执行计划 |
| 93dbe08 ~ 74f5941 | P0-1 ~ P0-2 后端脚手架 + 数据层 |
| a35d706 ~ 2a59088 | P0-3 LLM Gateway（多 provider + 降级 + 用量） |
| e2c5d5b ~ >568c099 | P0-4 ~ P0-7（Embedding/Qdrant/RAG/文档管线/API路由/SSE） |
| 103d7a3 | P0-8 真实端到端 MVP（fastembed + DeepSeek） |
| 52893be | P0-9 前端脚手架 + Glassmorphism token + 四视图 + i18n |
| 40d7ffe | P0-11 真实 API client + SSE hook + 命中测试面板 |

## 待办/阻塞

- BGE-M3（1024 维）升级：国内镜像/ModelScope/官方对大文件下载均停滞（2026-09-08 实测），暂时保留 fastembed MVP；网络好时用 scripts/download_bge_m3.py 再试。
