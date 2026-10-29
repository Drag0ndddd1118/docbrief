# Devpost submission copy — Nebius × NVIDIA Global AI Hackathon

**Track:** Best Apps and Agents
**Deadline:** Fri Oct 30, 2026, 10:00 AM PT (1:00 PM ET)

## Project name
DocBrief

## Elevator pitch / tagline (≤ 200 chars)
Speed-read any research paper or annual report: summary, key points, page-cited answers in English or 中文, and a check that flags any number not actually in the PDF. Powered by NVIDIA Nemotron on Nebius.

## Inspiration
I study financial engineering, and most of my week is spent digging through 10-Ks, earnings decks and arXiv papers. "Chat with your PDF" tools are fast but they quietly invent numbers — which is unacceptable when the number is revenue guidance. I wanted a reader I could trust: fast like an LLM, but with receipts. As a bilingual student I also wanted to ask questions in Chinese about English documents.

## What it does
Upload a PDF (paper or financial report). DocBrief returns:
- a TL;DR and structured summary,
- key points and risks/limitations, each with its source page,
- a key-metrics table (revenue, margins, EPS, cash flow, guidance; or datasets/accuracy for papers) where **every value is verified against the raw PDF text** — anything not literally found is flagged "⚠️ not found — verify",
- a chat that answers in English or 中文 and cites the pages it used (expandable source passages),
- a one-click Markdown export of the brief.
Optional toggles: **Deep reasoning** (Nemotron Ultra) and **live web context** (Tavily).

## How we built it
- **Python + Streamlit** UI; PDF text via pypdf with page markers; page-aware chunking.
- **NVIDIA Nemotron open models on Nebius Token Factory** (OpenAI-compatible API): Nemotron 3 Super for analysis, metrics and grounded answers; Nemotron 3 Nano as a fast tier for the map step on long filings and for rewriting Chinese questions into English search terms; Nemotron 3 Ultra behind a "Deep reasoning" toggle.
- **Hybrid retrieval**: BM25 (with CJK bigrams) + Qwen3-Embedding-8B embeddings from Nebius, fused with Reciprocal Rank Fusion.
- **Map-reduce summarization** for long documents (Nano maps sections, Super reduces).
- **Metric grounding check** that cross-checks every model-reported number with the PDF text.
- **Robust structured output**: strips reasoning `<think>` blocks, extracts balanced JSON, retries once.
- **Offline mock mode** (extractive heuristics) so the app and the test suite run without a key; a test exercises the live code path with a fake LLM.
- Optional **Tavily** search for questions that go beyond the document.

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
- Runs fully offline for demos and CI; 10 passing tests.

## What we learned
Smaller, faster models (Nemotron Nano) are ideal for the map step and query rewriting, while the larger models should only see retrieved evidence. Verification beats prompting for factual reliability.

## What's next for DocBrief
Table/figure extraction from scanned filings (OCR), multi-document comparison (YoY, peer sets), XBRL cross-checks for filings, and exporting briefs straight to Notion / Excel.

## Built with
Python, Streamlit, NVIDIA Nemotron (Super / Nano / Ultra), Nebius Token Factory, Qwen3-Embedding, rank-bm25, pypdf, Tavily (optional), pytest

## Links (to fill in)
- Public GitHub repo: https://github.com/Drag0ndddd1118/docbrief  (**NOT YET CREATED/PUSHED** — needs `gh auth login` as Drag0ndddd1118; local commit is ready)
- Demo video: demo/docbrief_demo.mp4 (1:43, 1080p) · cover: demo/cover.png (upload to YouTube yourself; paste the link here)
- Demo video (YouTube, < 3 min): <TODO>
- Live demo URL (optional): <TODO>

## Feedback on Nebius / NVIDIA (if the form asks)
Token Factory's OpenAI-compatible endpoint made integration a few lines of code. It would help to have one page listing exact model IDs and which regional base URL serves each, since IDs and endpoints differ between models.
