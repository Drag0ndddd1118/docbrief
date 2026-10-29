"""DocBrief — Ask any 10-K. Get the page. NVIDIA Nemotron on Nebius Token Factory + Tavily web fact-checking."""
from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from docbrief.chunking import chunk_document
from docbrief.config import Settings
from docbrief.engine import get_engine
from docbrief.guard import COST, DailyLedger, Limits, SessionQuota, validate_upload
from docbrief.pdf_loader import load_pdf
from docbrief.report import to_markdown
from docbrief.showcase import SHOWCASE_FOCUS, SHOWCASE_PDF, SHOWCASE_TITLE, Showcase, source_from_dict
from docbrief.tavily import make_search, tavily_search

ROOT = Path(__file__).resolve().parent
SAMPLES = {
    "📊 Aurora Robotics FY2025 report (synthetic)": ROOT / "samples" / "aurora_robotics_fy2025_report.pdf",
    "📄 Retrieval-augmented earnings paper": ROOT / "samples" / "retrieval_augmented_earnings_forecasting_paper.pdf",
}

st.set_page_config(page_title="DocBrief · Ask any 10-K. Get the page.", page_icon="📑", layout="wide")

CSS = """
<style>
.block-container {padding-top: 2.2rem; max-width: 1180px;}
.db-hero {padding: 2.2rem 0 .6rem 0;}
.db-eyebrow {display:inline-block; font-size:.78rem; letter-spacing:.08em; text-transform:uppercase; color:#7ee787; border:1px solid #238636; border-radius:999px; padding:.18rem .7rem; margin-bottom:1rem; background:rgba(46,160,67,.12);}
.db-h1 {font-size:3.6rem; line-height:1.05; font-weight:800; margin:0 0 .6rem 0; background:linear-gradient(90deg,#7ee787 0%,#56d4dd 60%,#a5d6ff 100%); -webkit-background-clip:text; background-clip:text; color:transparent;}
.db-sub {font-size:1.25rem; color:#c9d1d9; margin-bottom:.4rem;}
.db-sub b {color:#fff;}
.db-cards {display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin:1.4rem 0 1.2rem 0;}
.db-card {background:#161b22; border:1px solid #30363d; border-radius:14px; padding:1.1rem 1.2rem;}
.db-card .ic {font-size:1.7rem;}
.db-card h4 {margin:.4rem 0 .3rem 0; font-size:1.05rem; color:#fff;}
.db-card p {margin:0; color:#9da7b3; font-size:.92rem; line-height:1.45;}
.db-stack {color:#8b949e; font-size:.85rem; margin-top:.6rem;}
.db-stack code {background:#21262d; color:#c9d1d9; padding:.1rem .4rem; border-radius:5px;}
.db-tldr {background:linear-gradient(135deg,rgba(46,160,67,.16),rgba(56,139,253,.10)); border:1px solid #2ea04366; border-radius:14px; padding:1rem 1.25rem; margin:.4rem 0 1rem 0; font-size:1.08rem; color:#f0f6fc;}
.db-tldr b {color:#7ee787;}
.db-grid {display:grid; grid-template-columns:repeat(3,1fr); gap:.8rem;}
.db-metric {background:#161b22; border:1px solid #30363d; border-radius:12px; padding:.8rem 1rem;}
.db-metric.bad {border-color:#d29922;}
.db-metric .n {color:#9da7b3; font-size:.8rem; text-transform:uppercase; letter-spacing:.04em;}
.db-metric .v {color:#fff; font-size:1.7rem; font-weight:700; margin:.1rem 0;}
.db-metric .p {color:#9da7b3; font-size:.8rem;}
.db-metric .note {color:#8b949e; font-size:.78rem; margin-top:.35rem; line-height:1.35;}
.chip {display:inline-block; font-size:.72rem; padding:.05rem .5rem; border-radius:999px; background:#21262d; color:#c9d1d9; border:1px solid #30363d; margin-right:.3rem;}
.chip.ok {background:rgba(46,160,67,.15); color:#7ee787; border-color:#238636;}
.chip.warn {background:rgba(210,153,34,.15); color:#e3b341; border-color:#9e6a03;}
.chip.pre {background:rgba(56,139,253,.15); color:#79c0ff; border-color:#1f6feb;}
.db-fc {background:#161b22; border:1px solid #30363d; border-radius:14px; padding:1rem 1.2rem; margin-bottom:1rem; border-left-width:5px;}
.db-fc.consistent {border-left-color:#2ea043;}
.db-fc.differs {border-left-color:#d29922;}
.db-fc.no_web_evidence {border-left-color:#58a6ff;}
.db-fc .verdict {font-weight:700; font-size:.95rem;}
.db-fc .claim {font-size:1.05rem; color:#fff; margin:.4rem 0 .8rem 0;}
.db-two {display:grid; grid-template-columns:1fr 1fr; gap:.8rem;}
.db-box {background:#0d1117; border:1px solid #30363d; border-radius:10px; padding:.7rem .9rem; font-size:.92rem; color:#c9d1d9;}
.db-box .lbl {font-size:.74rem; text-transform:uppercase; letter-spacing:.05em; color:#8b949e; margin-bottom:.25rem;}
.db-why {margin-top:.8rem; color:#c9d1d9; font-size:.92rem;}
.db-src a {color:#79c0ff; text-decoration:none;}
.db-src {margin-top:.6rem; font-size:.84rem; color:#8b949e;}
@media (max-width: 800px) {.db-cards,.db-grid,.db-two {grid-template-columns:1fr;} .db-h1 {font-size:2.5rem;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def h(t) -> str:
    """HTML-escape (and neutralise `$`, which Streamlit would otherwise treat as LaTeX)."""
    return html.escape(str(t or "")).replace("$", "&#36;")


def esc(t) -> str:
    return (t or "").replace("$", "\\$")


def block(s: str) -> None:
    """Render an HTML block (no blank lines, so Markdown does not break it up)."""
    st.markdown("".join(line.strip() for line in s.splitlines()), unsafe_allow_html=True)


@st.cache_resource
def settings_and_engine():
    s = Settings.from_env()
    return s, get_engine(s)


@st.cache_resource
def shared_ledger(budget: int) -> DailyLedger:
    return DailyLedger(budget)


@st.cache_resource
def load_showcase():
    return Showcase.load()


S, ENGINE = settings_and_engine()
LIMITS = Limits.from_env()
LEDGER = shared_ledger(LIMITS.daily_budget)
QUOTA = SessionQuota(st.session_state, LIMITS, LEDGER)
SHOW = load_showcase()
LIVE_WEB = S.is_live and bool(S.tavily_key)
ss = st.session_state
ss.setdefault("mode", None)
ss.setdefault("up_n", 0)


def reset() -> None:
    for k in ("mode", "doc_key", "doc", "analysis", "retriever", "chat", "n_chunks", "precomputed"):
        ss.pop(k, None)
    for k in [k for k in ss if str(k).startswith("fc:")]:
        ss.pop(k, None)
    ss["up_n"] += 1


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## 📑 DocBrief")
    st.caption("AI that **cites**, **verifies**, and **fact-checks**.")
    if S.is_live:
        st.success("LIVE · Nebius Token Factory", icon="🟢")
        st.caption(
            f"**Main:** `{S.model.split('/')[-1]}`  \n**Fast:** `{S.fast_model.split('/')[-1]}`  \n"
            f"**Deep:** `{S.deep_model.split('/')[-1]}`  \n**Embeddings:** `{S.embed_model.split('/')[-1]}`  \n"
            f"**Web:** Tavily {'✅' if S.tavily_key else '— (no key)'}"
        )
    else:
        st.warning("OFFLINE MODE · no API key. The pre-computed 10-K demo still works; uploads use extractive heuristics.", icon="🟡")
    if ss["mode"] is not None:
        if st.button("← Back to start", use_container_width=True):
            reset()
            st.rerun()
    out_lang = st.radio("Answer language / 回答语言", ["Auto", "English", "中文"], horizontal=True, help="Auto = same language as your question")
    LANG = {"Auto": "auto", "English": "en", "中文": "zh"}[out_lang]
    deep = st.toggle("Deep reasoning (Nemotron Ultra)", value=False, disabled=not S.is_live, help=f"Slower, stronger model. Limited to {LIMITS.max_deep_questions} per session.")
    web = st.toggle("Add live web context (Tavily)", value=False, disabled=not LIVE_WEB, help="Adds recent web snippets as extra sources to your next live question (counts as a fact-check).")
    if S.is_live:
        st.divider()
        st.markdown("**Fair-use meter**")
        st.caption("This demo runs on a shared API budget. Pre-computed results are always free.")
        for label, kind in (("Analyses", "analysis"), ("Questions", "question"), ("Deep questions", "deep"), ("Fact-checks", "factcheck")):
            cap = QUOTA.cap(kind)
            st.progress(min(1.0, QUOTA.used(kind) / cap) if cap else 1.0, text=f"{label}: {QUOTA.used(kind)}/{cap}")
        rem = LEDGER.remaining() / max(1, LIMITS.daily_budget)
        st.caption(f"Shared daily budget: **{rem:.0%}** left (resets 00:00 UTC)")
    st.divider()
    st.caption("PDFs are processed in memory; only the relevant passages are sent to the model. Nothing is stored.")


# ---------------------------------------------------------------- loading
def start_showcase() -> None:
    doc = load_pdf(SHOWCASE_PDF.read_bytes(), SHOWCASE_PDF.name)
    chunks = chunk_document(doc)
    retriever = ENGINE.build_retriever(chunks, SHOW.matrix_for(chunks))
    ss.update(mode="showcase", doc_key="showcase", doc=doc, analysis=SHOW.analysis, retriever=retriever, chat=[], n_chunks=len(chunks), precomputed=True)
    ss["fc:showcase"] = {"results": SHOW.factcheck, "cached": True}
    ss["view"] = "Summary"


def start_upload(data: bytes, name: str) -> None:
    why = validate_upload(len(data), None, LIMITS)
    if why:
        st.error(why)
        return
    try:
        doc = load_pdf(data, name)
    except Exception as e:
        st.error(f"Couldn't read this PDF: {e}")
        return
    why = validate_upload(len(data), doc.n_pages, LIMITS)
    if why:
        st.error(why)
        return
    if S.is_live:
        why = QUOTA.spend("analysis")
        if why:
            st.error(why)
            return
    bar = st.progress(0.0, text=f"Reading {doc.n_pages} pages…")
    try:
        analysis = ENGINE.analyze(doc, lang={"auto": "en"}.get(LANG, LANG), progress=lambda f, m: bar.progress(min(f, 0.99), text=m), **({"max_chars": LIMITS.max_analysis_chars} if S.is_live else {}))
        chunks = chunk_document(doc)
        if len(chunks) > LIMITS.max_chunks:
            chunks = chunks[: LIMITS.max_chunks]
            doc.warnings.append(f"Very long document: Q&A indexes the first {LIMITS.max_chunks} passages (cost cap).")
        bar.progress(0.97, text="Indexing passages…")
        retriever = ENGINE.build_retriever(chunks)
    except Exception as e:
        bar.empty()
        st.error(f"Analysis failed: {e}")
        return
    bar.empty()
    ss.update(mode="upload", doc_key=f"{name}:{len(data)}", doc=doc, analysis=analysis, retriever=retriever, chat=[], n_chunks=len(chunks), precomputed=False)
    ss["view"] = "Summary"


# ---------------------------------------------------------------- landing
if ss["mode"] is None:
    block(
        f"""<div class="db-hero"><span class="db-eyebrow">NVIDIA Nemotron · Nebius Token Factory · Tavily</span>
        <div class="db-h1">Ask any 10-K.<br>Get the page.</div>
        <div class="db-sub"><b>AI that cites, verifies, and fact-checks.</b> Upload an annual report or a research paper: get a summary, numbers checked against the PDF, and answers that point to the exact page, then see what the live web says about its claims.</div></div>"""
    )
    block(
        """<div class="db-cards">
        <div class="db-card"><div class="ic">📍</div><h4>Cites every answer</h4><p>Hybrid search (BM25 + Qwen3 embeddings) finds the right passages. Each claim in the answer carries a page tag you can open.</p></div>
        <div class="db-card"><div class="ic">✅</div><h4>Verifies every number</h4><p>Each metric Nemotron extracts is re-checked against the raw PDF text. Anything not literally in the document gets flagged.</p></div>
        <div class="db-card"><div class="ic">🌐</div><h4>Fact-checks against the live web</h4><p>Nemotron picks checkable claims, Tavily searches the web, Nemotron reconciles PDF vs web with source links.</p></div></div>"""
    )
    b1, b2 = st.columns([3, 2])
    with b1:
        if SHOW is not None:
            if st.button("▶  Try the preloaded NVIDIA 10-K  (instant · no API cost)", type="primary", use_container_width=True):
                start_showcase()
                st.rerun()
            st.caption(f"Real SEC filing: **{SHOWCASE_TITLE}** (11-page excerpt, source: sec.gov). Pre-computed with Nemotron + Tavily; you can still ask it new questions live.")
    with b2:
        st.markdown("**…or analyse your own PDF**")
        up = st.file_uploader("Upload a PDF", type=["pdf"], label_visibility="collapsed", key=f"uploader_{ss['up_n']}", help=f"Up to {LIMITS.max_pdf_mb} MB / {LIMITS.max_pages} pages")
        st.caption(f"Limits on this public demo: {LIMITS.max_pdf_mb} MB, {LIMITS.max_pages} pages, {LIMITS.max_analyses} analyses and {LIMITS.max_questions} questions per session.")
        pick = st.selectbox("…or a small synthetic sample", ["—"] + list(SAMPLES), label_visibility="collapsed")
        if pick != "—" and SAMPLES[pick].exists() and st.button("Analyse sample", use_container_width=True):
            start_upload(SAMPLES[pick].read_bytes(), SAMPLES[pick].name)
            if ss["mode"]:
                st.rerun()
        if up is not None:
            start_upload(up.getvalue(), up.name)
            if ss["mode"]:
                st.rerun()
    block(
        """<div class="db-stack">Built with <code>nemotron-3-nano</code> (claims, fast steps) · <code>nemotron-3-super</code> (analysis, Q&amp;A, reconciliation) · <code>nemotron-3-ultra</code> (deep reasoning) · <code>Qwen3-Embedding-8B</code> (retrieval) · Tavily Search · Streamlit</div>"""
    )
    st.stop()

# ---------------------------------------------------------------- analysis view
doc, A, R = ss["doc"], ss["analysis"], ss["retriever"]
is_show = ss["mode"] == "showcase"

head1, head2 = st.columns([4, 1])
head1.subheader(esc(SHOWCASE_TITLE if is_show else A.title))
badge = '<span class="chip pre">⚡ pre-computed with Nemotron + Tavily</span>' if is_show else '<span class="chip ok">live analysis</span>'
block(f"""<div style="color:#9da7b3;font-size:.9rem">{badge} {h(doc.name)} · {doc.n_pages} pages · {ss['n_chunks']} passages · type: <b>{h(A.doc_type.replace('_', ' '))}</b> · retrieval: {h(R.mode)}</div>""")
head2.download_button("⬇ Export brief (.md)", to_markdown(A, ss["chat"]), file_name=f"{Path(doc.name).stem}_brief.md", use_container_width=True)
for w in doc.warnings:
    st.warning(w)
if R.embed_error:
    st.caption(f"ℹ️ Embeddings unavailable ({R.embed_error[:90]}…) — using BM25 keyword retrieval.")
if A.tldr:
    block(f"""<div class="db-tldr"><b>TL;DR</b> — {h(A.tldr)}</div>""")

VIEWS = ["Summary", "Key points", "Key metrics", "🌐 Fact-check with the web", "💬 Ask the document", "Source pages"]
V_SUM, V_PTS, V_MET, V_WEB, V_ASK, V_SRC = VIEWS
view = st.radio("View", VIEWS, horizontal=True, label_visibility="collapsed", key="view")

if view == V_SUM:
    st.markdown(esc(A.summary))
    if A.risks:
        st.markdown("#### ⚠️ Risks / limitations" if A.doc_type != "research_paper" else "#### ⚠️ Limitations")
        for p in A.risks:
            st.markdown(f"- {esc(p.text)}" + (f" `p.{p.page}`" if p.page else ""))

if view == V_PTS:
    for p in A.key_points:
        st.markdown(f"- {esc(p.text)}" + (f" `p.{p.page}`" if p.page else ""))

if view == V_MET:
    if not A.metrics:
        st.caption("No headline metrics detected for this document.")
    else:
        cards = []
        for m in A.metrics:
            vb = {True: '<span class="chip ok">✓ found in PDF</span>', False: '<span class="chip warn">⚠ not found — verify</span>', None: ""}[m.verified]
            pg = f'<span class="chip">p.{m.page}</span>' if m.page else ""
            cards.append(
                f'<div class="db-metric{" bad" if m.verified is False else ""}"><div class="n">{h(m.name)}</div><div class="v">{h(m.value)}</div>'
                f'<div class="p">{h(m.period)}</div><div style="margin-top:.4rem">{pg}{vb}</div>'
                + (f'<div class="note">{h(m.note)}</div>' if m.note else "")
                + "</div>"
            )
        block('<div class="db-grid">' + "".join(cards) + "</div>")
        n_bad = sum(1 for m in A.metrics if m.verified is False)
        st.caption("Every value is re-checked against the raw PDF text; anything the model reports that isn't literally in the document is flagged." + (f" **{n_bad} flagged.**" if n_bad else " **None flagged.**"))
        with st.expander("Table view"):
            st.dataframe(
                [{"Metric": m.name, "Value": m.value, "Period": m.period, "Page": m.page, "Check": {True: "✅ found in PDF", False: "⚠️ not found", None: "—"}[m.verified], "Context": m.note} for m in A.metrics],
                use_container_width=True,
                hide_index=True,
            )

VERDICT = {
    "consistent": ("✅ Consistent with the web", "consistent"),
    "differs": ("⚠️ Differs from the web", "differs"),
    "no_web_evidence": ("🔍 No web evidence found", "no_web_evidence"),
}

if view == V_WEB:
    st.markdown(
        "**Don't just trust the PDF.** Nemotron picks the claims that can be checked publicly, **Tavily** searches the live web for each one, "
        "and Nemotron reconciles what the document says with what the web says, with source links."
    )
    fc_key = f"fc:{ss['doc_key']}"
    if LIVE_WEB:
        left = QUOTA.left("factcheck")
        label = "🔄 Re-run live with Tavily" if (is_show and ss.get(fc_key)) else "🌐 Fact-check key claims with Tavily"
        if st.button(f"{label}  ({left} left this session)", type="primary" if not ss.get(fc_key) else "secondary", disabled=left <= 0):
            why = QUOTA.spend("factcheck")
            if why:
                st.error(why)
            else:
                with st.spinner("Nemotron picks claims → Tavily searches the web → Nemotron reconciles…"):
                    try:
                        res = ENGINE.fact_check(doc, A, make_search(S.tavily_key), lang={"auto": "en"}.get(LANG, LANG), n=3, **({"focus": SHOWCASE_FOCUS} if is_show else {}))
                        ss[fc_key] = {"results": res, "cached": False}
                    except Exception as e:
                        st.error(f"Fact-check failed: {e}")
    elif not is_show:
        st.info("Live fact-checking needs a Nebius key and a `TAVILY_API_KEY` on the server.")
    entry = ss.get(fc_key)
    if entry is not None:
        res = entry["results"]
        if entry["cached"]:
            block('<span class="chip pre">⚡ pre-computed with the live pipeline (Tavily + Nemotron)</span>')
        if not res:
            st.caption("No claims in this document can be checked against public web sources (e.g. it only reports a private company's own results).")
        for f in res:
            label, cls = VERDICT.get(f.verdict, VERDICT["no_web_evidence"])
            srcs = " · ".join(f'<a href="{h(w.url)}" target="_blank">[{h(w.label)}] {h(w.title or w.url)[:70]}</a>' for w in f.sources)
            block(
                f"""<div class="db-fc {cls}"><div class="verdict">{label}{f' <span class="chip">p.{f.page}</span>' if f.page else ''}</div>
                <div class="claim">“{h(f.claim)}”</div>
                <div class="db-two"><div class="db-box"><div class="lbl">📄 PDF says</div>{h(f.pdf_says or '—')}</div>
                <div class="db-box"><div class="lbl">🌐 Web says</div>{h(f.web_says or '—')}</div></div>
                <div class="db-why"><b>Nemotron's reconciliation:</b> {h(f.explanation)}</div>
                <div class="db-src">Tavily query: <i>{h(f.query)}</i><br>{srcs}</div></div>"""
            )

if view == V_ASK:
    cached_qs = SHOW.questions if is_show and SHOW else []
    suggestions = cached_qs if is_show else A.suggested_questions
    if suggestions and not ss["chat"]:
        st.caption("Try one" + (" (pre-computed, instant):" if is_show else ":"))
        cols = st.columns(len(suggestions))
        for col, q in zip(cols, suggestions):
            if col.button(q, use_container_width=True):
                ss["pending_q"] = q
    for turn in ss["chat"]:
        with st.chat_message(turn["role"]):
            st.markdown(esc(turn["content"]))
            if turn.get("cached"):
                st.caption("⚡ pre-computed by Nemotron")
            if turn.get("sources"):
                with st.expander(f"Sources ({len(turn['sources'])}) · {turn.get('engine', '')}"):
                    for s in turn["sources"]:
                        loc = f"p.{s.page}" if s.page else s.url
                        st.markdown(f"**[{loc}]** " + esc(f"{s.text[:600]}{'…' if len(s.text) > 600 else ''}"))
    placeholder = "Ask the NVIDIA 10-K anything… (English or 中文)" if is_show else "Ask anything about this document… (English or 中文)"
    q = st.chat_input(placeholder, max_chars=LIMITS.max_question_chars) or ss.pop("pending_q", None)
    if q:
        q = q.strip()[: LIMITS.max_question_chars]
        hist = [{"role": t["role"], "content": t["content"]} for t in ss["chat"]]
        ss["chat"].append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(esc(q))
        hit = SHOW.find_answer(q) if is_show and SHOW else None
        with st.chat_message("assistant"):
            if hit:  # served from the pre-computed cache: free and instant
                ans_text, ans_src, ans_engine, from_cache = hit["answer"], [source_from_dict(s) for s in hit["sources"]], hit.get("engine", ""), True
                st.markdown(esc(ans_text))
                st.caption("⚡ pre-computed by Nemotron")
                with st.expander(f"Sources ({len(ans_src)}) · {ans_engine}"):
                    for s in ans_src:
                        st.markdown(f"**[p.{s.page}]** " + esc(f"{s.text[:600]}{'…' if len(s.text) > 600 else ''}"))
            else:
                kind = "deep" if (deep and S.is_live) else "question"
                why = QUOTA.spend(kind) if S.is_live else None
                if why:
                    st.warning(why)
                    ss["chat"].pop()
                    st.stop()
                web_src = None
                if web and LIVE_WEB and QUOTA.spend("factcheck") is None:
                    try:
                        web_src = tavily_search(f"{A.title} {q}", S.tavily_key)
                    except Exception:
                        web_src = None
                with st.spinner("Searching the document…"):
                    try:
                        ans = ENGINE.answer(doc, R, q, history=hist, lang=LANG, deep=deep and S.is_live, web=web_src)
                    except Exception as e:
                        st.error(f"Model call failed: {e}")
                        ss["chat"].pop()
                        st.stop()
                ans_text, ans_src, ans_engine, from_cache = ans.text, ans.sources, ans.engine, False
                st.markdown(esc(ans_text))
                with st.expander(f"Sources ({len(ans_src)}) · {ans_engine}"):
                    for s in ans_src:
                        loc = f"p.{s.page}" if s.page else s.url
                        st.markdown(f"**[{loc}]** " + esc(f"{s.text[:600]}{'…' if len(s.text) > 600 else ''}"))
        ss["chat"].append({"role": "assistant", "content": ans_text, "sources": ans_src, "engine": ans_engine, "cached": from_cache})

if view == V_SRC:
    pg = st.number_input("Page", 1, doc.n_pages, 1)
    st.text(doc.pages[pg - 1] or "(no extractable text on this page)")
