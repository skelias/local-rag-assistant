# RAG 助手前端视觉规格 —— Glassmorphism 面板风格（2026-09-09）

> 参考图：智能家居控制面板（玻璃拟态、大圆角、层级模块化、冷灰基调）
> 原则：借鉴设计语言，不照抄布局；为 RAG 对话/知识库/设置重新组织
> 约束：全篇不使用 emoji，以文字标签、SVG 图标、色块状态代替

---

## 1. 风格分析（从参考图提取）

| 元素 | 特征 |
|---|---|
| **背景** | 模糊的环境底图 / 或深色渐变底，主面板"浮"在上面 |
| **主面板** | 超大圆角（~24-32px），半透明深灰（alpha 0.6-0.75），backdrop-blur（12-24px） |
| **导航** | 左侧垂直细条，圆角胶囊形图标按钮，当前项有实心背景高亮 |
| **模块卡片** | 内部功能分区，各自为独立圆角卡片，层次分明 |
| **色彩** | 整体冷灰/石板色；点缀色极克制（仅用于状态、滑块、选中） |
| **字体** | 白色主标题 / 浅灰副文本，字号对比大，信息密度适中 |
| **阴影** | 柔和漫射，不尖锐，强化"悬浮玻璃"感 |
| **交互** | 按钮/卡片 hover 时轻微亮度提升 + 边框发光 |

---

## 2. 适配 RAG 助手的布局方案

### 2.1 整体框架

```
+----------------------------------------------------------+
| [全屏背景：深色渐变 或 抽象模糊纹理]                      |
|                                                          |
|  +--+  +---------------------------------------------+   |
|  |N |  | 顶部栏：知识库选择 / 当前对话标题 / 用户菜单  |   |
|  |A |  +---------------------------------------------+   |
|  |V |  |                                           |   |
|  |  |  |              主内容区                      |   |
|  |  |  |    （对话 / 知识库 / Agent / 设置）        |   |
|  |  |  |                                           |   |
|  +--+  +---------------------------------------------+   |
|                                                          |
+----------------------------------------------------------+
```

- **左侧导航栏**：窄条（64px），浮于主面板左侧，与主面板同风格但略深一级
- **主面板**：占据画面中心，超大圆角（28px），所有内容在其内部
- **顶部栏**：主面板内顶部，标签式切换（对应参考图的 Room 切换）

### 2.2 四视图映射

| 视图 | 布局映射 |
|---|---|
| **对话** | 左侧消息流（用户右对齐玻璃气泡 / AI 左对齐玻璃气泡）+ 底部固定输入栏（Liquid Edge 药丸形）+ 右侧可滑出"来源抽屉" |
| **知识库** | 网格/列表卡片（每文档一张玻璃卡片，含缩略信息+状态徽章）+ 顶部上传区 |
| **Agent** | 空态占位页，一张居中大卡片说明"即将上线" |
| **设置** | 分组卡片列表（LLM / 检索 / 界面），每设置项一行，右侧控制项 |

---

## 3. 设计 Token 系统（CSS 变量 + Tailwind）

### 3.1 颜色

```css
:root {
  /* 背景层 */
  --bg-base: #0f0f12;              /* 最底层 */
  --bg-panel: rgba(28, 28, 32, 0.72);  /* 主面板玻璃底 */
  --bg-nav: rgba(22, 22, 26, 0.85);    /* 左侧导航 */
  --bg-card: rgba(255, 255, 255, 0.06); /* 内部卡片（更透） */
  --bg-card-hover: rgba(255, 255, 255, 0.10);

  /* 文字 */
  --text-primary: #f0f0f5;
  --text-secondary: #a0a0b0;
  --text-tertiary: #6e6e7a;
  --text-inverse: #1a1a1f;          /* 用于亮色按钮上的字 */

  /* 强调色（克制使用） */
  --accent-cyan: #4ecdc4;           /* 用户气泡/发送按钮/选中态 */
  --accent-violet: #a78bfa;         /* AI 气泡边框 glow / 引用标签 */
  --accent-warm: #f4a261;           /* 状态徽章：待确认 */
  --accent-success: #2ecc71;        /* 状态徽章：已就绪 */
  --accent-danger: #e74c3c;         /* 状态徽章：失败 / 删除 */

  /* 边框与光影 */
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-glow: rgba(78, 205, 196, 0.35);
  --shadow-panel: 0 24px 60px rgba(0, 0, 0, 0.45);
  --shadow-card: 0 4px 20px rgba(0, 0, 0, 0.25);
}
```

