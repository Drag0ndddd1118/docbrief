# Devpost submission copy — Nebius × NVIDIA Global AI Hackathon

**Track:** Best Apps and Agents
**Deadline:** Fri Oct 30, 2026, 10:00 AM PT (1:00 PM ET)

## Project name
DocBrief

## Elevator pitch / tagline (≤ 200 chars)
Ask any 10-K. Get the page. AI that cites every answer, verifies every number against the PDF, and fact-checks claims on the live web (Tavily). NVIDIA Nemotron on Nebius.

## Inspiration
I study financial engineering, and most of my week is spent digging through 10-Ks, earnings decks and arXiv papers. "Chat with your PDF" tools are fast but they quietly invent numbers — which is unacceptable when the number is revenue guidance. I wanted a reader I could trust: fast like an LLM, but with receipts. As a bilingual student I also wanted to ask questions in Chinese about English documents.

## What it does
The hosted demo opens on a **real NVIDIA FY2026 10-K excerpt (SEC EDGAR)** whose analysis, Q&A and web fact-check are pre-computed, so judges get an instant, zero-cost, no-signup experience, and can still ask new questions live or upload their own PDF within fair-use limits (per-session quotas, size/page caps, and a shared daily budget protect the API key).

Upload a PDF (paper or financial report). DocBrief returns:
- a TL;DR and structured summary,
- key points and risks/limitations, each with its source page,
- a key-metrics table (revenue, margins, EPS, cash flow, guidance; or datasets/accuracy for papers) where **every value is verified against the raw PDF text** — anything not literally found is flagged "⚠️ not found — verify",
- a chat that answers in English or 中文 and cites the pages it used (expandable source passages),
- **🌐 Fact-check with the web (Tavily)**: Nemotron picks the claims in the document that can be checked publicly (market size, growth rates, benchmarks, public-company facts), Tavily searches the live web for each, and Nemotron reconciles *PDF vs web* into a verdict — ✅ consistent, ⚠️ differs, 🔍 no web evidence — with the PDF page and the clickable web sources side by side,
- a one-click Markdown export of the brief.
Optional toggles: **Deep reasoning** (Nemotron Ultra) and **live web context in Q&A** (Tavily).

## How we built it
- **Python + Streamlit** UI; PDF text via pypdf with page markers; page-aware chunking.
- **NVIDIA Nemotron open models on Nebius Token Factory** (OpenAI-compatible API): Nemotron 3 Super for analysis, metrics and grounded answers; Nemotron 3 Nano as a fast tier for the map step on long filings and for rewriting Chinese questions into English search terms; Nemotron 3 Ultra behind a "Deep reasoning" toggle.
- **Hybrid retrieval**: BM25 (with CJK bigrams) + Qwen3-Embedding-8B embeddings from Nebius, fused with Reciprocal Rank Fusion.
- **Map-reduce summarization** for long documents (Nano maps sections, Super reduces).
- **Tavily Search API (runtime call, core feature)**: the *Fact-check with the web* view calls Tavily live for every claim Nemotron Nano selects, de-duplicates and labels the results W1…Wn, and Nemotron Super reconciles them against the cited PDF page. Tavily also feeds optional web snippets into Q&A answers (cited as [W1]). Without a Tavily key the app still runs; with one, the web is part of the pipeline, not decoration.
- **Metric grounding check** that cross-checks every model-reported number with the PDF text.
- **Robust structured output**: strips reasoning `<think>` blocks, extracts balanced JSON, retries once.
- **Offline mock mode** (extractive heuristics) so the app and the test suite run without a key; a test exercises the live code path with a fake LLM.
- **Tavily** live web search for the fact-check view and for questions that go beyond the document.

## Challenges we ran into
- Reasoning models wrap output in `<think>` blocks and sometimes return near-JSON; we built tolerant parsing and a retry.
- Chinese questions don't match English passages in keyword search — solved with a Nano query-rewrite step plus CJK bigrams and dense embeddings.
- Hallucinated numbers: solved by making the PDF the verifier, not the model.
- Long filings exceed a comfortable single-pass context, so we added map-reduce with a cheaper model on the map side.
- Making the demo reliable: a deterministic offline mode and fully fictional sample documents.

## Accomplishments that we're proud of
- Every number in the metrics table is machine-verified against the source.
- Seamless bilingual Q&A over English documents.
- Uses three Nemotron tiers for the right job each (cost/latency-aware routing).
- Runs fully offline for demos and CI; 27 passing tests (including the Tavily path with a fake client, the abuse-protection guard and a Streamlit AppTest smoke test).

## What we learned
Smaller, faster models (Nemotron Nano) are ideal for the map step and query rewriting, while the larger models should only see retrieved evidence. Verification beats prompting for factual reliability.

## What's next for DocBrief
Table/figure extraction from scanned filings (OCR), multi-document comparison (YoY, peer sets), XBRL cross-checks for filings, and exporting briefs straight to Notion / Excel.

## Built with
Python, Streamlit, NVIDIA Nemotron (Super / Nano / Ultra), Nebius Token Factory, Qwen3-Embedding, rank-bm25, pypdf, Tavily Search API, pytest

## Links (to fill in)
- Live demo (Streamlit Community Cloud): https://docbrief.streamlit.app  (replace after deploy; add it to the README too)
- Demo video v3 (2:33, 1080p, real NVIDIA 10-K, includes the Tavily fact-check): `demo/docbrief_demo_v3.mp4` (upload to YouTube and replace the link below)
- Public GitHub repo: https://github.com/Drag0ndddd1118/docbrief  
- Previous demo video (v2, YouTube): https://youtu.be/0WsNXSGSV2Y

## Feedback on Nebius / NVIDIA (if the form asks)
Token Factory's OpenAI-compatible endpoint made integration a few lines of code. It would help to have one page listing exact model IDs and which regional base URL serves each, since IDs and endpoints differ between models.

## Best Use of Tavily — answer

DocBrief calls the Tavily Search API at runtime in its **🌐 Fact-check with the web** view (`docbrief/tavily.py`, `docbrief/factcheck.py`). Nemotron Nano picks up to three claims in the uploaded PDF that can be checked publicly (market size, growth rates, benchmarks, public-company facts); Tavily searches the live web for each one; Nemotron Super then reconciles "PDF says" vs "web says" and returns a verdict (consistent / differs / no web evidence) with [p.N] PDF citations next to [W#] web-source links. Tavily also optionally adds live web context to chat answers. In our live test on a sample report, a claimed 6% market CAGR was flagged as differing from web sources (about 11–19%), while an e-commerce-share claim was confirmed. The Tavily client is injectable, so the whole path is covered by offline tests with a fake client.
