# DocBrief — 3-minute demo video script

**Target length:** 2:40–2:55 (limit is 3:00). Record the screen at 1080p with voiceover; upload to YouTube as Public/Unlisted. Use no copyrighted music (silence or YouTube Audio Library).
**Before recording:** run in LIVE mode (`NEBIUS_API_KEY` set) so the badge says LIVE; have `samples/aurora_robotics_fy2025_report.pdf` ready; browser zoom ~110%; close other tabs.

| Time | Shot (screen) | Voiceover |
|---|---|---|
| 0:00–0:15 | Title card "DocBrief", then the empty app | "Reading a 10-K or a research paper takes hours — and chat-with-PDF tools often make up numbers. DocBrief is a speed-reader that shows its receipts, built on NVIDIA Nemotron running on Nebius Token Factory." |
| 0:15–0:30 | Sidebar: LIVE badge, language options, Deep reasoning toggle | "It's running live on Nebius. Nemotron Super does the analysis, Nemotron Nano handles fast steps, and Nemotron Ultra is available for deep reasoning." |
| 0:30–0:50 | Drag in the Aurora Robotics annual report; progress bar | "I'll upload an annual report. DocBrief reads the pages, and for long filings it maps sections with Nano and merges them with Super." |
| 0:50–1:20 | Summary tab: TL;DR, summary, risks with page tags; then Key points | "In seconds: a TL;DR, a structured summary, key points and risks — each tagged with the page it came from." |
| 1:20–1:55 | Key metrics tab; hover Check column; point at ✅ and any ⚠️ | "Here are the headline metrics — revenue, margins, EPS, cash flow, guidance. The important part is this column: every number the model reports is checked against the raw PDF text. If it isn't literally in the document, it's flagged for review. That's how you stop hallucinated financials." |
| 1:55–2:25 | Ask tab: click "What is the outlook or guidance?"; show answer and open Sources | "Now questions. The answer is grounded in retrieved passages and cites its pages. Retrieval combines BM25 with Nebius embeddings." |
| 2:25–2:45 | Type in Chinese: "公司2026财年的收入指引是多少？"; show Chinese answer with page citations | "I can ask in Chinese about an English document. Nano rewrites the question into search terms, and the answer comes back in Chinese with citations." |
| 2:45–2:55 | Toggle Deep reasoning; click Export brief; show GitHub URL on a closing card | "Switch on Deep reasoning for harder questions, export the brief as Markdown, and it's all open source under MIT. Thanks for watching." |

## Tips
- Rehearse once; keep the Chinese question pre-typed in a notes file to paste.
- If a live call is slow, trim the pause in editing rather than cutting the answer.
- Show the sample PDF is fictional in the description: "Sample documents are fictional."
- YouTube description: link repo + Nebius/NVIDIA mention.
