"""对话接口：POST /api/chat/stream —— SSE 流式回答。

事件协议（前端照着解析）：
  event: sources   data: [{n,file,score,...}]   先推来源（引用面板可先画）
  event: token     data: {"t": "一个字"}        流式文字
  event: done      data: {"conversation_id": N}  结束
"""
import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_chat_gateway, get_db, get_vector_store
from app.core.llm_gateway import ChatMessage
from app.models.schemas import ChatRequest, MessageCreate
from app.services.rag_engine import RAGEngine
from app.services.repositories import ConfigRepository, ConversationRepository

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    db=Depends(get_db),
    store=Depends(get_vector_store),
    gateway=Depends(get_chat_gateway),
):
    conv_repo = ConversationRepository(db)

    # 1) 新对话：建会话；否则续接
    conv_id = req.conversation_id
    if conv_id is None:
        conv_id = await conv_repo.create(title=req.query[:30], model=req.model, kb_id=req.kb_id)

    # 2) 取最近历史（最近 3 轮 = 最多 6 条 user/assistant）
    history_rows = await conv_repo.get_messages(conv_id)
    history = [
        ChatMessage(role=m["role"], content=m["content"])
        for m in history_rows
        if m["role"] in ("user", "assistant")
    ][-6:]

    # 3) 把用户问题存库
    await conv_repo.save_message(conv_id, MessageCreate(role="user", content=req.query))

    engine = RAGEngine(store=store, gateway=gateway,
                       cfg=ConfigRepository(db), kb_id=req.kb_id)

    async def event_gen():
        full_text = ""
        sources_payload: list[dict] = []
        async for payload, sources in engine.generate_stream(
            req.query,
            history=history,
            kb_id=req.kb_id,
            model=req.model,
            overrides={"top_k": req.top_k, "threshold": req.threshold},
        ):
            if sources is not None:                      # 首帧：来源
                sources_payload = [s.to_dict() for s in sources]
                yield {"event": "sources",
                       "data": json.dumps(sources_payload, ensure_ascii=False)}
            elif payload:                                # 后续帧：文字
                full_text += payload
                yield {"event": "token",
                       "data": json.dumps({"t": payload}, ensure_ascii=False)}

        # 4) AI 完整回答落库（含来源），再发结束事件
        await conv_repo.save_message(conv_id, MessageCreate(
            role="assistant", content=full_text, sources=sources_payload,
        ))
        yield {"event": "done",
               "data": json.dumps({"conversation_id": conv_id})}

    return EventSourceResponse(event_gen())
