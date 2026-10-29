"""Pre-compute the public-demo showcase (analysis + Q&A + Tavily fact-check + embeddings) with the LIVE pipeline.

Usage:  python scripts/build_showcase.py            # needs NEBIUS_API_KEY and TAVILY_API_KEY in .env
Writes: showcase/nvidia_fy2026_mdna.json   (commit this file; it is what the hosted demo serves for free)
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docbrief.chunking import chunk_document  # noqa: E402
from docbrief.config import Settings  # noqa: E402
from docbrief.engine import get_engine  # noqa: E402
from docbrief.pdf_loader import load_pdf  # noqa: E402
from docbrief.showcase import SHOWCASE_FOCUS, SHOWCASE_JSON, SHOWCASE_PDF, to_cache_dict  # noqa: E402
from docbrief.tavily import make_search  # noqa: E402

FOCUS = SHOWCASE_FOCUS
QUESTIONS = [
    ("Who are NVIDIA's biggest customers, and how much of revenue do they represent?", "en"),
    ("Why did gross margin fall in fiscal 2026?", "en"),
    ("How much capital did NVIDIA return to shareholders through share repurchases and dividends in fiscal 2026?", "en"),
    ("英伟达2026财年的营收和毛利率是多少，同比变化如何？", "auto"),
]


def main() -> None:
    s = Settings.from_env()
    assert s.is_live and s.tavily_key, "needs NEBIUS_API_KEY and TAVILY_API_KEY"
    eng = get_engine(s)
    doc = load_pdf(SHOWCASE_PDF.read_bytes(), SHOWCASE_PDF.name)
    print("pages", doc.n_pages, "chars", doc.n_chars)
    if "--factcheck-only" in sys.argv:  # keep analysis/Q&A/embeddings from the existing cache, redo only the Tavily fact-check
        old = json.loads(SHOWCASE_JSON.read_text(encoding="utf-8"))
        from docbrief.showcase import analysis_from_dict

        a = analysis_from_dict(old["analysis"])
        fc = eng.fact_check(doc, a, make_search(s.tavily_key), lang="en", n=3, focus=FOCUS)
        for f in fc:
            print("FC:", f.verdict, "|", f.claim, "| web:", f.web_says[:200])
        old["factcheck"] = [asdict(f) for f in fc]
        SHOWCASE_JSON.write_text(json.dumps(old, ensure_ascii=False))
        print("updated fact-check only")
        return
    if "--qa-only" in sys.argv:  # redo Q&A only, reusing cached analysis + embeddings
        from docbrief.showcase import Showcase

        sc = Showcase.load()
        chunks = chunk_document(doc)
        r = eng.build_retriever(chunks, sc.matrix_for(chunks))
        print("retrieval:", r.mode, "chunks", len(chunks))
        old = json.loads(SHOWCASE_JSON.read_text(encoding="utf-8"))
        qa = []
        for q, lang in QUESTIONS:
            ans = eng.answer(doc, r, q, lang=lang)
            qa.append({"q": q, "answer": ans.text, "engine": ans.engine, "sources": [asdict(x) for x in ans.sources]})
            print("Q:", q, "\nA:", ans.text[:500].replace("\n", " "), "\n")
        old["qa"] = qa
        SHOWCASE_JSON.write_text(json.dumps(old, ensure_ascii=False))
        print("updated Q&A only")
        return
    a = eng.analyze(doc, lang="en")
    print("analysis:", a.tldr[:160], "| metrics", len(a.metrics), "flagged", sum(1 for m in a.metrics if m.verified is False))
    chunks = chunk_document(doc)
    r = eng.build_retriever(chunks)
    print("retrieval:", r.mode, "chunks", len(chunks))
    qa = []
    for q, lang in QUESTIONS:
        ans = eng.answer(doc, r, q, lang=lang)
        qa.append({"q": q, "answer": ans.text, "engine": ans.engine, "sources": [asdict(x) for x in ans.sources]})
        print("Q:", q, "\nA:", ans.text[:400].replace("\n", " "), "\n")
    fc = eng.fact_check(doc, a, make_search(s.tavily_key), lang="en", n=3, focus=FOCUS)
    for f in fc:
        print("FC:", f.verdict, "|", f.claim, "| web:", f.web_says[:140])
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "models": {"main": s.model, "fast": s.fast_model, "deep": s.deep_model, "embed": s.embed_model},
        "source": "NVIDIA Form 10-K FY2026 (SEC accession 0001045810-26-000021), Item 7 + 7A excerpt",
        "llm_calls": eng.llm.calls,
        "tokens": eng.llm.usage,
    }
    SHOWCASE_JSON.parent.mkdir(exist_ok=True)
    SHOWCASE_JSON.write_text(json.dumps(to_cache_dict(a, qa, fc, r.matrix, chunks, meta), ensure_ascii=False))
    print("wrote", SHOWCASE_JSON, SHOWCASE_JSON.stat().st_size // 1024, "KB", meta["llm_calls"], "calls", meta["tokens"])


if __name__ == "__main__":
    main()
