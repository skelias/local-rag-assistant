# 前端设计增补 01：侧边栏命名提示 + 个性化背景/头像（2026-09-09）

> 给 Claude Code 实现的规格补充。基于「玻璃面板 × 霓虹」样板 D（docs/designs/variants/variant-d-panel-neon.html）。
> 原则延续：无 emoji、状态用色块/文字/SVG；只增需求、不改既有结构。

## 1. 侧边栏：悬停显示功能名（低风险，纯前端）

- 触发：鼠标 hover 图标 / 键盘 focus 该图标
- 表现：图标右侧浮出药丸标签（白字、玻璃底+霓虹细边+微光），带小箭头指向图标；hover 离开即消失
- 位置：距图标 12px；同一时刻只显示一个
- 可访问性：标签用 aria-label/aria-describedby 兜底（不依赖 hover）
- 命名：对话 / 知识库 / Agent / 设置（与 i18n t() 一致，en: Chat / Knowledge / Agent / Settings）
- 参考实现：样板 D `.ic .tip` 的 CSS

## 2. 个性化：背景与头像（用户可上传自己的图片）

### 2.1 背景
- 提供 ≥4 个预设：玻璃×霓虹（默认）、纯净黑、毛玻璃浅、极光
- 「自定义背景」：上传一张图片 → 作为全屏背景（背景图 + 原样覆盖的暗色/霓虹渐变 overlay 保证文字可读）
- 透明/尺寸：图片仅装饰；overlay 恒定，保证对比度
- 入口：设置 → 界面（与语言放一组）

### 2.2 头像
- 两处可自定义：用户头像、AI 助手头像
- 默认：字母徽章（现样式：你=渐变 R 徽章/我=玻璃徽章），用户上传后替换
- 出现位置：对话消息行首（现有 .ava）；用户头像额外可用于顶栏/菜单（可选）
- 约束：上传前做图片格式（png/jpg/webp）与大小（≤2MB）校验；显示为圆形/圆角裁剪

### 2.3 存储方案（已定：B · 后端 data/，2026-09-09 用户确认）
后端新增最小能力（约半节课量）：

- **接口契约**
  - `GET /api/profile` → `{background, avatar_user, avatar_ai}`（null 或 URL 路径）
  - `POST /api/profile/upload`（multipart：`kind ∈ {background, avatar_user, avatar_ai}` + `file`）
    → 校验（png/jpg/webp，≤2MB）→ 存盘 → 返回 `{url}`（相对路径）
  - `DELETE /api/profile/upload?kind=…`（可选，先不做也 OK）
- **文件位置**：`data/backgrounds/<uuid>.<ext>`、`data/avatars/<uuid>.<ext>`
- **元信息**：写 `user_config` 键 `ui.background` / `ui.avatar_user` / `ui.avatar_ai`（值=URL 路径）
- **静态托管**：FastAPI 挂载 `/media` → `data/media`（或分两个目录各自挂载），与现有 single-port 托管并存；URL 形如 `/media/backgrounds/x.png`
- **默认回退**：无配置时背景=预设默认（霓虹渐变）、头像=字母徽章
- 前端 `SettingsView` 新增「界面」分组：背景预设单选 + 自定义上传预览；用户/AI 头像两个上传位；上传后即时刷新全局背景与气泡头像

### 2.4 前端改动范围（对应组件）
- `SettingsView.jsx`：新增「界面」分组（背景预设+上传、双头像上传预览）
- 全局应用层：`App.jsx` 读取 ui.* 配置 → body 背景与 .ava 组件 props
- `MessageBubble.jsx / TopBar`：头像数据源改为配置；`i18n` 补词条

## 3. 涉及既有未定项
- 设置页「模型/Key 可改」需求另需后端动态配置改造（已接受，任务另列），本次不混入。
