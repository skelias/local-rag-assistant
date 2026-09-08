"""数据模型（Pydantic）：给进出的数据"定形状 + 把关"。

BaseModel 用法：声明类属性 = 声明字段；实例化时自动校验类型。
输入模型：给 API 请求"把关"；以后再加输出模型（序列化返回）。
"""
from typing import Any

from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    """创建一条消息时的输入数据。"""
    role: str                                          # user / assistant / system
    content: str                                       # 消息内容
    sources: list[dict[str, Any]] = Field(default_factory=list)  # AI 的来源引用

    # 注意：默认值写 Field(default_factory=list) 而不是 = []
    # 原因：=[] 会让所有实例共享同一个列表（Python 可变默认值经典坑）


class DocumentCreate(BaseModel):
    """新建一条文档记录时的输入数据。"""
    kb_id: int = 1                                     # 属于哪个知识库
    filename: str                                      # 文件名
    file_type: str                                     # 扩展名 .md/.pdf...
    file_path: str                                     # 存在磁盘哪里
    size: int = 0                                      # 字节数


class ChatRequest(BaseModel):
    """发起一次对话（流式）的输入。"""
    kb_id: int = 1
    conversation_id: int | None = None   # None = 开新对话
    query: str
    model: str | None = None             # None = 用配置默认
    # 检索参数覆盖（可选；缺省读 kb 级配置 —— 单一参数源）
    top_k: int | None = None
    threshold: float | None = None


class HitTestRequest(BaseModel):
    """命中测试（检索调试台）的输入；与对话共用同一套检索参数。"""
    kb_id: int = 1
    query: str
    top_k: int | None = None
    threshold: float | None = None
    rerank_enabled: bool | None = None


class ConfigItem(BaseModel):
    """写一条配置：键 + JSON 值。"""
    key: str
    value: Any
