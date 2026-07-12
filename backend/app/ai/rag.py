"""RAG over ESG policies + environmental goals.

Retrieval backends:
  * TF-IDF (scikit-learn) — always available, fully local, great for a small
    curated corpus. This is the default and the offline-safe fallback.
  * FAISS + Gemini embeddings — used when EMBEDDINGS_BACKEND=="gemini", a key
    is set, and both libs import. Falls back to TF-IDF on any failure.

The index is an in-memory singleton, (re)built from the DB on ingest.
"""
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ESGPolicy, EnvironmentalGoal


@dataclass
class Chunk:
    title: str
    text: str


def _chunk_text(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    text = " ".join(text.split())
    if len(text) <= size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


class _Index:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.backend: str = "none"
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._embeddings = None  # np.ndarray for gemini/faiss path

    # ---------------------------- build -------------------------------- #
    def build(self, db: Session) -> int:
        self.chunks = []
        for p in db.query(ESGPolicy).all():
            header = f"{p.title} (v{p.version}, {p.category})"
            for c in _chunk_text(p.document):
                self.chunks.append(Chunk(title=header, text=c))
        for g in db.query(EnvironmentalGoal).all():
            dept = g.department.name if g.department else "Org-wide"
            txt = (f"Environmental Goal — {g.target_metric}: target {g.target_value} "
                   f"{g.unit} by {g.deadline} for {dept}. "
                   f"Current value {g.current_value} {g.unit}.")
            self.chunks.append(Chunk(title=f"Goal: {g.target_metric}", text=txt))

        if not self.chunks:
            self.backend = "none"
            return 0

        corpus = [c.text for c in self.chunks]
        if not self._try_build_gemini_faiss(corpus):
            self._build_tfidf(corpus)
        return len(self.chunks)

    def _build_tfidf(self, corpus: list[str]) -> None:
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform(corpus)
        self.backend = "tfidf"

    def _try_build_gemini_faiss(self, corpus: list[str]) -> bool:
        if settings.EMBEDDINGS_BACKEND != "gemini" or not settings.GEMINI_API_KEY:
            return False
        try:
            embs = _gemini_embed(corpus)
            if embs is None:
                return False
            import faiss  # noqa: F401 — presence check; we use numpy cosine below
            self._embeddings = embs
            self.backend = "faiss+gemini"
            return True
        except Exception as e:  # noqa: BLE001
            print(f"[rag] gemini/faiss build failed, using tfidf: {e}")
            return False

    # ---------------------------- query -------------------------------- #
    def retrieve(self, query: str, k: int = 4) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        if self.backend == "faiss+gemini" and self._embeddings is not None:
            q = _gemini_embed([query])
            if q is not None:
                sims = cosine_similarity(q, self._embeddings)[0]
                return self._top(sims, k)
        # tfidf path (default / fallback)
        if self._vectorizer is None:
            self._build_tfidf([c.text for c in self.chunks])
        qv = self._vectorizer.transform([query])
        sims = cosine_similarity(qv, self._matrix)[0]
        return self._top(sims, k)

    def _top(self, sims, k: int) -> list[tuple[Chunk, float]]:
        idx = np.argsort(sims)[::-1][:k]
        return [(self.chunks[i], float(sims[i])) for i in idx if sims[i] > 0.01]


def _gemini_embed(texts: list[str]):
    """Embed with Gemini; returns np.ndarray or None on failure."""
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        vecs = []
        for t in texts:
            r = client.models.embed_content(model="text-embedding-004", contents=t)
            vecs.append(r.embeddings[0].values)
        return np.array(vecs, dtype="float32")
    except Exception as e:  # noqa: BLE001
        print(f"[rag] gemini embed failed: {e}")
        return None


# Module singleton
index = _Index()
