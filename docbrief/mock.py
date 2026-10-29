"""Offline engine: deterministic, extractive, no network. Lets the app run and be demoed without an API key."""
from __future__ import annotations

import re
from collections import Counter
from typing import Optional

from .chunking import Chunk
from .metrics import detect_doc_type, regex_metrics, verify_metrics
from .pdf_loader import Document
from .retrieval import Retriever, STOP, tokenize
from .types import Analysis, Answer, Point, Source

_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")


def _sentences(doc: Document) -> list[tuple[int, str]]:
    out = []
    for pno, t in enumerate(doc.pages, 1):
        for s in _SPLIT.split(re.sub(r"\s*\n\s*", " ", t)):
            s = re.sub(r"\s+", " ", s).strip()
            if 40 <= len(s) <= 400 and sum(ch.isdigit() for ch in s) < 0.2 * len(s) and len(re.findall(r"[A-Za-z\u4e00-\u9fff]", s)) > 0.5 * len(s):
                out.append((pno, s))
    return out


def _rank(sents: list[tuple[int, str]], boost_numbers: bool) -> list[tuple[float, int]]:
    words = Counter(w for _, s in sents for w in tokenize(s) if w not in STOP and len(w) > 2)
    scored = []
    for i, (pno, s) in enumerate(sents):
        toks = [w for w in tokenize(s) if len(w) > 2]
        if not toks:
            continue
        sc = sum(words[w] for w in toks) / (len(toks) ** 0.6)
        if boost_numbers and re.search(r"\d", s):
            sc *= 1.25
        sc *= 1.0 + 0.3 / (1 + pno)  # mild early-page bonus
        scored.append((sc, i))
    return sorted(scored, reverse=True)


class MockEngine:
    name = "mock"

    def describe(self) -> str:
        return "Offline demo mode (extractive heuristics, no LLM)"

    def analyze(self, doc: Document, lang: str = "en", progress=None) -> Analysis:
        dtype = detect_doc_type(doc.full_text)
        sents = _sentences(doc)
        ranked = _rank(sents, boost_numbers=dtype == "financial_report")
        top = sorted(i for _, i in ranked[:5])
        summary = " ".join(sents[i][1] for i in top)
        first_lines = [l.strip() for l in doc.pages[0].splitlines() if l.strip()][:2]
        title = doc.meta_title or " — ".join(first_lines)[:140] or doc.name

        used_pages: Counter = Counter()
        kps: list[Point] = []
        for _, i in ranked:
            pno, s = sents[i]
            if used_pages[pno] >= 2 or any(s[:50] == k.text[:50] for k in kps):
                continue
            used_pages[pno] += 1
            kps.append(Point(s, pno))
            if len(kps) == 6:
                break
        kps.sort(key=lambda p: p.page or 0)

        risk_re = re.compile(r"\b(risk|adverse|uncertain|limitation|however|may not|could harm|exposure|challeng)", re.I)
        risks, seen = [], set()
        for pno, s in sents:
            if risk_re.search(s) and s[:50] not in seen:
                seen.add(s[:50])
                risks.append(Point(s, pno))
            if len(risks) == 4:
                break

        metrics = verify_metrics(regex_metrics(doc.pages), doc.full_text) if dtype != "research_paper" else []
        if dtype == "research_paper":
            qs = ["What problem does this paper address?", "What is the main method or contribution?", "What are the main results and limitations?"]
        else:
            qs = ["How did revenue and profit change versus last year?", "What are the biggest risks?", "What is the outlook or guidance?"]
        return Analysis(
            title=title,
            doc_type=dtype,
            tldr=(sents[top[0]][1][:220] if top else ""),
            summary=summary,
            key_points=kps,
            metrics=metrics,
            risks=risks,
            suggested_questions=qs,
            engine=self.describe(),
        )

    def build_retriever(self, chunks: list[Chunk]) -> Retriever:
        return Retriever(chunks, embedder=None)

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
        hits = retriever.search(question, k=5)
        sources = [Source(label=f"S{i}", page=c.page, text=c.text) for i, (c, _) in enumerate(hits, 1)]
        qtok = set(tokenize(question))
        cands = []
        for c, _ in hits:
            for s in _SPLIT.split(re.sub(r"\s*\n\s*", " ", c.text)):
                s = s.strip()
                if len(s) < 25:
                    continue
                ov = len(qtok & set(tokenize(s)))
                if ov:
                    cands.append((ov + (0.3 if re.search(r"\d", s) else 0), c.page, s))
        cands.sort(key=lambda x: -x[0])
        picked, seen = [], set()
        for _, pg, s in cands:
            if s[:40] in seen:
                continue
            seen.add(s[:40])
            picked.append(f"{s} [p.{pg}]")
            if len(picked) == 3:
                break
        if not picked:
            text = "I couldn't find anything in the document that answers this. (Offline mode matches keywords only — try rephrasing in the document's language, or add an API key for full Q&A.)"
        else:
            text = "\n\n".join(f"- {p}" for p in picked) + "\n\n*Offline mode: extractive answer built from the best-matching passages (no LLM).*"
        return Answer(text=text, sources=sources, engine=f"offline · retrieval: {retriever.mode}")
