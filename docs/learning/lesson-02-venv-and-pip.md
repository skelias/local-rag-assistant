# 第 2 课：虚拟环境 venv + pip + requirements.txt

## 为什么需要虚拟环境

Python 的库装在"全局"，A/B 项目要同一个库的不同版本就会打架，还可能搞坏系统里其它软件。
**venv = 给每个项目开一间独立的"迷你 Python 房间"**：独立的 Python + 独立的库，互不干扰，删文件夹即卸载。

## 概念速记

| 词 | 是什么 | 比喻 |
|---|---|---|
| pip | Python 装库的工具（`pip install 库名`） | 应用商店 |
| venv | 项目的独立 Python 环境 | 独立小房间 |
| requirements.txt | 记录项目要哪些库的"清单文件" | 购物清单 |
| `pip install -r 文件` | 按清单一次装齐 | 照着清单采购 |

## 本次实际敲的命令（我示范用的完整路径写法）

```powershell
cd "D:\RAG个人AI助手"                       # 站到项目根
python -m venv backend\venv                # 在 backend 里创建 venv 房间
backend\venv\Scripts\python --version      # 用"房间里"的 python（注意路径里有 venv\Scripts）
backend\venv\Scripts\python -m pip install pytest   # 把 pytest 装进这间房间
backend\venv\Scripts\python -m pip list    # 看看房间里已装了哪些库
```

> Windows 下"激活房间"可用 `backend\venv\Scripts\Activate.ps1`（激活后直接敲 `python` 就是房间里的）；
> 不用激活也能用完整路径 `backend\venv\Scripts\python`，教学阶段推荐后者（更直白）。

## 为什么 pip list 里有那么多"陌生"库

装 pytest 时它自动带上了依赖：`colorama`(颜色)、`iniconfig`(配置文件)、`packaging`(版本号解析)、`pluggy`(插件机制)、`Pygments`(代码高亮) —— **库会自己装它需要的小工具**，这是正常现象，不用背。

## 本项目策略

- 计划文档里列的重型库（torch / FlagEmbedding 等，几个 GB）**先不装**，到 P0-4 那课再装；
- 教学每课只装当课需要的最小依赖。

---

## backend 目录导游（backend 里各文件夹分工）

```
backend\                    ← 后端程序的家
├── app\                    ← 程序代码本体（python 包）
│   ├── core\               ← 核心部件：配置 / AI 调用 / 向量库
│   ├── models\             ← 数据模型：定义数据"长什么样"
│   ├── services\           ← 业务逻辑：真正干活的模块
│   └── api\                ← 对外窗口：浏览器访问的入口（FastAPI 路由）
├── tests\                  ← 测试的家（pytest 质检员）
└── venv\                   ← 独立房间：python + 库（别手改里面）
```

## venv 三步走（从零配置）

```powershell
# 1) 创建（在哪个目录建，房间开在哪）
python -m venv D:\练习venv

# 2) 用房间里的 python 装库
D:\练习venv\Scripts\python -m pip install requests

# 3) 激活（可选；激活后命令行出现 (练习venv) 前缀，直接敲 python 即房间内）
D:\练习venv\Scripts\Activate.ps1
deactivate        # 退出房间
# 不激活也行：全程用完整路径 D:\练习venv\Scripts\python
```

## 重点提醒

- venv 文件夹**不进 git**（大 + 每台机器不同）；`.gitignore` 已写 `venv/`。
- 进 git 的是 `requirements.txt`（购物清单），别人 clone 后自建房间照单安装。
- venv 里面（Scripts / Lib\site-packages / pyvenv.cfg）**永远不要手动改**。

