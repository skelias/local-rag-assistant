# 本地 RAG 助手

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![Node](https://img.shields.io/badge/Node-18%2B-brightgreen)
![Tests](https://img.shields.io/badge/tests-49%20passed-success)

把技术文档和代码丢进本地知识库，然后直接问它。**答案带出处，资料不出本机。**

比如这种问题，它答得不错：

> "我们的鉴权逻辑到底写在哪个文件里？"
> "上次那套部署脚本，环境变量有哪几个？"
> "这个报错码在文档里怎么解释的？"

它会先去你的资料里找相关片段，再让大模型**只根据这些片段**回答，并标出 `[1]` `[2]` 是引用自哪个文件。找不到就直说"知识库中没有相关内容"，不瞎编。

---

## 为什么写这个

我的技术资料散在 Markdown、PDF 和代码注释里。用在线 AI 问问题，得先把内容复制过去，麻烦；有些内容也不适合往外发。

现成的方案试过几个，要么太重（一堆容器、一堆服务），要么改不动。所以自己写了一个：能看懂、能改、够用就行。

## 它能做什么

**问答**
- 上传 Markdown / TXT / 代码文件 → 先给你看切好的分块 → 你点确认，才进知识库
- 回答走 SSE 流式输出，一个字一个字出来，中途可以停
- 引用可点：打开右侧抽屉看是哪个文件、第几段、相关度多少

**多知识库**
- 顶栏三个库分开：默认库 / 代码库 / 笔记库
- 各自上传、各自检索，互相不串

**调试检索**
- 知识库页有"命中测试"：同一个问题看召回了什么、分数怎么构成（向量分 / BM25 分 / 融合分）
- 它和对话用的是**同一份检索参数** —— 你在测试面板调好，对话里就是那个效果

**换模型**
- 内置 Claude、DeepSeek、智谱 GLM、Kimi、OpenAI；也支持任何 OpenAI 兼容端点
- 全在**设置页**里填：API Key、Base URL、模型名。点"拉取模型列表"能自动问端点要清单，也可以直接手打
- 保存即生效，不用改 `.env`、不用重启

**外观**
- 深色界面、中英双语切换
- 背景可以换（预设或传自己的图），用户和 AI 的头像也能换成自己的图片

## 快速开始

需要 Python 3.12+ 和 Node 18+。

```bash
git clone https://github.com/yikui123/local-rag-assistant.git
cd local-rag-assistant

setup.bat     # 建后端虚拟环境 + 装前端依赖，并从示例生成 .env
start.bat     # 前端没构建过会自动构建，然后打开 http://127.0.0.1:8000
```

打开页面后，去 **设置 → 模型 / 密钥**：

1. 挑一个 Provider，把 **API Key** 填进去（留空就用 `.env` 里的）
2. 模型名可以直接手填，也可以点"拉取模型列表"选一个，点"添加"
3. 顶上把"主力模型"选上 → 保存

然后去知识库页传一份自己的文档，确认入库，就可以开始问了。

> 首次运行主要时间花在下依赖上，大概几分钟。前端开发模式也可以单独跑：`cd frontend && npm run dev`（会代理到 8000 端口）。

## 它是怎么跑起来的

```
上传文件 → 解析切块（md / txt / 代码）→ 你确认分块 → 向量化写入 Qdrant
                                                        ├─ 稠密向量（fastembed，中文友好）
                                                        └─ 稀疏 BM25（关键词、错误码精确命中）

提问 → 两路召回 → RRF 融合 → 按 token 预算挑片段 → 拼进提示词 → 模型流式回答 → 前端渲染可点的 [n] 引用
```

几个刻意的选择：

- **先预览再入库**：分块切得烂，你当场就能发现，不要让垃圾进向量库
- **两路召回而不是单路**：语义问题靠向量，`errno 10053` 这种精确词条靠 BM25
- **引用结构化**：`sources` 里带 file / page / score / chunk，前端才能做出"点开看原文片段"
- **用量只统计 token 和缓存命中率**，不折算成钱 —— 我更关心"这段提示词有没有被缓存复用"



## 已知的限制


- **Agent 页面是占位**，工具调用、多步推理还没实现（下一阶段的主要工作）
- **只认文本类文档**：PDF / DOCX 会明确报"解析器未安装"，扫描件 OCR 也没做
- **嵌入模型用的是轻量版**（fastembed bge-small-zh，512 维），不是 BGE-M3；换模型代码已留好接口，缺的是把大模型下下来
- **多知识库是固定三个槽位**（kb 1/2/3），还不能自己新建库
- **单用户本地使用**：没有登录、没有权限体系
- 会话列表管理、消息编辑重发这些体验细节还没做

## 接下来想做的

1. PDF / DOCX 解析（顺带 OCR，能处理扫描件）
2. 会话列表 + 消息编辑、重发、删除
3. BGE-M3 一键切换（下载好就能开）
4. Agent：工具调用、联网检索、长任务进度

## 常见问题

**API Key 存在哪里？**
填在设置页的会存本机 SQLite（`data/rag.db` 的 `user_config` 表）；留空则用 `.env` 里的。两种都不会进 git。

**它说"知识库中没有相关内容"怎么办？**
先去知识库页确认文档状态是"已就绪"，再用命中测试拿同一个问题试。召回不到就调低阈值、换 BM25 权重、或者补文档 —— 这是检索问题，不是模型问题。

**端口 8000 被占用了？**
改 `.env` 里的 `PORT`，或者改 `start.bat` 启动命令里的端口号。



## 技术栈

| | |
|---|---|
| 后端 | Python 3.12+ · FastAPI · aiosqlite · Qdrant（本地文件模式） |
| 检索 | fastembed（bge-small-zh 稠密 + BM25 稀疏）· RRF 融合 · 可选 Rerank |
| 模型 | Anthropic 原生 + 任意 OpenAI 兼容端点（DeepSeek / GLM / Kimi / GPT / 自建网关） |
| 前端 | React 18 · Vite · TailwindCSS · Zustand |

## 开发

```bash
# 后端测试（49 个）
cd backend && venv\Scripts\python -m pytest

# 前端构建 / 开发
cd frontend && npm run build
cd frontend && npm run dev

# 一些自用脚本
backend/scripts/real_e2e.py      # 真端到端：传文档 → 向量化 → 提问
backend/scripts/smoke_llm.py     # 模型连通性 + token/缓存命中
backend/scripts/list_models.py   # 问某个端点有哪些模型
```

目录大致是这样：

```
backend/app/core/       config · llm_gateway · embedding · vector_store
backend/app/services/   repositories · rag_engine · doc_pipeline
backend/app/api/        app · deps · routes/{chat,knowledge,config,profile,llm}
frontend/src/           components · views · api · hooks
docs/plans/             实施计划   docs/research/  对标调研
docs/designs/           设计规格与界面预览   docs/learning
```

## 致谢

设计阶段对标过几个开源项目（AnythingLLM、Open WebUI、RAGFlow、kotaemon、Khoj、MaxKB、FastGPT）。

## License

MIT
