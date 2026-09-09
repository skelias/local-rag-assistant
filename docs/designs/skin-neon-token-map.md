# 皮肤翻新映射：玻璃面板 × 霓虹（样板 D → Tailwind/组件）2026-09-09

> 用途：把 `docs/designs/variants/variant-d-panel-neon.html`（样板 D）的视觉落地到现有
> `frontend/`（玻璃风）。结构/组件划分不动，只换"token 与类样式"。
> 遵守：无 emoji、状态用色块/文字/SVG、可访问性不降级。
> 样板 D 是 CSS 真源：拿不准的细节直接读它的 `<style>`。

## 1. 色板映射（tailwind.config.js）

| 现在（玻璃风） | 改为（霓虹） | 用途 |
|---|---|---|
| `bg-base #0f0f12` | `#07040d` | 页面底层 |
| `bg-panel rgba(28,28,32,.72)` | `rgba(16,11,28,.62)` | 中央面板玻璃 |
| `bg-nav rgba(22,22,26,.88)` | `rgba(10,6,20,.78)` | 左侧导航 |
| `bg-card rgba(255,255,255,.055)` | 保持（深底下够用） | 卡片 |
| `accent-cyan #4ecdc4` | `#22d3ee` | 主霓虹青（交互/发送/用户主色） |
| `accent-violet #a78bfa` | `#a855f7` | 霓虹紫（描边/AI 边/引用/选中） |
| 新增 `accent-pink` | `#f472b6` | 点缀第三色（渐变尾端） |
| `border-sub rgba(255,255,255,.07)` | `rgba(168,85,247,.22)` | 霓虹描边 |
| `text-p/s/t` | 保持 `#efe9ff/#9489bd/…` | 文字 |
| 状态色 | 霓虹化：indexing `#22d3ee`、ready `#34d399`、parsed `#fbbf24`、failed `#fb7185` | 徽章 |

## 2. 全局 CSS 增量（frontend/src/index.css）

```css
@property --a { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
.conic-ring { border-radius: 999px; padding: 1.5px;
  background: conic-gradient(from var(--a), #22d3ee, #a855f7, #f472b6, #22d3ee);
  animation: spinRing 7s linear infinite; }
@keyframes spinRing { to { --a: 360deg } }
.neon-glow-violet { box-shadow: 0 0 18px -4px rgba(168,85,247,.8); }
.neon-glow-cyan  { box-shadow: 0 0 14px -3px rgba(34,211,238,.8); }
.panel-inset { box-shadow: inset 0 0 80px -60px rgba(168,85,247,.6); }
```

## 3. 组件改动清单（改 token/类，不改结构）

| 组件 | 改动 |
|---|---|
| `App.jsx` | 页面背景换为样板 D 的三层径向光斑 + `#07040d`（新增 `.bg-neon` 工具类或 CSS 类） |
| `Sidebar.jsx` | ① 图标项：选中态=渐变底(青紫 α)+霓虹描边+左下 3px 渐变指示条（`::before`，参考 .ic.on）；hover=紫描边淡底；② **tooltip**：见增补 01 —— 每项包 `<span class="tip">`（玻璃+紫边+微光），hover/focus 显示；命名走 i18n |
| 主面板容器（App/layout） | 面板圆角 28 不变；边框色用新 border；加 `.panel-inset` 内辉 |
| `TopBar.jsx` | 分隔线/选中标签改霓虹：`.tab.on` 渐变底+紫描边+微光；模型胶囊换 cyan 霓虹药丸（样板 .pill2） |
| `MessageBubble.jsx` | 用户气泡：渐变底(青→紫 α) + 紫霓虹描边 + 外发光（参考 .row.u .bub）；AI 气泡：透明玻璃 + `inset` 青色微光（.row.ai .bub）；头像框加霓虹描边 |
| `SourceDrawer.jsx` | 边框色、编号圆角块=青紫渐变底；分数条改三色渐变进度条（低红→中黄→高青）；hover 光 |
| `LiquidInput.jsx` | 输入栏改为"外圈 `.conic-ring` + 内层深色药丸"两层结构（参考 .liquid/.inner）；发送钮改圆形渐变+青色外发光 |
| 引用标签（组件内） | `.cite` 药丸：青字 + 青霓虹描边微光 |
| 文档卡片/状态徽章（KnowledgeView/DocCard） | 卡片边框色更新；徽章色用霓虹化状态色（同 §1 表格） |
| `AgentView.jsx` 空态卡 | 仅换边框/按钮色调，保持"即将上线"文案 |

## 4. 落地顺序建议（交给 Claude Code 或我这边后端课时并行）

1. tailwind token + index.css 增量（§1/§2）
2. Sidebar tooltip + 霓虹（增补 01 §1）
3. 逐组件套用（§3），随时对照样板 D 微调
4. 背景/头像（增补 01 §2，待 /api/profile 后端就绪后接线）
5. `npm run build` 验证 + 截图对比样板 D

> 强度控制：样板 D 中辉光为"示例强度"；若整体过浓，统一把各 `box-shadow` alpha 下调 30-50% 即可，无需动结构。
