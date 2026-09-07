# RAG 个人 AI 助手 — 成熟化产品规格 + 修订版 P0 任务清单（2026-09-07）

> 输入：`docs/plans/2026-08-02-benchmark-and-roadmap.md`（P0/P1/P2 路线）
> + `docs/research/2026-09-07-mature-benchmark.md`（7 项目产品惯例深挖）
> + `docs/plans/2026-07-22-backend-phase1.md`（8 Task 实施计划，含 TDD）
> 目的：把"成熟产品经验"翻译成本项目的**功能规格与修订 P0**。只借鉴理念，不复制任何代码（许可红线见对标报告 §5）。

---

## 1. 定位（不变，重述以对齐）

单用户、本地运行、免 Docker 优先的 RAG 个人 AI 助手：
- 知识以**代码 + 技术文档**为主（含扫描件/表格/专有名词/错误码），辅以个人笔记；
- Web GUI（React），多步推理 Agent（LangGraph）内置；
- 模型全走云端 API（Claude 主力 / DeepSeek 降级），embedding 本地 BGE-M3（API 备选）；
- 用户可在 GitHub 开源 → **隐私与许可安全是第一约束**。

## 2. 产品原则（对标提炼 × 本项目约束，8 条）

1. **检索可信度即产品成败**：混合检索（稠密 + 全文）+ rerank 是标配；检索参数可视化可调；命中测试与真实对话**共用同一参数源**。
2. **引用是一等公民**：答案内 `[n]` → 可点开原文片段/高亮/定位 → 带分数；低置信显式提示。
3. **内容质量门**：解析器/分块器可插拔、统一产物契约；**入库前分段预览 + 人工校正**；文档状态机可视、可手动复位。
4. **多知识库现在建模**：全表 `kb_id`（default=1），库级独立模型/参数/上传规则；换 embedding = 全量重嵌并 UI 警告。
5. **对话体验完整**：SSE 流式 + 停止/重发 + 会话管理；Agent 思考/工具调用折叠展示；文件范围显式选择。
6. **上手即用、备份即拷贝**：一键 setup/start 脚本 + 浏览器自动打开；**单一数据目录**（`data/`）整体拷贝即备份迁移。
7. **数据本地 + 透明遥测**：Key 只存本地；默认无遥测，若要上报走"匿名 + 可关 + 源码可见"清单。
8. **安全默认从严**：上传校验；命令/代码执行默认人工确认，任意代码执行默认不做（沙箱是硬仗，P2 再说）。

---

## 3. 成熟 MVP（修订 P0）功能规格

> P0 目标不变：**上传文档 → 提问 → 流式回答带可点击来源**，但按对标把"可信度与产品壳"做足。
> 每项标 [来源项目] 表示借鉴其产品理念。

### A. 数据与备份 —— 单目录模型 [kotaemon / Open WebUI]
- 目录布局（README 已有的 `data/` 扩展为规范）：
  ```
  data/
  ├── rag.db            # SQLite：元数据/会话/配置/用量（README 已定）
  ├── qdrant/           # 向量（README 已定）
  ├── uploads/          # 原始文件（README 已定）
  └── export/           # 整库导出 .zip 的临时/目标目录（P1）
  ```
- README 明示：**备份/迁移 = 拷贝 `data/`**。
- 规则：`.gitignore` 已排除 `data/`，不变。

### B. 知识库模型（多库 + 生命周期） [AnythingLLM workspace / MaxKB]
- 全表带 `kb_id`（documents/chunks/conversations/messages；default=1）。`chunks` 亦带 `document_id`。
- 文档状态机：`uploading → parsing → embedding → ready | failed(retryable) | disabled`；每文档进度与日志可见，失败可重试。
- 库级可配（先落表、UI 后置）：检索 top_k / rerank 开关 / 相似度阈值 / embedding 模型（换模型→重嵌警告）。

### C. 文档接入与解析 [RAGFlow 0.21 / MaxKB]
- **解析器/分块器可插拔契约**（P0 就按接口写，别写死）：
  ```
  Parser(ext) -> list[ParsedDoc{text, meta}]   # Unstructured / 代码(tree-sitter) / MD / TXT
  Splitter(ParsedDoc) -> list[Chunk{text, meta, seq}]
  Indexer(Chunk) -> Qdrant point + SQLite chunk 行
  ```
  Phase1 Task 6 的 loader 全部收敛到这个契约下；tree-sitter 要么真正用于代码切分，要么从依赖删掉（二选一，别留死代码）。
- 上传校验：类型白名单 + 大小上限（如 100MB）+ 文件名清洗（防 path traversal）。
- **入库前分段预览 + 人工校正**：前端"上传 → 看分段预览（可编辑/删段）→ 确认入库"。[MaxKB] 作为 P0 内嵌于知识库视图（最小版：预览只读列表，编辑删段放 P1，但交互路径先通）。
- P1：文档级解析/分块人工介入（hover 预览、加关键词、禁用整档）、扫描件 OCR 回退、库导出/导入 zip。

