"""Live engine: NVIDIA Nemotron models served by Nebius Token Factory."""
from __future__ import annotations

import re
from typing import Optional

from . import prompts
from .chunking import Chunk
from .config import Settings
from .llm import NebiusLLM
from .metrics import detect_doc_type, verify_metrics
from .pdf_loader import Document
from .retrieval import Retriever
from .types import Analysis, Answer, Metric, Point, Source

SINGLE_PASS_CHARS = 60_000  # ≈15k tokens: one call to the main model
SECTION_CHARS = 36_000  # map step section size for long documents
LANG_NAME = {"auto": "the same language as the user's question (default English)", "en": "English", "zh": "Simplified Chinese (简体中文)"}


def _points(items) -> list[Point]:
    out = []
    for it in items or []:
        if isinstance(it, str):
            out.append(Point(it))
        elif isinstance(it, dict) and it.get("text"):
            pg = it.get("page")
            out.append(Point(str(it["text"]), int(pg) if str(pg).isdigit() else None))
    return out


def _metrics(items) -> list[Metric]:
    out = []
    for it in items or []:
        if isinstance(it, dict) and it.get("name") and it.get("value"):
            pg = it.get("page")
            out.append(
                Metric(
                    name=str(it["name"]),
                    value=str(it["value"]),
                    period=str(it.get("period") or ""),
                    page=int(pg) if str(pg).isdigit() else None,
                    note=str(it.get("note") or ""),
                )
            )
    return out


def _to_analysis(d: dict, doc: Document, engine: str) -> Analysis:
    a = Analysis(
        title=str(d.get("title") or doc.meta_title or doc.name),
        doc_type=d.get("doc_type") if d.get("doc_type") in ("financial_report", "research_paper", "other") else detect_doc_type(doc.full_text),
        tldr=str(d.get("tldr") or ""),
        summary=str(d.get("summary") or ""),
        key_points=_points(d.get("key_points")),
        metrics=_metrics(d.get("metrics")),
        risks=_points(d.get("risks")),
        suggested_questions=[str(q) for q in (d.get("suggested_questions") or [])][:3],
        engine=engine,
    )
    verify_metrics(a.metrics, doc.full_text)  # grounding check against the source PDF
    return a


class LiveEngine:
    name = "live"

    def __init__(self, s: Settings):
        self.s = s
        self.llm = NebiusLLM(s)

    def describe(self) -> str:
        return f"Nebius Token Factory · {self.s.model} (+ {self.s.fast_model.split('/')[-1]} for long docs)"

    # ---- analysis -------------------------------------------------------
    def analyze(self, doc: Document, lang: str = "en", progress=None) -> Analysis:
        lname = LANG_NAME.get(lang, "English")
        suffix = f"\nWrite all prose fields in {lname}; keep metric values exactly as written in the document."
        text = doc.marked_text()
        if len(text) <= SINGLE_PASS_CHARS:
            msgs = [
                {"role": "system", "content": prompts.ANALYZE_SYSTEM + suffix},
                {"role": "user", "content": f"Document: {doc.name}\n\n{text}"},
            ]
            d = self.llm.chat_json(msgs, tier="main")
            return _to_analysis(d, doc, self.describe())

        # map-reduce for long documents: fast Nemotron per section, main Nemotron merges
        sections, buf = [], ""
        for pno, ptxt in enumerate(doc.pages, 1):
            piece = f"[[Page {pno}]]\n{ptxt}\n\n"
            if buf and len(buf) + len(piece) > SECTION_CHARS:
                sections.append(buf)
                buf = ""
            buf += piece
        if buf:
            sections.append(buf)
        partials = []
        for i, sec in enumerate(sections, 1):
            if progress:
                progress(i / (len(sections) + 1), f"Reading section {i}/{len(sections)} with {self.s.fast_model.split('/')[-1]}…")
            try:
                partials.append(
                    self.llm.chat_json(
                        [
                            {"role": "system", "content": prompts.MAP_SYSTEM},
                            {"role": "user", "content": f"Document: {doc.name} — section {i}/{len(sections)}\n\n{sec}"},
                        ],
                        tier="fast",
                    )
                )
            except Exception:
                continue
        if not partials:
            raise RuntimeError("Could not analyse any section of the document.")
        if progress:
            progress(0.95, f"Merging with {self.s.model.split('/')[-1]}…")
        import json

        d = self.llm.chat_json(
            [
                {"role": "system", "content": prompts.REDUCE_SYSTEM + suffix},
                {"role": "user", "content": f"Document: {doc.name}\n\nPartial analyses:\n{json.dumps(partials, ensure_ascii=False)[:90000]}"},
            ],
            tier="main",
        )
        return _to_analysis(d, doc, self.describe() + " · map-reduce")

    # ---- web fact-check (Tavily + Nemotron) -----------------------------
    def fact_check(self, doc: Document, analysis: Analysis, search, lang: str = "en", n: int = 3):
        from .factcheck import run_fact_check

        return run_fact_check(self.llm, doc, analysis, search, LANG_NAME.get(lang, "English"), n)

    # ---- retrieval + Q&A ------------------------------------------------
    def build_retriever(self, chunks: list[Chunk]) -> Retriever:
        return Retriever(chunks, embedder=self.llm.embed)

    def _rewrite(self, q: str) -> str:
        if not re.search(r"[^\x00-\x7f]", q):
            return q
        try:
            return self.llm.chat(
                [{"role": "system", "content": prompts.REWRITE_SYSTEM}, {"role": "user", "content": q}],
                tier="fast",
                max_tokens=600,
            ).strip() or q
        except Exception:
            return q

    def answer(
        self,
        doc: Document,
        retriever: Retriever,
        question: str,
        history: Optional[list[dict]] = None,
        lang: str = "auto",
        deep: bool = False,
        web: Optional[list[Source]] = None,
    ) -> Answer:
        query = self._rewrite(question)
        hits = retriever.search(query if query == question else f"{query} {question}", k=7)
        sources = [Source(label=f"S{i}", page=c.page, text=c.text) for i, (c, _) in enumerate(hits, 1)]
        ctx = "\n\n".join(f"[p.{s.page}] {s.text}" for s in sources)
        if web:
            ctx += "\n\nWeb sources:\n" + "\n\n".join(f"[{w.label}] ({w.url}) {w.text}" for w in web)
        msgs = [{"role": "system", "content": prompts.QA_SYSTEM + f"\nReply language: {LANG_NAME.get(lang, 'English')}."}]
        for h in (history or [])[-6:]:
            msgs.append({"role": h["role"], "content": h["content"][:1500]})
        msgs.append({"role": "user", "content": f"Sources from \"{doc.name}\":\n{ctx}\n\nQuestion: {question}"})
        txt = self.llm.chat(msgs, tier="deep" if deep else "main", temperature=0.2, max_tokens=4000 if not deep else 8000)
        txt = re.sub(r"[【\[]\s*p\.?\s*(\d+)\s*[】\]]", r"[p.\1]", txt)  # normalise 【p.4】 -> [p.4]
        eng = f"{self.s.deep_model if deep else self.s.model} · retrieval: {retriever.mode}"
        return Answer(text=txt, sources=sources + list(web or []), engine=eng)
