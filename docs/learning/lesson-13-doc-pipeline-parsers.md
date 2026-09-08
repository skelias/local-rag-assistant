# 第 13 课：文档管线（上）—— 可插拔解析/切分

## 为什么要"可插拔契约"

解析器千万别写死在业务里（RAGFlow 0.21 的教训）。
统一契约：文件 → Parser → ParsedBlock(语义块) → Splitter → Chunk(受控分块) → Indexer(入库，下节)。

## 今天的实现

- `app/services/doc_pipeline.py`：
  - `PipelineError`（业务错误：不支持的格式）
  - `ParsedBlock` / `Chunk`（两个 dataclass：语义块 vs 入库分块）
  - `parse_document(path, content)`：按扩展名分派
    - md/txt/markdown → 按空行切段落块（标题天然成块）
    - 代码类(.py/.js/.ts/json/yaml...) → 整文件一个块（交给按行切分器）
    - pdf/docx → 明确报错（不假装支持；P1 接 Docling/OCR）
  - `RecursiveSplitter(chunk_size=1200, overlap=150)`：先切 ≤chunk_size 小段(句/行断开)，
    再带重叠拼接；无标点巨块硬切 → 保证块长可控
  - `split_python_code(code, max_lines)`：按行批量 + 空行处断刀 + 短尾并入前块

## 踩坑

切分器最初假设"前置拆分已把片段限制在 ~800 字符"，但 chunk_size 可以更小(500) → 单片超限。
修复：拆与并统一按 chunk_size 约束（`_pieces` 的 cap），并给"无法断开的巨块"走硬切分支。

## 测试（5 个新增，合计 28 passed）

md 按空行出块 / txt 段落 / 不支持格式报错 / 超长块切分长度可控 / 代码按行批切且不丢内容。

## 思考题

Q：为什么"代码按行+空行处切"而不是像文档那样按句号切？
A：代码里句号(.)到处都是（点运算符、小数、省略号），按句号切=碎成渣；
    空行才是代码的"自然分段点"（函数/类之间的分隔），在空行处断刀最保整。