### 3.2 圆角

| 元素 | 圆角 |
|---|---|
| 主面板 | `28px` |
| 左侧导航条 | `24px`（整体）/ 按钮 `16px` 胶囊 |
| 内部卡片 | `20px` |
| 消息气泡 | 用户 `20px 20px 4px 20px` / AI `4px 20px 20px 20px` |
| 输入栏 | `24px` 药丸形 |
| 按钮 | `12px` |
| 徽章/标签 | `8px` |

### 3.3 玻璃效果标准

```css
.glass-panel {
  background: var(--bg-panel);
  backdrop-filter: blur(20px) saturate(1.2);
  -webkit-backdrop-filter: blur(20px) saturate(1.2);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-panel);
  border-radius: 28px;
}

.glass-card {
  background: var(--bg-card);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-card);
  border-radius: 20px;
  transition: background 0.2s, box-shadow 0.2s;
}

.glass-card:hover {
  background: var(--bg-card-hover);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35), 0 0 0 1px var(--border-glow);
}
```

---

## 4. 组件规格

### 4.1 左侧导航（Sidebar）

- 宽度：64px，垂直居中偏左
- 背景：`var(--bg-nav)`，圆角 24px
- 图标：24px SVG（对话、书本、机器人、齿轮），默认 `var(--text-tertiary)`
- 当前项：
  - 图标色：`var(--accent-cyan)`
  - 背景：实心椭圆 `rgba(78, 205, 196, 0.15)`
  - 左侧 3px 竖条指示器（`var(--accent-cyan)`）
- Hover：背景变为 `rgba(255,255,255,0.06)`

### 4.2 顶部标签栏（Top Tabs）

- 位置：主面板内顶部，高 56px
- 样式：模仿参考图的 Room 切换
- 标签："全部知识库"、"代码库"、"笔记库"（多库预留）
- 当前项：胶囊形背景 `rgba(255,255,255,0.1)` + 文字白
- 未选项：文字 `var(--text-secondary)`，无背景

### 4.3 消息气泡（Chat Bubbles）

| 属性 | 用户 | AI |
|---|---|---|
| 背景 | `linear-gradient(135deg, rgba(78,205,196,0.12), rgba(78,205,196,0.04))` | `var(--bg-card)` |
| 边框 | 无 | `1px solid var(--border-subtle)` |
| 圆角 | `20px 20px 4px 20px` | `4px 20px 20px 20px` |
| 对齐 | 右侧 | 左侧 |
| 最大宽度 | 78% | 78% |

引用标签（`[1]`、`[2]`）：
- 样式：`inline-flex`，背景 `rgba(167,139,250,0.12)`，文字 `var(--accent-violet)`，圆角 6px，字号 12px
- Hover：背景加深，可点击打开来源抽屉

### 4.4 输入栏（Input Bar）

- 位置：主面板底部固定
- 形状：药丸形（圆角 24px）
- 背景：`var(--bg-card)`，高度 56px
- Focus 状态：
  - 外框：1px `var(--border-glow)`
  - 微弱内发光：`box-shadow: inset 0 0 12px rgba(78,205,196,0.08)`
- 发送按钮：右侧圆形，直径 40px，背景 `var(--accent-cyan)`，图标白色
- 停止按钮：同位置，背景 `var(--accent-danger)`

### 4.5 来源抽屉（Source Drawer）

- 触发：点击引用标签 或 侧边按钮
- 位置：主面板右侧滑出（宽度 360px）
- 背景：与主面板同级的玻璃，但略深
- 内容：每条来源一张小卡片
  - 顶部：编号圆圈 + 文件名 + 页码
  - 中部：分数条（横向进度条，颜色按分数渐变：低=红/中=黄/高=青）
  - 底部：文本片段（最多 4 行，渐变淡出）

### 4.6 知识库文档卡片（Doc Card）

- 布局：网格，每行 2-3 张
- 单卡：
  - 顶部：文件类型图标（24px SVG）+ 文件名
  - 中部：分块数、文件大小
  - 底部：状态徽章
- 状态徽章颜色：
  - parsed（待确认）：`var(--accent-warm)` 背景 + 文字
  - ready（已就绪）：`var(--accent-success)`
  - failed（失败）：`var(--accent-danger)`
  - indexing（索引中）：`var(--accent-cyan)` 脉动动画

### 4.7 状态与图标对照（无 emoji）

