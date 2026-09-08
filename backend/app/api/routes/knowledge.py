"""知识库接口组：上传 / 列表 / 预览 / 确认入库 / 删除。

流程串起第 14 课的函数：save_upload → run_upload_pipeline → preview → confirm_document_index。
"""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_db, get_upload_dir, get_vector_store
from app.core.config import settings
from app.models.schemas import DocumentCreate
from app.services.doc_pipeline import (
    PipelineError,
    confirm_document_index,
    run_upload_pipeline,
    save_upload,
)
from app.services.repositories import ChunkRepository, DocumentRepository

router = APIRouter(prefix="/api", tags=["knowledge"])


@router.post("/knowledge/{kb_id}/documents", status_code=201)
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    db=Depends(get_db),
    upload_dir=Depends(get_upload_dir),
):
    """上传文档：落盘 → 解析+分块(pending) → 文档状态 parsed(待确认)。"""
    name = Path(file.filename or "unnamed").name          # 只留文件名，防路径注入
    ext = Path(name).suffix.lower()
    if ext not in settings.allowed_exts:
        raise HTTPException(415, f"不支持的类型：{ext or '(无扩展名)'}")

    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"超过 {settings.max_upload_mb}MB 上限")

    dest = save_upload(data, name, kb_id, base_dir=upload_dir)

    doc_repo = DocumentRepository(db)
    chunk_repo = ChunkRepository(db)
    doc_id = await doc_repo.create(DocumentCreate(
        kb_id=kb_id, filename=name, file_type=ext,
        file_path=str(dest), size=len(data),
    ))

    try:
        count = await run_upload_pipeline(dest, chunk_repo, doc_id, kb_id)
    except PipelineError as e:
        await doc_repo.set_status(doc_id, "failed", str(e))
        raise HTTPException(422, f"解析失败：{e}")

    await doc_repo.set_status(doc_id, "parsed")
    doc = await doc_repo.get(doc_id)
    return {**doc, "pending_chunks": count}


@router.get("/knowledge/{kb_id}/documents")
async def list_documents(kb_id: int, db=Depends(get_db)):
    """列出某知识库的文档（含状态与已索引分块数）。"""
    return await DocumentRepository(db).list_by_kb(kb_id)


@router.get("/knowledge/{kb_id}/documents/{doc_id}/preview")
async def preview_document(doc_id: int, kb_id: int, db=Depends(get_db)):
    """分段预览（只读）：parsed→看 pending；ready→看全部（历史）。"""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get(doc_id)
    if not doc or doc["kb_id"] != kb_id:
        raise HTTPException(404, "文档不存在")

    chunk_repo = ChunkRepository(db)
    rows = await chunk_repo.list_pending(doc_id)
    if not rows and doc["status"] == "ready":
        rows = await chunk_repo.list_all(doc_id)

    return {"chunks": [{"seq": c["seq"], "text": c["text"][:2000], "meta": c["meta"]}
                       for c in rows]}


@router.post("/knowledge/{kb_id}/documents/{doc_id}/confirm")
async def confirm_document(doc_id: int, kb_id: int,
                           db=Depends(get_db), store=Depends(get_vector_store)):
    """确认入库：pending 分块向量化进 Qdrant → 文档 ready。

    真实嵌入模型(BGE-M3/torch)未装时会报 422 友好错误 —— 那正是下一步要装的。
    """
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get(doc_id)
    if not doc or doc["kb_id"] != kb_id:
        raise HTTPException(404, "文档不存在")
    if doc["status"] == "ready":
        return {"status": "ready"}                       # 幂等：已入库直接返回
    if doc["status"] != "parsed":
        raise HTTPException(409, f"状态 {doc['status']} 不可确认（需 parsed）")

    try:
        await confirm_document_index(doc_id, kb_id, doc_repo, ChunkRepository(db), store)
    except Exception as e:                                # 真实嵌入未装/网络等
        await doc_repo.set_status(doc_id, "failed", str(e))
        raise HTTPException(422, f"入库失败：{e}")
    return {"status": "ready"}


@router.delete("/knowledge/{kb_id}/documents/{doc_id}")
async def delete_document(doc_id: int, kb_id: int,
                          db=Depends(get_db), store=Depends(get_vector_store)):
    """删除文档：向量库清除 + 数据库级联删 chunks + 尝试删原文件。"""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get(doc_id)
    if not doc or doc["kb_id"] != kb_id:
        raise HTTPException(404, "文档不存在")

    await store.delete_document(doc_id=doc_id, kb_id=kb_id)
    await doc_repo.delete(doc_id)
    try:                                                  # 原文件删不掉也不致命
        Path(doc["file_path"]).unlink(missing_ok=True)
    except Exception:
        pass
    return {"ok": True}