### D. 检索与引用可信度 [kotaemon / RAGFlow / FastGPT]
- 检索链路（后端统一，P0 内实现）：
  ```
  问题(可选 LLM 指代消除，P1) → 稠密(BGE-M3) + 全文/BM25(代码文档刚需，P0 起) 
  → 融合 → Rerank(BGE-Reranker-v2-m3, API 或本地按需) → 阈值过滤 → 按 tokens 裁引用上限
  ```
- **参数单一来源**：`kb_id` 级检索参数存 SQLite `user_config`/kb 表；对话检索与"命中测试"端点读同一份 → 测试面板所见即对话所得。[RAGFlow 教训]
- API：`POST /api/knowledge/{kb_id}/hit-test`（8/2 roadmap 已有）返回召回明细：每段 `{chunk, doc, score_breakdown{vector, bm25, rerank}, pass_threshold}`。
- 引用数据结构（对齐 roadmap §4 的 sources 标准化）：
  ```json
  {"sources": [{"n":1, "kb_id":1, "document_id":3, "chunk_id":57, "file":"...", "page":null,
                "score":0.82, "text":"...", "url":null}]}
  ```
- 前端：答案 `[n]` 可点击 → 抽屉/浮窗显示 chunk 原文片段 + 分数 + 文件/页码；置信度条；低置信整体提示。[kotaemon/FastGPT]
- P1：证据多分数面板、原文高亮定位（本地文件预览）、用户标注修正引用。

### E. 对话体验 [Open WebUI / AnythingLLM]
- SSE 流式（Phase1 Task 7 已定）+ 前端"停止生成"（abort）。
- 会话管理：列表/标题自动生成（Task model，P1）/删除/历史加载。
- 消息操作：P0=重发；P1=编辑/分支。
- **文件/库范围显式选择**：会话侧栏勾选"全部 / 指定 kb"（P0 最小：按 kb 选；P1：到文件级）。[kotaemon]
- Agent 思考/工具调用折叠展示（Phase2 Agent 落地时随附）。[AnythingLLM]

### F. Provider 与成本 [AnythingLLM / Open WebUI]
- LLM Gateway（Phase1 Task 3）扩展出**配置 UI 可写回**的 provider 表：`providers{name,type(openai-compatible|anthropic|deepseek),base_url?,api_key*,enabled}`；chat 与 embedding/rerank **分开配置**。
- 首次运行向导（P1 完整版；P0 最小版 = 检测 `.env`/config 为空 → 页面引导填 Key）。
- 用量/成本：`usage_records` 落库（Task 3 已定）+ 前端"消费概览"卡片（P1 完善，P0 留接口与表）。
- 模型名以配置为准（**不硬编码 `claude-opus-4-8` 等**）——曾有模型不存在/429 教训。

### G. Agent 与工具安全（Phase2 对应，规则先定） [MaxKB 教训 / khoj]
- 工具执行默认"用户确认"；任意代码执行**默认不做**；若 P2 做，先做威胁建模再谈 gVisor 级沙箱。
- 跨会话记忆与定时任务（P2，参照 khoj Automations / AnythingLLM Scheduled Jobs 理念自行实现）。

### H. 分发与工程 [Open WebUI / AnythingLLM / kotaemon]
- `setup.bat`（装 venv/依赖/生成 .env）/ `start.bat`（起 uvicorn，自动开浏览器）。
- 单端口：FastAPI `StaticFiles` 托管 `frontend/dist`（P1 发布时启用；开发期仍分离）。
- 首启引导：检测未配置 → 打开设置页（P1 完善）。
- **i18n 骨架 P0 就位**：前端抽 `zh`/`en` 两个 locale，默认中文（趁早成本极低）。[AnythingLLM/Open WebUI]
- 遥测：默认无；如加，遵守匿名+可关+透明清单。
- 测试：延续 Phase1 的 TDD（每 Task 写失败测试→实现→提交）。

---

## 4. 修订版 P0 任务清单（可勾选，含验收）

> 执行方式二选一（延续 7/22 未决问题）：**A. 本会话逐 Task 派发实现 + 审查** / **B. 生成新计划用 executing-plans 批量跑**。
> 建议顺序执行、每步提交 git。映射 Phase1 8 Tasks，差异处加 ★。

