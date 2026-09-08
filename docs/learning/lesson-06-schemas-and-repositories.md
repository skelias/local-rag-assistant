# 第 6 课：Pydantic 数据模型 + Repository 模式

## 核心概念

| 词 | 一句话 |
|---|---|
| Pydantic | Python 的数据校验库：用类定义"数据形状"，进来自动把关 |
| BaseModel | Pydantic 的基类；继承它，类属性就是字段 |
| Repository 模式 | 每个表配一个"管理员"类；业务代码不直接写 SQL |
| fixture | pytest 的"夹具"：每场测试前准备好的东西（这里=临时数据库+管理员） |
| `Field(default_factory=list)` | 列表默认值的正确写法（`=[]` 会让所有实例共享同一个列表！） |

## 本次新增文件

- `app/models/schemas.py`：`MessageCreate`（role/content/sources）、`DocumentCreate`（kb_id/filename/...）—— 目前只要"输入模型"，用到再加输出模型
- `app/services/repositories.py`：
  - `ConversationRepository`：create / save_message / get_messages / list / delete
  - `DocumentRepository`：create / get / set_status / list_by_kb
  - 私有小工具 `_json` / `_loads`（Python 对象 ↔ JSON 字符串）
- `tests/test_repositories.py`：4 个测试（对话创建、存消息+读回 sources、文档状态机、删对话级联删消息）

## 关键写法回顾

```python
# 存消息：sources 列表 → JSON 字符串进 TEXT 列
_json(msg.sources)

# 读消息：JSON 字符串 → 还原成列表
dict(r) | {"sources": _loads(r["sources"], [])}

# 删除级联：建表时写了 REFERENCES ... ON DELETE CASCADE
# → 删 conversations 行，messages 里指向它的行自动消失
```

## 状态

测试 `8 passed`；commit `feat(p0-2): pydantic schemas and conversation/document repositories`。

## 下一课预告

还剩三个"管理员"没写：ChunkRepository（分块）、ConfigRepository（设置）、UsageRepository（用量）—— 写完 P0-2 就收官。
