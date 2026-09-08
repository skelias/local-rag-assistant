"""文档管线测试：Parser(解析) + Splitter(切分) 的可插拔契约。

规则：文件名以 test_ 开头；这里测纯函数，不碰数据库/网络。
"""
from pathlib import Path

import pytest

from app.services.doc_pipeline import (
    PipelineError,
    RecursiveSplitter,
    parse_document,
    split_python_code,
)


def test_parse_markdown_returns_blocks():
    blocks = parse_document(Path("x.md"), "# 标题\n\n第一段文字。\n\n第二段。")
    assert len(blocks) >= 3          # 标题 + 两段
    assert blocks[0].text == "# 标题"
    assert blocks[1].text == "第一段文字。"


def test_parse_txt_plain_paragraphs():
    blocks = parse_document(Path("x.txt"), "第一行。\n第二行。\n\n第三段。")
    assert len(blocks) >= 2


def test_parse_unsupported_ext_raises():
    with pytest.raises(PipelineError):
        parse_document(Path("x.xyz"), "内容")


def test_splitter_breaks_long_block():
    splitter = RecursiveSplitter(chunk_size=500, overlap=50)
    blocks = parse_document(Path("x.md"), "词" * 3000)
    chunks = splitter.split(blocks)
    assert len(chunks) >= 2
    assert all(len(c.text) <= 600 for c in chunks)     # 500 + 允许一点余量


def test_split_python_code_batches_lines():
    code = "".join(f"def f{i}():\n    return {i}\n\n" for i in range(30))
    parts = split_python_code(code, max_lines=20)
    assert len(parts) >= 2
    # 合起来仍是原来的代码（没有丢内容）
    assert "".join(parts).strip() == code.strip()
