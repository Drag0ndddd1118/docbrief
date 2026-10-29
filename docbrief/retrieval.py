"""Hybrid retrieval: BM25 (always) + dense embeddings from Nebius (when available), fused with RRF."""
from __future__ import annotations

import re
from typing import Callable, Optional, Sequence

import numpy as np
from rank_bm25 import BM25Okapi

from .chunking import Chunk

_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-%$]*")
_CJK = re.compile(r"[\u4e00-\u9fff]")
STOP = set(
    "a an the of and or to in on for with by is are was were be been it its this that these those as at from "
    "what which who how why when where do does did can could should would about into over than then also not "
    "has have had we our their they you your i me my".split()
)


def tokenize(text: str) -> list[str]:
    text = text.lower()
    toks = [t.strip(".-") for t in _WORD.findall(text)]
    toks = [t for t in toks if t and t not in STOP]
    cjk = _CJK.findall(text)  # character bigrams for Chinese
    toks += [a + b for a, b in zip(cjk, cjk[1:])]
    return toks


Embedder = Callable[[Sequence[str]], np.ndarray]


class Retriever:
    def __init__(self, chunks: list[Chunk], embedder: Optional[Embedder] = None):
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c.text) or ["_"] for c in chunks])
        self.embedder = embedder
        self.matrix: Optional[np.ndarray] = None
        self.embed_error: Optional[str] = None
        if embedder is not None:
            try:
                m = np.asarray(embedder([c.text for c in chunks]), dtype=np.float32)
                self.matrix = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
            except Exception as e:  # embeddings are optional — degrade to BM25
                self.embed_error = f"{type(e).__name__}: {e}"

    @property
    def mode(self) -> str:
        return "hybrid (BM25 + embeddings)" if self.matrix is not None else "BM25"

    def search(self, query: str, k: int = 6) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        bm = np.asarray(self.bm25.get_scores(tokenize(query) or ["_"]))
        order_bm = np.argsort(-bm)
        scores: dict[int, float] = {}
        for rank, i in enumerate(order_bm[: max(k * 3, 12)]):
            if bm[i] > 0:
                scores[int(i)] = scores.get(int(i), 0.0) + 1.0 / (60 + rank)
        if self.matrix is not None and self.embedder is not None:
            try:
                q = np.asarray(self.embedder([query]), dtype=np.float32)[0]
                q = q / (np.linalg.norm(q) + 1e-9)
                sim = self.matrix @ q
                for rank, i in enumerate(np.argsort(-sim)[: max(k * 3, 12)]):
                    scores[int(i)] = scores.get(int(i), 0.0) + 1.0 / (60 + rank)
            except Exception as e:
                self.embed_error = f"{type(e).__name__}: {e}"
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:k]
        return [(self.chunks[i], s) for i, s in ranked]
