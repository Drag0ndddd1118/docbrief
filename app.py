"""DocBrief — speed-read any paper or financial report. Powered by NVIDIA Nemotron on Nebius Token Factory."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from docbrief.chunking import chunk_document
from docbrief.config import Settings
from docbrief.engine import get_engine
from docbrief.pdf_loader import load_pdf
from docbrief.report import to_markdown
from docbrief.tavily import make_search, tavily_search

SAMPLES = {
    "📊 Sample: Aurora Robotics FY2025 report": Path("samples/aurora_robotics_fy2025_report.pdf"),
    "📄 Sample: Retrieval-augmented earnings paper": Path("samples/retrieval_augmented_earnings_forecasting_paper.pdf"),
}

st.set_page_config(page_title="DocBrief · Nemotron on Nebius", page_icon="📑", layout="wide")


@st.cache_resource
def settings_and_engine():
    s = Settings.from_env()
    return s, get_engine(s)


S, ENGINE = settings_and_engine()

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("## 📑 DocBrief")
    st.caption("Speed-read papers & financial reports. Grounded answers, page-cited.")
    if S.is_live:
        st.success("LIVE · Nebius Token Factory", icon="🟢")
        st.caption(f"**Main:** `{S.model.split('/')[-1]}`  \n**Fast:** `{S.fast_model.split('/')[-1]}`  \n**Deep:** `{S.deep_model.split('/')[-1]}`  \n**Embeddings:** `{S.embed_model.split('/')[-1]}`")
    else:
        st.warning("OFFLINE DEMO MODE · no API key set. Extractive heuristics only. Set `NEBIUS_API_KEY` for Nemotron-powered analysis.", icon="🟡")
    out_lang = st.radio("Answer language / 回答语言", ["Auto", "English", "中文"], horizontal=True, help="Auto = same language as your question")
    LANG = {"Auto": "auto", "English": "en", "中文": "zh"}[out_lang]
    deep = st.toggle("Deep reasoning (Nemotron Ultra)", value=False, disabled=not S.is_live, help="Slower, stronger model for hard analytical questions.")
    web = st.toggle("Add live web context (Tavily)", value=False, disabled=not (S.is_live and S.tavily_key), help="Needs TAVILY_API_KEY. Adds recent web snippets as extra sources.")
    st.divider()
    st.caption("Your PDF is processed in memory and only the relevant passages are sent to the model. Nothing is stored.")

st.title("📑 DocBrief")
st.markdown("Upload a **research paper** or **annual report** → get a summary, key points, verified metrics, and a chat that cites its pages.")

# ---------------------------------------------------------------- input
c1, c2 = st.columns([3, 2])
with c1:
    up = st.file_uploader("Upload a PDF", type=["pdf"], label_visibility="collapsed")
with c2:
    pick = st.selectbox("…or try a sample", ["—"] + list(SAMPLES), label_visibility="collapsed")

data, name = None, None
if up is not None:
    data, name = up.getvalue(), up.name
elif pick != "—" and SAMPLES[pick].exists():
    data, name = SAMPLES[pick].read_bytes(), SAMPLES[pick].name

if data is None:
    st.info("👆 Upload a PDF or choose a sample to begin. Works in English and Chinese questions (中文提问也可以).")
    st.stop()

def esc(t):
    """Streamlit renders $...$ as LaTeX; financial text is full of dollar signs."""
    return (t or "").replace("$", "\\$")


# ---------------------------------------------------------------- analyse (cached per document)
key = f"{name}:{len(data)}"
if st.session_state.get("doc_key") != key:
    try:
        doc = load_pdf(data, name)
    except Exception as e:
        st.error(f"Couldn't read this PDF: {e}")
        st.stop()
    bar = st.progress(0.0, text=f"Reading {doc.n_pages} pages…")
    try:
        analysis = ENGINE.analyze(doc, lang={"auto": "en"}.get(LANG, LANG), progress=lambda f, m: bar.progress(min(f, 0.99), text=m))
        chunks = chunk_document(doc)
        bar.progress(0.97, text="Indexing passages…")
        retriever = ENGINE.build_retriever(chunks)
    except Exception as e:
        bar.empty()
        st.error(f"Analysis failed: {e}")
        st.stop()
    bar.empty()
    st.session_state.update(doc_key=key, doc=doc, analysis=analysis, retriever=retriever, chat=[], n_chunks=len(chunks))

doc, A, R = st.session_state["doc"], st.session_state["analysis"], st.session_state["retriever"]

head1, head2 = st.columns([4, 1])
head1.subheader(esc(A.title))
head1.caption(f"{doc.name} · {doc.n_pages} pages · {st.session_state['n_chunks']} passages · type: **{A.doc_type.replace('_', ' ')}** · retrieval: {R.mode}")
head2.download_button("⬇ Export brief (.md)", to_markdown(A, st.session_state["chat"]), file_name=f"{Path(doc.name).stem}_brief.md", use_container_width=True)
for w in doc.warnings:
    st.warning(w)
if R.embed_error:
    st.caption(f"ℹ️ Embeddings unavailable ({R.embed_error[:90]}…) — using BM25 keyword retrieval.")

if A.tldr:
    st.info(f"**TL;DR** — {esc(A.tldr)}")

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
        rows = [
            {"Metric": m.name, "Value": m.value, "Period": m.period, "Page": m.page, "Check": {True: "✅ found in PDF", False: "⚠️ not found — verify", None: "—"}[m.verified], "Context": m.note}
            for m in A.metrics
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        n_bad = sum(1 for m in A.metrics if m.verified is False)
        st.caption("Every value is checked against the raw PDF text; anything the model reports that isn't literally in the document is flagged." + (f" **{n_bad} flagged.**" if n_bad else ""))

if view == V_WEB:
    st.markdown("**Don't just trust the PDF.** Nemotron picks the claims in this document that can be checked publicly (market size, growth rates, benchmarks, public-company facts), **Tavily** searches the live web for each one, and Nemotron reconciles what the PDF says with what the web says.")
    if not (S.is_live and S.tavily_key):
        st.info("Needs live mode and a `TAVILY_API_KEY` (see README).")
    else:
        fc_key = f"fc:{st.session_state['doc_key']}:{LANG}"
        if st.button("🌐 Fact-check key claims with Tavily", type="primary"):
            with st.spinner("Nemotron picks claims → Tavily searches the web → Nemotron reconciles…"):
                try:
                    st.session_state[fc_key] = ENGINE.fact_check(doc, A, make_search(S.tavily_key), lang={"auto": "en"}.get(LANG, LANG), n=3)
                except Exception as e:
                    st.session_state[fc_key] = None
                    st.error(f"Fact-check failed: {e}")
        res = st.session_state.get(fc_key)
        if res is not None and not res:
            st.caption("No claims in this document can be checked against public web sources (e.g. it only reports a private company's own results).")
        BADGE = {"consistent": ("✅ Consistent with the web", st.success), "differs": ("⚠️ Differs from the web", st.warning), "no_web_evidence": ("🔍 No web evidence found", st.info)}
        for fcx in res or []:
            label, box = BADGE.get(fcx.verdict, BADGE["no_web_evidence"])
            with st.container(border=True):
                box(f"**{label}**")
                st.markdown(f"**Claim**{' `p.' + str(fcx.page) + '`' if fcx.page else ''}: {esc(fcx.claim)}")
                c_pdf, c_web = st.columns(2)
                c_pdf.markdown("**📄 PDF says**  \n" + esc(fcx.pdf_says or "—"))
                c_web.markdown("**🌐 Web says**  \n" + esc(fcx.web_says or "—"))
                if fcx.explanation:
                    st.markdown("**Nemotron's reconciliation:** " + esc(fcx.explanation))
                if fcx.sources:
                    st.caption("Web sources (Tavily) · query: " + esc(fcx.query))
                    for w in fcx.sources:
                        st.markdown(f"- **[{w.label}]** [{esc(w.title or w.url)}]({w.url})")

if view == V_ASK:
    if A.suggested_questions and not st.session_state["chat"]:
        st.caption("Try one:")
        cols = st.columns(len(A.suggested_questions))
        for col, q in zip(cols, A.suggested_questions):
            if col.button(q, use_container_width=True):
                st.session_state["pending_q"] = q
    for turn in st.session_state["chat"]:
        with st.chat_message(turn["role"]):
            st.markdown(esc(turn["content"]))
            if turn.get("sources"):
                with st.expander(f"Sources ({len(turn['sources'])}) · {turn.get('engine', '')}"):
                    for s in turn["sources"]:
                        loc = f"p.{s.page}" if s.page else s.url
                        st.markdown(f"**[{loc}]** " + esc(f"{s.text[:600]}{'…' if len(s.text) > 600 else ''}"))
    q = st.chat_input("Ask anything about this document… (English or 中文)") or st.session_state.pop("pending_q", None)
    if q:
        hist = [{"role": t["role"], "content": t["content"]} for t in st.session_state["chat"]]
        st.session_state["chat"].append({"role": "user", "content": q})
        with st.chat_message("user"):
            st.markdown(esc(q))
        with st.chat_message("assistant"):
            with st.spinner("Searching the document…"):
                try:
                    web_src = tavily_search(f"{A.title} {q}", S.tavily_key) if (web and S.tavily_key) else None
                except Exception:
                    web_src = None
                try:
                    ans = ENGINE.answer(doc, R, q, history=hist, lang=LANG, deep=deep, web=web_src)
                except Exception as e:
                    st.error(f"Model call failed: {e}")
                    st.stop()
            st.markdown(esc(ans.text))
            with st.expander(f"Sources ({len(ans.sources)}) · {ans.engine}"):
                for s in ans.sources:
                    loc = f"p.{s.page}" if s.page else s.url
                    st.markdown(f"**[{loc}]** " + esc(f"{s.text[:600]}{'…' if len(s.text) > 600 else ''}"))
        st.session_state["chat"].append({"role": "assistant", "content": ans.text, "sources": ans.sources, "engine": ans.engine})

if view == V_SRC:
    pg = st.number_input("Page", 1, doc.n_pages, 1)
    st.text(doc.pages[pg - 1] or "(no extractable text on this page)")
