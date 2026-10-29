import numpy as np

from docbrief.chunking import chunk_document
from docbrief.pdf_loader import load_pdf
from docbrief.retrieval import Retriever
from docbrief.showcase import SHOWCASE_PDF, Showcase, decode_matrix, encode_matrix, to_cache_dict
from docbrief.types import Analysis, FactCheck, Source


def test_matrix_roundtrip():
    m = np.random.default_rng(1).normal(size=(5, 8)).astype("float32")
    assert np.allclose(decode_matrix(encode_matrix(m)), m, atol=1e-2)


def test_shipped_showcase_is_consistent_with_its_pdf():
    sc = Showcase.load()
    assert sc is not None and sc.analysis.tldr and sc.analysis.metrics
    doc = load_pdf(SHOWCASE_PDF.read_bytes(), SHOWCASE_PDF.name)
    chunks = chunk_document(doc)
    assert sc.matrix_for(chunks) is not None and len(sc.matrix_for(chunks)) == len(chunks)  # embeddings match THIS pdf
    assert sc.qa and sc.factcheck and all(f.sources for f in sc.factcheck)
    assert all(m.verified is not False for m in sc.analysis.metrics)  # every cached number is grounded in the filing
    assert sc.find_answer(sc.questions[0].upper() + "  ") is not None  # case/punctuation-insensitive lookup


def test_matrix_for_rejects_stale_chunks():
    doc = load_pdf(SHOWCASE_PDF.read_bytes(), SHOWCASE_PDF.name)
    chunks = chunk_document(doc)
    a = Analysis(title="t")
    sc = Showcase(to_cache_dict(a, [], [FactCheck(claim="c", sources=[Source("W1", None, "x")])], np.ones((len(chunks), 4)), chunks, {}))
    assert sc.matrix_for(chunks) is not None
    assert sc.matrix_for(chunks[:-1]) is None


def test_retriever_uses_preloaded_matrix_without_embedding_calls():
    doc = load_pdf(SHOWCASE_PDF.read_bytes(), SHOWCASE_PDF.name)
    chunks = chunk_document(doc)
    sc = Showcase.load()
    calls = []

    def embedder(texts):
        calls.append(len(texts))
        return np.ones((len(texts), sc.matrix.shape[1]), dtype="float32")

    r = Retriever(chunks, embedder, sc.matrix_for(chunks))
    assert r.mode.startswith("hybrid") and not calls  # chunk embeddings were not recomputed
    r.search("share repurchases and dividends")
    assert calls == [1]  # only the query is embedded