- [ ] **P0-0 基线**：提交 `docs/`、`.agents/`、`skills-lock.json`；把 `.superpowers/brainstorm/` 4 份原型复制到 `docs/designs/` 留存并入库；更新 README 状态。（★ 新增）
- [ ] **P0-1 脚手架**：目录 + `requirements.txt` + `core/config.py`（配置全部可被 SQLite 覆盖）+ `run.py`。（= Task 1）
- [ ] **P0-2 Storage**：SQLite 建表（含 `kb_id`、`documents.status`、`chunks.document_id`、`jobs`、`user_config`、`usage_records`）+ Repository（Conversation/Document/Chunk/Config）。★ 相对 Task 2 加 kb_id/jobs/config。
- [ ] **P0-3 LLM Gateway**：provider 路由/流式/降级/计费 + provider 表读写 + **模型名不硬编码**。（= Task 3 + provider 数据化）
- [ ] **P0-4 Embedding + Qdrant**：BGE-M3 本地 + AsyncQdrantClient + **稠密 + 稀疏(BM25) 混合存储**。★ 相对 Task 4 补全文/稀疏通道（代码/编号检索刚需）。
- [ ] **P0-5 RAG Engine**：检索(混合+Rerank+阈值)→上下文→流式生成；`hit-test` 返回分数构成。★ 相对 Task 5 落地真实混合+阈值+tokens 裁引用。
- [ ] **P0-6 文档管线**：Parser/Splitter/Indexer 契约（Unstructured + MD/TXT + tree-sitter 代码切分）+ jobs 表 worker（进度/失败重试）+ **分段预览 API**。（= Task 6 重构版）
- [ ] **P0-7 API Gateway**：health / chat SSE / knowledge（上传+状态+列表）/ hit-test / config 路由 + deps 单例 + lifespan。（= Task 7 + hit-test/config）
- [ ] **P0-8 端到端验证**：上传 → 状态流转 → 提问 → 流式回答带 sources → 命中测试一致。（= Task 8）
- [ ] **P0-9 前端骨架**：React+Vite+Tailwind+Zustand；**LiquidRAG 风格 token 层**（从 liquidrag-style-v1.html 抽取：黑曜石色板/玻璃气泡/圆角/输入栏样式为 CSS 变量）。（★ 前端正式起步）
- [ ] **P0-10 前端四视图（mock 先行）**：对话（流式+sources 抽屉+停止）、知识库（上传+分段预览确认+状态列表）、设置（Key/模型/参数）、消费概览占位。
- [ ] **P0-11 前端接入真实 API + i18n 骨架**（zh/en，默认 zh）。（★）
- [ ] **P0-12 分发**：`setup.bat`/`start.bat`；README 双语更新与"备份=拷贝 data/"说明。

**P0 验收**：全新用户 10 分钟内：clone → setup.bat → start.bat → 设置页填 Key → 上传一个 PDF+一个代码文件（看分段预览）→ 提问 → 流式回答，`[n]` 可点开来源与分数；切 DeepSeek 可降级；命中测试与对话参数一致；`data/` 拷贝即迁移。

**明确不进 P0**（P1/P2）：OCR 回退、命中→改分块、证据多分数面板、原文高亮预览、库 zip 导出、编辑/分支消息、文件级检索范围、多模型对比、MCP、记忆与定时、任意代码执行。

---

## 5. 许可合规自查（每次动手前过一遍）

- 只从以下借鉴**代码级**：AnythingLLM(MIT)、kotaemon(Apache-2.0)、RAGFlow(Apache-2.0，注意其内置模型/OCR 组件另有许可)。
- MaxKB(GPL)/FastGPT(自定义，含外观专利)/Open WebUI(品牌条款)/Khoj(AGPL)：**只看行为与文档，零代码、不复刻界面视觉**。
- 本项目若开源，建议预置宽松许可（如 MIT/Apache-2.0）并保留各借鉴项目的版权/NOTICE（如确有代码级参照）。
- 全程可向 Claude/编码 agent 声明："不抄 MaxKB/FastGPT/Open WebUI/Khoj 的任何代码与视觉；AnythingLLM/kotaemon/RAGFlow 仅理念级借鉴，如引入代码须加注释来源。"

---

## 6. 决策记录与待办

**已确认（2026-09-07）**
1. ✅ roadmap 决策 **A：按规划自研推进**；本规格为执行蓝图。
2. ✅ 修订 P0 作为执行蓝图。
3. ✅ **执行方式（2026-09-07 定）**：先产出完整执行计划供用户审阅——已产出
   `2026-09-07-p0-execution-backend.md`（P0-1~P0-8）与 `2026-09-07-p0-execution-frontend.md`（P0-9~P0-12）；
   用户确认后按计划逐 Task 执行（TDD + 每步提交）。
4. ⏳ 模型可用性核实：当前可用 Claude/DeepSeek 模型 ID 与配额（历史：`claude-opus-4-8` 为默认配置、`deepseek-v4-pro[1m]` 曾报不存在、遇过 org 429）。
5. ✅ 唯一工作副本 = `D:\RAG个人AI助手`（历史 `D:\rag` 为其旧名，实施时以本目录为准，计划内绝对路径需按此适配）。

**P0-0 基线进展（2026-09-07）**
- ✅ 前端 4 版原型从 `.superpowers/brainstorm/` 复制至 `docs/designs/` 并加索引（定稿 = `liquidrag-style-v1.html`）。
- ✅ README 更新为"路线确认 + 目标结构 + 文档索引"。
- ✅ git 基线提交：`docs/`（plans/research/designs）+ `README.md`。
- ℹ️ `.agents/skills`（~10MB 第三方技能副本）、`.claude/skills`（junction）、`skills-lock.json` **不入库**：第三方内容 + 许可混杂 + 仓库膨胀；如需版本化另行处理。
