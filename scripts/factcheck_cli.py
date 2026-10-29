"""Run the web fact-check on a PDF from the command line (live mode: needs NEBIUS_API_KEY + TAVILY_API_KEY)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docbrief.config import Settings
from docbrief.engine import get_engine
from docbrief.pdf_loader import load_pdf
from docbrief.tavily import make_search

s = Settings.from_env()
assert s.is_live and s.tavily_key, "set NEBIUS_API_KEY and TAVILY_API_KEY"
p = Path(sys.argv[1])
doc = load_pdf(p.read_bytes(), p.name)
eng = get_engine(s)
a = eng.analyze(doc)
for c in eng.fact_check(doc, a, make_search(s.tavily_key)):
    print(f"\n[{c.verdict.upper()}] (p.{c.page}) {c.claim}\n  query: {c.query}\n  PDF: {c.pdf_says}\n  WEB: {c.web_says}\n  WHY: {c.explanation}")
    for w in c.sources:
        print(f"   - [{w.label}] {w.url}")
print("\nNebius calls:", eng.llm.calls, "tokens:", eng.llm.usage)
