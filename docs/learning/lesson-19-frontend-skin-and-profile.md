# 第 19 课：前端定稿（DSH 皮肤）+ 个性化（背景/头像）+ 后端 profile

## 皮肤演进与定稿

- 早期候选：A 明亮玻璃 / B 现代卡片 / C 霓虹夜航 / D 玻璃面板×霓虹
- 用户最终拍板：**E · 仿 DeepSeek Harness 桌面风格**（近黑蓝灰、克制冷蓝点缀、无霓虹）
- 配色来源：直接抓取运行中的 DSH Web GUI（127.0.0.1:3080）样式文件抽样
  - bg `#0f1115` / surface `#16181e` / text `#f9fafb·#a2a9b4` / accent `#99c8ff` / danger `#f28b82`
- 落地文件：`docs/designs/skin-map-dsh-final.md`（token/组件映射）+ `frontend/tailwind.config.js` + `index.css`

## 侧边栏 tooltip（hover/focus 显示功能名）

- 实现：`Sidebar.jsx` 每个图标按钮内加 `.nav-tip`（CSS：绝对定位到图标右侧、hover/focus 显隐）
- 关键坑：tooltip 溢出导航栏边界后，被后绘制的主面板盖住 → 修复：导航容器 `relative z-30`
- 无障碍：保留 `title`，焦点态同样显示（`:focus-visible`）

## 个性化：背景与头像（存后端 data/，方案 B）

### 后端（本会话实现）
- `routes/profile.py`：`GET /api/profile`（读 user_config）、`POST /api/profile/upload?kind=…`（校验类型/2MB → 存 `data/media/{backgrounds|avatars}` → 写 `user_config` 键 ui.* → 返回 URL）
- `app.py`：挂载 `/media` → `data/media`（StaticFiles）；`deps.get_media_dir`
- 测试：`tests/test_profile_api.py`（上传/读回/静态可访问/415 类型/400 kind）
- 冒烟脚本：`scripts/smoke_profile.py`

### 前端（本会话实现）
- `api/client.js`：`profile()` / `uploadProfile(kind,file)`
- `store.js`：`profile` + `setProfile`
- `App.jsx`：启动拉 profile；根据 `background`（preset:xxx 纯色 / URL 图）应用 body 背景
- `SettingsView.jsx`：界面组 = 3 个背景预设 + 自定义上传；用户/AI 头像上传与预览
- `MessageBubble.jsx` / `TopBar.jsx`：头像数据源改配置（图或字母徽章回退）
- `i18n.js`：补 background/头像/上传等词条（zh/en）

## 协作与自测

- 前端 P0-9~12 原由 Claude Code 提交；皮肤/个人化改由本会话负责（用户指示"全部由你来做"）
- 自测：后端 pytest 46 全绿；前端 npm build 通过；真实起服务：profile 上传 200 → `/media` 返回 image/png 200 → 读回一致

## 命令速记

```powershell
cd "D:\RAG个人AI助手\backend"; .\venv\Scripts\python -m pytest   # 46 passed
cd "D:\RAG个人AI助手\frontend"; npm run build                    # 通过
.\venv\Scripts\python run.py  # 打开 http://127.0.0.1:8000
```
