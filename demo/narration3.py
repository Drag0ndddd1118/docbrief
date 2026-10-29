"""Generate per-scene narration (edge-tts, en-US-AndrewNeural) + word timings."""
import asyncio, json, edge_tts
VOICE = "en-US-AndrewNeural"
SCENES = [
 ("s0", "Who are NVIDIA's biggest customers? One customer is twenty-two percent of revenue. Another, fourteen. Cited to page seven, from a real ten-K, instantly."),
 ("s1", "I'm Qin, and this is DocBrief: ask any ten-K, get the page. Chat-with-PDF tools are fast, but they quietly invent numbers. DocBrief is AI that cites, verifies, and fact-checks."),
 ("s2", "It runs on NVIDIA Nemotron, served by Nebius Token Factory. Nano handles the fast steps, Super does the analysis, Ultra is there for deep reasoning, and Qwen embeddings power retrieval. Tavily adds live web search. And for a public demo, a real filing is preloaded, so anyone can try it at no cost."),
 ("s3", "This is a real SEC filing: NVIDIA's fiscal 2026 ten-K, the MD&A section. One click loads the analysis: a one line takeaway, a structured summary, and risks, each tagged with its page."),
 ("s4", "Every number on these cards is re-checked against the raw text of the PDF. If the model reports a figure that isn't literally in the document, it gets flagged. Revenue, two hundred sixteen billion, up sixty-five percent, found on page three."),
 ("s5", "But a PDF can agree with itself and still be wrong about the world. So Nemotron Nano picks the claims that can be checked publicly, Tavily searches the live web, and Nemotron Super reconciles the PDF against what it found."),
 ("s6", "Here it is running live. Every claim gets a verdict, with web sources. Revenue, two hundred sixteen billion: confirmed by NVIDIA's own results. The four and a half billion dollar H20 charge: confirmed. If the web disagreed, it would say so, with links."),
 ("s7", "Now I can ask anything. This question wasn't precomputed, so it's a live call. Hybrid search finds the right passages, and Nemotron Super answers with the page. The government required a license for H20 exports to China, triggering a four and a half billion dollar charge."),
 ("s8", "And I can ask in Chinese about an English filing, and get a cited answer in Chinese."),
 ("s9", "Because this demo is public, it's built to be safe. Per-session quotas, a PDF size and page cap, a global daily budget, and precomputed answers that cost nothing."),
 ("s10", "DocBrief: AI that cites, verifies, and fact-checks. Open source under the MIT license. Built on NVIDIA Nemotron, Nebius, and Tavily. Thanks for watching."),
]
async def one(sid, text):
    c = edge_tts.Communicate(text, VOICE, rate="+0%", boundary="WordBoundary")
    words = []
    with open(f"build/{sid}.mp3", "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7, "w": ch["text"]})
    json.dump({"text": text, "words": words}, open(f"build/{sid}.json", "w"))
async def main():
    for sid, t in SCENES: await one(sid, t)
asyncio.run(main())
