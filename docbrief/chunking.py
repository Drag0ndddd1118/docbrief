"""Page-aware chunking."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .pdf_loader import Document


@dataclass(frozen=True)
class Chunk:
    id: int
    page: int
    text: str


def chunk_document(doc: Document, size: int = 1100, overlap: int = 150) -> list[Chunk]:
    """Split each page into ~`size`-char chunks on paragraph/sentence boundaries."""
    chunks: list[Chunk] = []
    for pno, text in enumerate(doc.pages, 1):
        if not text.strip():
            continue
        units = [u.strip() for u in re.split(r"\n{2,}|(?<=[.!?。！？])\s+", text) if u.strip()]
        buf = ""
        for u in units:
            if buf and len(buf) + len(u) + 1 > size:
                chunks.append(Chunk(len(chunks), pno, buf.strip()))
                buf = buf[-overlap:] + " " + u if overlap else u
            else:
                buf = f"{buf} {u}" if buf else u
        if buf.strip():
            chunks.append(Chunk(len(chunks), pno, buf.strip()))
    return chunks
