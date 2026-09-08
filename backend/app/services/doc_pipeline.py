"""文档管线：解析(Parse) → 切分(Split) 的可插拔契约。

契约（换解析器不改下游的关键）：
  parse_document(path, content) -> list[ParsedBlock]   # 文件 → 语义块
  RecursiveSplitter.split(blocks)  -> list[Chunk]      # 语义块 → 长度受控的分块
  （Indexer 入库在 P0-6 下节课 + P0-7 API 组装）

支持的解析器（可扩展）：
  .md/.txt/.markdown → 按空行切块
  代码类(.py/.js/.ts/...) → 整文件一个块，交给"按行切分器"
  .pdf/.docx → 未装解析器 → 明确报错（P1 接 Docling 等）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


class PipelineError(Exception):
    """文档管线业务错误（如：不支持的格式）。"""


@dataclass
class ParsedBlock:
    """解析器产出的"语义块"：一段有意义文字 + 附带元数据。"""
    text: str
    meta: dict = field(default_factory=dict)


@dataclass
class Chunk:
    """入库分块：长度受控的文字 + meta + 序号。"""
    text: str
    meta: dict = field(default_factory=dict)
    seq: int = 0


# ---------------- 解析器（按扩展名分派） ----------------

_CODE_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".json",
              ".yaml", ".yml", ".toml", ".csv", ".html", ".css"}
_TEXT_EXTS = {".md", ".txt", ".markdown"}


def parse_document(path: Path, content: str | None = None) -> list[ParsedBlock]:
    """根据扩展名调用对应解析器，返回语义块列表。"""
    ext = path.suffix.lower()
    text = content if content is not None else path.read_text(encoding="utf-8", errors="replace")

    if ext in _TEXT_EXTS:
        return _parse_paragraphs(text)
    if ext in _CODE_EXTS:
        # 代码不按空行切（空行在代码里有意义），整文件先当一个块
        return [ParsedBlock(text=text, meta={"lang": ext.lstrip(".")})]
    if ext in {".pdf", ".docx"}:
        raise PipelineError(
            f"{ext} 解析器未安装（P0 默认支持 md/txt/代码类；PDF/DOCX 等 P1 接入 Docling/OCR）"
        )
    raise PipelineError(f"不支持的文件类型：{ext or '(无扩展名)'}")


def _parse_paragraphs(text: str) -> list[ParsedBlock]:
    """按空行把文本切成段落块（Markdown 标题单独成块，天然保留）。"""
    blocks: list[ParsedBlock] = []
    for raw in text.split("\n\n"):
        block = raw.strip()
        if block:
            blocks.append(ParsedBlock(text=block))
    return blocks or [ParsedBlock(text=text.strip())]


# ---------------- 切分器 ----------------

class RecursiveSplitter:
    """通用切分：先切成 ≤chunk_size 的小段（优先句号/换行断开），再带重叠拼接。

    无法断开的超长巨块（无标点无换行）直接硬切成 chunk_size 片段 —— 保证每块长度可控。
    """

    def __init__(self, chunk_size: int = 1200, overlap: int = 150):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, blocks: list[ParsedBlock]) -> list[Chunk]:
        chunks: list[Chunk] = []
        seq = 0
        for b in blocks:
            text = b.text
            if len(text) <= self.chunk_size:
                chunks.append(Chunk(text=text, meta=dict(b.meta), seq=seq))
                seq += 1
                continue

            cur = ""
            for piece in self._pieces(text):
                # 是否把新段并入当前块
                if cur and len(cur) + len(piece) + 1 > self.chunk_size:
                    chunks.append(Chunk(text=cur, meta=dict(b.meta), seq=seq))
                    seq += 1
                    # 下一块带上前一块的"尾巴"做重叠（防止跨块语义断裂）
                    tail = cur[-self.overlap:] if self.overlap else ""
                    cur = (tail + "\n" + piece).strip() if len(tail) + len(piece) + 1 <= self.chunk_size else piece
                else:
                    cur = (cur + "\n" + piece).strip() if cur else piece
            if cur:
                chunks.append(Chunk(text=cur, meta=dict(b.meta), seq=seq))
                seq += 1
        return chunks

    def _pieces(self, text: str, cap: int | None = None) -> list[str]:
        """把文本切成 ≤cap(默认 chunk_size) 的片段，优先在句末/换行断开。"""
        cap = cap or self.chunk_size
        segs = re.split(r"(?<=[。！？!?\n])", text)
        out: list[str] = []
        buf = ""
        for seg in segs:
            if len(seg) >= cap:                     # 无法断开的巨块 → 硬切
                if buf:
                    out.append(buf)
                    buf = ""
                out.extend(seg[i:i + cap] for i in range(0, len(seg), cap))
            elif buf and len(buf) + len(seg) > cap:
                out.append(buf)
                buf = seg
            else:
                buf += seg
        if buf:
            out.append(buf)
        return out or [text]


def split_python_code(code: str, max_lines: int = 40, min_lines: int = 5) -> list[str]:
    """代码按行批量切分：在空行处断开，尽量保住完整语句块。

    精确版（tree-sitter AST 切分）留到 P1；这个轻量版对教学和多数场景够用。
    """
    lines = code.splitlines(keepends=True)
    if len(lines) <= max_lines:
        return [code]

    parts: list[str] = []
    buf: list[str] = []
    blank_streak = 0
    for line in lines:
        buf.append(line)
        if line.strip() == "":
            blank_streak += 1
        else:
            blank_streak = 0
        # 攒够 max_lines 且正好在空行处 → 收一刀
        if len(buf) >= max_lines and blank_streak >= 1:
            parts.append("".join(buf))
            buf = []
            blank_streak = 0
    if buf:
        parts.append("".join(buf))

    # 尾巴太短（凑不成一个完整块）就并进上一块，避免孤立碎代码
    if len(parts) > 1 and len(parts[-1].splitlines()) < min_lines:
        parts[-2] += parts[-1]
        parts.pop()
    return parts


# ---------------- 流程编排：落盘 → 解析分块 → 预览 → 确认入库 ----------------

def save_upload(content: bytes, filename: str, kb_id: int,
                base_dir: Path | None = None) -> Path:
    """把上传的文件字节存到 data/uploads/kb{id}/ 下，返回落盘路径。

    base_dir 默认用配置里的 UPLOAD_DIR；测试可传临时目录。
    """
    from app.core.config import settings
    root = base_dir or settings.UPLOAD_DIR
    name = Path(filename).name                    # 只留文件名，去掉可能的路径成分
    folder = root / f"kb{kb_id}"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / name
    dest.write_bytes(content)
    return dest


async def run_upload_pipeline(path: Path, chunk_repo, doc_id: int, kb_id: int) -> int:
    """同步段（快）：解析 → 分块 → 写 SQLite(pending)。返回 pending 块数。

    文档状态由调用方负责：先 uploading，跑完本函数后置 parsed（“待确认”）。
    """
    content = path.read_text(encoding="utf-8", errors="replace")
    ext = path.suffix.lower()
    blocks = parse_document(path, content)

    if ext in _CODE_EXTS:
        # 代码类：.py 用“按行批切”，其余代码类型退回通用切分
        if ext == ".py":
            parts: list[str] = []
            for b in blocks:
                parts.extend(split_python_code(b.text))
            chunks = [Chunk(text=p, meta={"lang": ext.lstrip(".")}, seq=i)
                      for i, p in enumerate(parts)]
        else:
            chunks = [Chunk(text=b.text, meta={**b.meta, "lang": ext.lstrip(".")}, seq=i)
                      for i, b in enumerate(RecursiveSplitter().split(blocks))]
    else:
        chunks = RecursiveSplitter().split(blocks)

    rows = [{"kb_id": kb_id, "document_id": doc_id, "seq": c.seq,
             "text": c.text, "meta": {"file": path.name, **c.meta}}
            for c in chunks]

    await chunk_repo.delete_by_document(doc_id)   # 清旧块（重新上传场景）
    await chunk_repo.insert_many(rows)
    return len(rows)


async def confirm_document_index(doc_id: int, kb_id: int, doc_repo, chunk_repo,
                                 store) -> None:
    """确认入库：把 pending chunks 向量化写入向量库 → 标记 indexed → 文档 ready。

    store 需有 async upsert_chunks(chunks)；测试注入 RecordingStore / FakeEmbedder+QdrantStore。
    """
    rows = await chunk_repo.list_pending(doc_id)
    if rows:
        await store.upsert_chunks([{**r, "id": r["id"]} for r in rows])
        await chunk_repo.mark_indexed(doc_id)
    await doc_repo.set_status(doc_id, "ready")