| 含义 | 实现方式 |
|---|---|
| 成功/就绪 | 绿色圆点（8px）或 "已就绪" 文字徽章 |
| 警告/待确认 | 橙色圆点或 "待确认" 文字徽章 |
| 错误/失败 | 红色圆点或 "失败" 文字徽章 |
| 加载中 | 青色旋转圆环（CSS animation）或 "索引中..." |
| 发送 | 纸飞机 SVG 图标 |
| 停止 | 方块 SVG 图标 |
| 上传 | 向上箭头 SVG 图标 |
| 删除 | 垃圾桶 SVG 图标 |
| 设置/齿轮 | 齿轮 SVG 图标 |
| 展开/收起 | Chevron 箭头 SVG |
| 来源/引用 | 书签或引号 SVG 图标 |

---

## 5. 与 LiquidRAG 原稿的关键差异

| 维度 | LiquidRAG（原稿） | Glassmorphism（本稿） |
|---|---|---|
| 背景 | 黑曜石纯色 + 焦散光斑动画 | 可配模糊底图或深渐变，主面板"浮"起 |
| 面板形式 | 全屏沉浸，无边框 | 中央大圆角玻璃面板，有明确边界 |
| 导航 | 顶部或左侧展开式 | 左侧极简垂直图标条 |
| 圆角 |  already 大圆角 | 更大、更统一（28px 主面板 / 20px 卡片） |
| 色彩点缀 | Aurora 渐变（cyan/violet）大量用于气泡 | 点缀色极度克制，仅用于状态和交互反馈 |
| 信息密度 | 偏宽松（ Liquid 感） | 中等密度，模块化卡片排布 |
| 动画重点 | 背景焦散漂移、边框旋转 | 卡片 hover 发光、抽屉滑入、按钮反馈 |

---

## 6. Tailwind 配置草案

```js
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'bg-base': '#0f0f12',
        'bg-panel': 'rgba(28,28,32,0.72)',
        'bg-nav': 'rgba(22,22,26,0.85)',
        'bg-card': 'rgba(255,255,255,0.06)',
        'text-p': '#f0f0f5',
        'text-s': '#a0a0b0',
        'text-t': '#6e6e7a',
        'accent-cyan': '#4ecdc4',
        'accent-violet': '#a78bfa',
        'accent-warm': '#f4a261',
        'accent-success': '#2ecc71',
        'accent-danger': '#e74c3c',
        'border-subtle': 'rgba(255,255,255,0.08)',
        'border-glow': 'rgba(78,205,196,0.35)',
      },
      borderRadius: {
        'panel': '28px',
        'card': '20px',
        'bubble-user': '20px 20px 4px 20px',
        'bubble-ai': '4px 20px 20px 20px',
        'pill': '24px',
      },
      boxShadow: {
        'panel': '0 24px 60px rgba(0,0,0,0.45)',
        'card': '0 4px 20px rgba(0,0,0,0.25)',
        'glow-cyan': '0 0 0 1px rgba(78,205,196,0.35)',
      },
      backdropBlur: {
        'panel': '20px',
        'card': '12px',
      },
    },
  },
}
```

---

## 7. 文件输出清单（P0-9 ~ P0-12 编码时参照）

- `docs/designs/liquidrag-style-v1.html` —— 原稿（历史参考）
- `docs/designs/rag-glassmorphism-spec.md` —— 本文档（执行依据）
- `frontend/tailwind.config.js` —— 按第 6 节配置
- `frontend/src/index.css` —— CSS 变量 + glass 工具类
- `frontend/src/components/Sidebar.jsx` —— 左侧垂直导航
- `frontend/src/components/TopBar.jsx` —— 顶部标签/标题栏
- `frontend/src/components/DocCard.jsx` —— 知识库文档卡片
- `frontend/src/components/MessageBubble.jsx` —— 对话气泡
- `frontend/src/components/SourceDrawer.jsx` —— 来源抽屉
- `frontend/src/components/LiquidInput.jsx` —— 底部输入栏（保留药丸形，风格适配）

---

## 8. 验收标准（视觉层）

- [ ] 整体无 emoji，所有状态用颜色徽章、SVG 图标或文字表达
- [ ] 主面板呈现"悬浮玻璃"质感（blur + 半透明 + 柔和阴影）
- [ ] 左侧导航与主面板层级分明，当前项有明确指示
- [ ] 消息气泡区分用户/AI，引用标签可点击
- [ ] 输入栏 focus 时有青色发光边框
- [ ] 知识库卡片网格排列，状态徽章颜色正确
- [ ] 来源抽屉从右侧滑入，分数条直观展示置信度
- [ ] 全站不使用任何 emoji 字符
