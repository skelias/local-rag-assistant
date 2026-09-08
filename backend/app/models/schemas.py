"""数据模型（Pydantic）：给进出的数据"定形状 + 把关"。

BaseModel 用法：声明类属性 = 声明字段；实例化时自动校验类型。
目前只定义"创建类输入"需要的两个模型；后面需要"输出模型"时再加。
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
