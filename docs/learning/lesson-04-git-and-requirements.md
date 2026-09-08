# 第 4 课：requirements 清单 + git 四件套

## 购物清单（requirements）

| 文件 | 用途 | 内容 |
|---|---|---|
| requirements.txt | 正式运行项目的人照它装 | 运行时依赖 |
| requirements-dev.txt | 开发者用 | `-r requirements.txt` + pytest 等 |

铁律：**每装一个新库，就同步加一行清单**，清单永远等于事实。
版本写法：`包名==1.2.3`（精确锁死）/ `包名>=1.2`（最低版本，可升级）。

## git 四件套

```
git status           工作台体检：哪些文件变了（红=未登记，绿=已 add）
git add 文件名       把改动登记进"候选名单"
git commit -m "说明"  把候选名单拍照存档 = 一个新版本
git log --oneline    翻版本历史（一行一个）
```

- 为什么分两步：add 让你**挑文件**，commit 才打包 —— 可以只提交部分文件。
- `.gitignore`：里面写的（`venv/`、`.env`、`data/`…）git 自动无视。
- commit 说明写作规范：`类型(范围): 一句话`，如 `feat(p0-1): ...`（feat=新功能 / fix=修 bug / docs=文档 / chore=杂务）。

## 作业自测（答案在下文，先自己默答再看）

1. requirements.txt 和 requirements-dev.txt 的区别？
2. 为什么 commit 前要 add？
3. .gitignore 里写了 `venv/`，git 会怎样？

<details>
<summary>答案</summary>
1. 前者是"正式运行"的购物清单，后者是"开发者"额外要的（含测试工具），并引用前者。
2. add = 挑出要存的文件；commit = 拍照存档。分开做才能"只提交想要的部分"。
3. 自动无视 venv 文件夹 —— 它不会出现在 status 里，也不会被 commit。
</details>
