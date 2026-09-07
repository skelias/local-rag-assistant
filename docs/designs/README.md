# 前端设计资产（Frontend Design Assets）

从 `.superpowers/brainstorm/`（临时目录，已被 `.gitignore` 忽略）留存至此，纳入版本控制，避免设计定稿丢失。

## 四版迭代与定稿

| 文件 | 时间 | 说明 |
|---|---|---|
| `layout-v1.html` | 2026-07-22 00:56 | v1：基础深蓝紫黑单视图（用户："不太好"） |
| `layout-v2.html` | 2026-07-22 01:37 | v2：OKLCH 夜间调色板 + 对话/知识库/Agent/设置四视图（用户："太素了"） |
| `glassmorphism-v1.html` | 2026-07-22 01:43 | v3：毛玻璃发光夜间版（过渡） |
| **`liquidrag-style-v1.html`** | 2026-07-22 02:04 | **✅ 定稿**：LiquidRAG 风格"黑暗泻湖"（仿 [lorinefeng/LiquidRAG](https://github.com/lorinefeng/LiquidRAG) 前端呈现效果，不取其实现） |

## 定稿风格要点（实现前端时的抽取依据）

- 背景：黑曜石 `#0A0A0F` + 缓慢漂移的 cyan/violet 焦散光斑
- 3 层液态玻璃气泡栈：亮度层 → 色彩模糊层（极光渐变）→ 噪点纹理层
- 用户气泡：aurora 渐变（cyan 10% → violet 6%），圆角 `24px 24px 6px 24px`
- AI 气泡：冷板岩渐变，圆角 `6px 24px 24px 24px`
- Liquid Edge 输入栏：聚焦时 conic-gradient 边框旋转；药丸形渐变发光发送按钮
- 来源抽屉：右侧滑入毛玻璃面板 + 置信度水填充进度条
- 滚动条：2px 玻璃轨道

> 正式前端（P0-9 起）将把以上提炼为 Tailwind/CSS 变量 token，见 `docs/plans/2026-09-07-mature-product-spec-and-p0.md`。
