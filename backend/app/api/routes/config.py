"""配置接口：GET/PUT /api/config —— 运行时改设置（模型、检索参数等）。

存的键就是 RetrievalParamsResolver / Gateway 读的那些，
例如 kb.1.retrieval.top_k / llm.primary_model ...
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.models.schemas import ConfigItem
from app.services.repositories import ConfigRepository

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config")
async def get_config(db=Depends(get_db)) -> dict:
    """把所有设置倒出来（设置页加载用）。"""
    return await ConfigRepository(db).all()


@router.put("/config")
async def put_config(item: ConfigItem, db=Depends(get_db)) -> dict:
    """写一条设置（运行时生效）。"""
    await ConfigRepository(db).set(item.key, item.value)
    return {"ok": True, "key": item.key, "value": item.value}
