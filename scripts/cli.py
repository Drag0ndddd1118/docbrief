"""Headless usage:  python scripts/cli.py samples/aurora_robotics_fy2025_report.pdf ["question"]"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docbrief.chunking import chunk_document
from docbrief.config import Settings
from docbrief.engine import get_engine
from docbrief.pdf_loader import load_pdf
from docbrief.report import to_markdown


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    s = Settings.from_env()
    eng = get_engine(s)
    doc = load_pdf(Path(sys.argv[1]).read_bytes(), Path(sys.argv[1]).name)
    a = eng.analyze(doc)
    print(f"[{eng.describe()}]\n")
    print(to_markdown(a))
    if len(sys.argv) > 2:
        r = eng.build_retriever(chunk_document(doc))
        ans = eng.answer(doc, r, sys.argv[2])
        print("\nQ:", sys.argv[2], "\nA:", ans.text)


if __name__ == "__main__":
    main()
