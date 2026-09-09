# 皮肤映射（最终版）：仿 DeepSeek Harness 桌面风格 → Tailwind/组件（2026-09-09）

> 用途：把 `docs/designs/variants/variant-e-dsh-style.html`（变体 E，**用户已定稿**）落地到现有
> `frontend/`（当前是玻璃风 token）。只换皮肤与若干新增，结构/组件划分不动。
> 旧版 `skin-neon-token-map.md`（样板 D 霓虹）**作废**，以本文为准。
> 关联：`spec-addendum-01-sidebar-tooltips-and-customization.md`（tooltip + 背景/头像）一并实现。

## 1. 色板（tailwind.config.js 替换/新增）

| Token | 值 | 用途 |
|---|---|---|
| `bg-base` | `#0f1115` | 页面底层 |
| `bg-surface` | `#15171c` | 消息/面板/输入 |
| `bg-surface2` | `#1b1e25` | 嵌套/选中底 |
| `hover` | `rgba(255,255,255,.05)` | hover |
| `line` | `rgba(255,255,255,.08)` | 1px 细边框 |
| `text-p/s/t` | `#f9fafb` / `#a2a9b4` / `#6b7380` | 三级文字 |
| `accent` | `#99c8ff` | 链接/选中/发送/品牌点 |
| `accent-strong` | `#7aa2ff` | 按压/hover 加深 |
| `danger/ok/warn` | `#f28b82` / `#7dd3a8` / `#eab676` | 状态徽章 |
| `code-bg` | `#0b0d12` | 代码块 |
| 圆角 | 面板/输入 10px、码块 8px、头像 8px | — |
| 阴影 | 低；仅 focus 用 `0 0 0 2px rgba(153,200,255,.12)` | — |

原则：**去霓虹化**——无辉光/渐变描边/动画边框；点缀色克制（冷蓝），错误红仅用于停止/失败。

## 2. 全局/结构

- 页面：`#0f1115` 纯底（无光斑），可选自定义背景图时叠加 55% 暗化保证对比（见增补 §2）
- 布局骨架保持现有：窄栏/面板结构不必推翻；若前端现为"中央大玻璃面板"，可简化为整页分区（顶栏 + 左窄栏 + 主区），以 E 样板为视觉基准
- 顶栏：品牌点(accent 发光点)+标题、分段标签(胶囊tab)、右侧模型 chip、缓存 chip

## 3. 组件逐项

| 组件 | 改动 |
|---|---|
| 顶栏/TopBar | 改 E 顶栏样式；分段标签组 `#15171c` 底 + 选中 `#1b1e25`；model chip 用 `.chip` 细边样式 |
| Sidebar | 保持功能；配色换 E（`.item` hover/选中 冷蓝 8% 底）；**tooltip** 按增补 01 实现（玻璃深底+细边，hover/focus 显示，容器 relative+z 防遮挡） |
| MessageBubble | AI：`surface` 底 + 细边（无渐变）；用户：冷蓝 7% 底 + `rgba(153,200,255,.22)` 边；行内引用 = **链接色文字**（非发光药丸），hover 下划线，点击开抽屉 |
| 代码块 | 组件内 `<div class="code"><div class=hd>file · page</div><pre>…`：深色 `#0b0d12` + 文件头条 |
| SourceDrawer | 配色同 E：surface 底、细边、圆角 10px；分数条改细进度条（红→黄→绿），标题/编号用 accent |
| LiquidInput | E 输入区：`surface` 底 + 细边 + focus 冷蓝细圈；发送钮 accent 底深字（running 时变 danger 的 stop 态） |
| 状态徽章/模型chip/Agent空态 | 换 E 状态色（ok/warn/danger/accent）与 chip 样式 |

## 4. 新增（增补 01，一并做）

1. 侧栏 tooltip（见上）
2. 背景：设置→界面 提供预设（默认 DSH 深底 / 纯黑 / 浅灰可选）+ 「自定义图片」上传 → 存后端（/api/profile 契约见增补 01 §2.3）
3. 头像：用户/AI 各一上传位，预览 + 应用到消息行头像；无图时回退字母徽章
4. 后端就绪前：前端可用 mock/默认值联调；`/api/profile` 由后端侧实现后接线（url 由 GET /api/profile 提供）

## 5. 验证

`npm run build` 通过；对照 variant-e 视觉；tooltip 不被遮挡；背景图上传后全局即时生效、刷新不丢（数据在 data/）；头像在气泡显示正确。
