"""Smoke-test your Nebius setup (uses NEBIUS_API_KEY from env/.env). Costs a fraction of a cent.

    python scripts/check_nebius.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docbrief.config import Settings
from docbrief.llm import NebiusLLM


def main() -> None:
    s = Settings.from_env()
    if not s.api_key:
        sys.exit("NEBIUS_API_KEY is not set. Get one at https://tokenfactory.nebius.com")
    llm = NebiusLLM(s)
    ok = True
    for tier, name in (("main", s.model), ("fast", s.fast_model), ("deep", s.deep_model)):
        try:
            out = llm.chat([{"role": "user", "content": "Reply with the single word: pong"}], tier=tier, max_tokens=300)
            print(f"OK   chat/{tier:<4} {name}: {out[:40]!r}")
        except Exception as e:
            ok = False
            print(f"FAIL chat/{tier:<4} {name}: {type(e).__name__}: {str(e)[:160]}")
    try:
        v = llm.embed(["hello world"])
        print(f"OK   embeddings {s.embed_model}: dim={v.shape[1]}")
    except Exception as e:
        print(f"WARN embeddings {s.embed_model}: {type(e).__name__}: {str(e)[:160]}  (app falls back to BM25)")
    print(f"\nTokens used: prompt={llm.usage['prompt']} completion={llm.usage['completion']}")
    print("\nTip: if a model 404s, pick the right ID/region from https://tokenfactory.nebius.com/model-catalog.md and set it in .env")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
