# 项目进度追踪（随课程勾选）

> P0-1 ~ P0-8 后端（执行计划：`docs/plans/2026-09-07-p0-execution-backend.md`）
> P0-9 ~ P0-12 前端（执行计划：`docs/plans/2026-09-07-p0-execution-frontend.md`）

## 后端

- [x] **P0-1 脚手架**（第 3-4 课）—— 配置模块 + 首个 pytest 绿
      ⚠️ 教学节奏说明：`run.py` 入口文件推迟到 P0-7（真正能启动服务器那课）再建
- [x] **P0-2 Storage** — SQLite 建表 + Repository（第 5-7 课，12 测试绿）
- [ ] **P0-3 LLM Gateway** — 调云端模型
- [ ] **P0-4 Embedding + Qdrant** — 向量化 + 混合检索
- [ ] **P0-5 RAG Engine** — 检索→上下文→流式生成
- [ ] **P0-6 文档管线** — 上传/解析/分块/预览/确认
- [ ] **P0-7 API Gateway** — FastAPI 路由 + SSE
- [ ] **P0-8 端到端** — 全链路测试

## 前端

- [ ] **P0-9 脚手架 + 样式 token** — Vite + LiquidRAG 风格
- [ ] **P0-10 四视图（mock）**
- [ ] **P0-11 接真实 API + i18n**
- [ ] **P0-12 单端口托管 + 脚本**

## 已提交里程碑

| commit | 内容 |
|---|---|
| b537b71 | 项目脚手架（gitignore/README/.env.example） |
| 238e58a / 7333fb6 | 对标调研 + 规格 + 修订 P0 + 设计资产 |
| 7fc227a | 后端/前端执行计划 |
| 1d53dc6 ~ 74f5941 | 学习笔记（第 1-2 课） |
| 93dbe08 | P0-1：包骨架 + 配置 + 首个测试绿 |

