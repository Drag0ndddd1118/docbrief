"""Pre-computed showcase: a real SEC filing analysed ahead of time so the public demo costs nothing to browse.

The cache (`showcase/nvidia_fy2026_mdna.json`) holds the analysis, a few Q&A turns, a Tavily fact-check and the
chunk embeddings, all produced live by `scripts/build_showcase.py` with the same pipeline the app runs for uploads.
"""
from __future__ import annotations

import base64
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import numpy as np

from .chunking import Chunk
from .types import Analysis, FactCheck, Metric, Point, Source

ROOT = Path(__file__).resolve().parent.parent
SHOWCASE_PDF = ROOT / "samples" / "nvidia_fy2026_10k_mdna_excerpt.pdf"
SHOWCASE_JSON = ROOT / "showcase" / "nvidia_fy2026_mdna.json"
SHOWCASE_TITLE = "NVIDIA Form 10-K FY2026 — MD&A (excerpt)"


def _norm(q: str) -> str:
    return re.sub(r"\W+", " ", q.lower()).strip()


def analysis_from_dict(d: dict) -> Analysis:
    return Analysis(
        title=d.get("title", ""),
        doc_type=d.get("doc_type", "other"),
        tldr=d.get("tldr", ""),
        summary=d.get("summary", ""),
        key_points=[Point(**p) for p in d.get("key_points", [])],
        metrics=[Metric(**m) for m in d.get("metrics", [])],
        risks=[Point(**p) for p in d.get("risks", [])],
        suggested_questions=list(d.get("suggested_questions", [])),
        engine=d.get("engine", ""),
    )


def source_from_dict(d: dict) -> Source:
    return Source(label=d["label"], page=d.get("page"), text=d.get("text", ""), url=d.get("url", ""), title=d.get("title", ""))


def factcheck_from_dict(d: dict) -> FactCheck:
    d = dict(d)
    d["sources"] = [source_from_dict(s) for s in d.get("sources", [])]
    return FactCheck(**d)


def encode_matrix(m: np.ndarray) -> dict:
    a = np.asarray(m, dtype=np.float16)
    return {"shape": list(a.shape), "dtype": "float16", "b64": base64.b64encode(a.tobytes()).decode()}


def decode_matrix(d: dict) -> np.ndarray:
    return np.frombuffer(base64.b64decode(d["b64"]), dtype=np.float16).reshape(d["shape"]).astype(np.float32)


class Showcase:
    def __init__(self, data: dict):
        self.data = data
        self.analysis = analysis_from_dict(data["analysis"])
        self.qa = data.get("qa", [])
        self.factcheck = [factcheck_from_dict(f) for f in data.get("factcheck", [])]
        self.matrix: Optional[np.ndarray] = decode_matrix(data["embeddings"]) if data.get("embeddings") else None
        self.chunk_hash: str = data.get("chunk_hash", "")

    @classmethod
    def load(cls, path: Path = SHOWCASE_JSON) -> Optional["Showcase"]:
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except Exception:
            return None

    @property
    def meta(self) -> dict:
        return self.data.get("meta", {})

    @property
    def questions(self) -> list[str]:
        return [t["q"] for t in self.qa]

    def find_answer(self, q: str) -> Optional[dict]:
        n = _norm(q)
        return next((t for t in self.qa if _norm(t["q"]) == n), None)

    def matrix_for(self, chunks: list[Chunk]) -> Optional[np.ndarray]:
        """Cached embeddings are only valid for exactly the chunks they were computed from."""
        return self.matrix if self.matrix is not None and self.chunk_hash == chunks_hash(chunks) else None


def chunks_hash(chunks: list[Chunk]) -> str:
    import hashlib

    h = hashlib.sha1()
    for c in chunks:
        h.update(f"{c.page}|{c.text}\n".encode())
    return h.hexdigest()[:16]


def to_cache_dict(analysis: Analysis, qa: list[dict], factcheck: list[FactCheck], matrix: Optional[np.ndarray], chunks: list[Chunk], meta: dict) -> dict:
    return {
        "meta": meta,
        "analysis": analysis.to_dict(),
        "qa": qa,
        "factcheck": [asdict(f) for f in factcheck],
        "embeddings": encode_matrix(matrix) if matrix is not None else None,
        "chunk_hash": chunks_hash(chunks),
    }

# steers the showcase fact-check towards headline numbers that the press/analysts also report
SHOWCASE_FOCUS = "headline financial results that news and analysts report (revenue, growth, margins, buybacks), not legal or tax boilerplate"
