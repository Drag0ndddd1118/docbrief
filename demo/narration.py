"""Generate per-scene narration (edge-tts, en-US-AndrewNeural) + word timings."""
import asyncio, json, edge_tts
VOICE = "en-US-AndrewNeural"
SCENES = [
 ("s0", "What's next year's revenue guidance? Five seconds. Cited to the page."),
 ("s1", "I'm Qin, and this is DocBrief, a speed reader for research papers and annual reports. Chat-with-PDF tools are fast, but they quietly invent numbers. DocBrief shows its receipts, and checks them against the live web."),
 ("s2", "It runs live on NVIDIA Nemotron models, served by Nebius Token Factory. Nemotron Super does the analysis, Nemotron Nano handles the fast steps, and Nemotron Ultra is there for deep reasoning. Tavily adds live web search."),
 ("s3", "I drop in a company's annual report. Super reads every page, and on long filings Nano summarizes each section first, then Super merges them."),
 ("s4", "In seconds: a one line takeaway, a structured summary, key points, and risks, each tagged with the page it came from."),
 ("s5", "Now the part I care about. Every number in this table is checked against the raw text of the PDF. If the model reports a figure that isn't literally in the document, it gets flagged for review. That's how you stop hallucinated financials."),
 ("sT", "But a PDF can be consistent with itself and still wrong about the world. So I hit Fact-check with the web. Nemotron Nano picks the claims that can be checked publicly. Tavily searches the live web for each one. Then Nemotron Super reconciles the PDF against what it found. This report says warehouse automation grows six percent a year. The web says nearly nineteen. Flagged, with links. The e-commerce share claim checks out."),
 ("s6", "Then I can just ask. Retrieval blends keyword search with Nebius embeddings, and the answer comes back with its page citations. Guidance, five sixty to five eighty million, on page four."),
 ("s7", "Open the sources, and the exact passages are right there."),
 ("s8", "And I can ask in Chinese about an English document. Nano rewrites the question into search terms, and Super answers in Chinese, still citing the page."),
 ("s9", "Switch on deep reasoning for harder questions, or export the whole brief as Markdown. DocBrief is open source under the MIT license. Built on NVIDIA Nemotron, Nebius, and Tavily. Thanks for watching."),
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
