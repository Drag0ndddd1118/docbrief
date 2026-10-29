"""Fact-check with the web: Nemotron picks checkable claims → Tavily searches the live web → Nemotron reconciles PDF vs web."""
from __future__ import annotations

import json
from typing import Optional

from . import prompts
from .pdf_loader import Document
from .tavily import SearchFn
from .types import Analysis, FactCheck, Source

VERDICTS = ("consistent", "differs", "no_web_evidence")
MAX_DOC_CHARS = 60_000


def _claim_context(doc: Document, a: Analysis) -> str:
    text = doc.marked_text()
    if len(text) <= MAX_DOC_CHARS:
        return text
    # long document: use the page-annotated analysis instead of raw text
    brief = {
        "title": a.title, "summary": a.summary,
        "key_points": [{"text": p.text, "page": p.page} for p in a.key_points],
        "metrics": [{"name": m.name, "value": m.value, "period": m.period, "page": m.page} for m in a.metrics],
        "risks": [{"text": p.text, "page": p.page} for p in a.risks],
    }
    return json.dumps(brief, ensure_ascii=False)


def extract_claims(llm, doc: Document, a: Analysis, n: int = 3) -> list[dict]:
    d = llm.chat_json(
        [
            {"role": "system", "content": prompts.CLAIMS_SYSTEM.format(n=n)},
            {"role": "user", "content": f"Document: {doc.name}\n\n{_claim_context(doc, a)}"},
        ],
        tier="fast",
        max_tokens=6000,
    )
    out = []
    for c in (d.get("claims") or [])[:n]:
        if isinstance(c, dict) and c.get("claim") and c.get("query"):
            pg = c.get("page")
            out.append({"claim": str(c["claim"]), "query": str(c["query"]), "page": int(pg) if str(pg).isdigit() else None})
    return out


def run_fact_check(llm, doc: Document, a: Analysis, search: SearchFn, lang_name: str = "English", n: int = 3) -> list[FactCheck]:
    """Returns one FactCheck per claim (≤ n). `search(query, start_label)` is injected (Tavily in production, a fake in tests)."""
    claims = extract_claims(llm, doc, a, n)
    checks: list[FactCheck] = []
    nxt = 1
    for c in claims:
        try:
            srcs = search(c["query"], nxt)
        except Exception:
            srcs = []
        nxt += len(srcs)
        checks.append(FactCheck(claim=c["claim"], page=c["page"], query=c["query"], sources=srcs))
    if not checks:
        return []

    blocks = []
    for i, fc in enumerate(checks):
        pdf = f"[p.{fc.page}] " if fc.page else ""
        page_txt = ""
        if fc.page and 1 <= fc.page <= doc.n_pages:
            page_txt = doc.pages[fc.page - 1][:1200]
        web = "\n".join(f"[{s.label}] ({s.url}) {s.text[:600]}" for s in fc.sources) or "(no web results)"
        blocks.append(f"### Claim {i}\nDocument says {pdf}: {fc.claim}\nPage excerpt: {page_txt}\nSearch query: {fc.query}\nWeb snippets:\n{web}")
    try:
        d = llm.chat_json(
            [
                {"role": "system", "content": prompts.RECONCILE_SYSTEM + f"\nLanguage: {lang_name}."},
                {"role": "user", "content": "\n\n".join(blocks)},
            ],
            tier="main",
        )
        for r in d.get("results") or []:
            try:
                fc = checks[int(r.get("index"))]
            except Exception:
                continue
            v = str(r.get("verdict") or "").strip().lower()
            fc.verdict = v if v in VERDICTS else "no_web_evidence"
            fc.pdf_says = str(r.get("pdf_says") or "")
            fc.web_says = str(r.get("web_says") or "")
            fc.explanation = str(r.get("explanation") or "")
    except Exception as e:  # keep the web sources visible even if the judge call fails
        for fc in checks:
            fc.explanation = f"Web sources were found but the reconciliation step failed ({str(e)[:80]})."
    return checks
