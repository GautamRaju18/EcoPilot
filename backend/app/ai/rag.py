"""RAG over ESG policies, goals, departments, and operational data.

Retrieval backends:
  * TF-IDF (scikit-learn) — always available, fully local, great for a small
    curated corpus. This is the default and the offline-safe fallback.
  * FAISS + Gemini embeddings — used when EMBEDDINGS_BACKEND=="gemini", a key
    is set, and both libs import. Falls back to TF-IDF on any failure.

The index is per-company, cached in memory, and auto-invalidated when master
data changes (departments, goals, policies, etc.).
"""
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    ESGPolicy, EnvironmentalGoal, Department, EmissionFactor,
    CarbonTransaction, CSRActivity, Challenge, ComplianceIssue,
)


@dataclass
class Chunk:
    title: str
    text: str
    company_id: int | None = None


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


# --------------------------------------------------------------------------- #
# Per-company index cache — invalidated when master data changes
# --------------------------------------------------------------------------- #
_company_indexes: dict[int, "_Index"] = {}


def get_or_build_index(db: Session, company_id: int | None = None) -> "_Index":
    """Return a cached per-company index, building it on first access."""
    if company_id is None:
        # Fallback: global index (unlikely in normal flow)
        if "_global" not in _company_indexes:
            idx = _Index()
            idx.build(db)
            _company_indexes["_global"] = idx
        return _company_indexes["_global"]

    if company_id not in _company_indexes:
        idx = _Index()
        idx.build(db, company_id=company_id)
        _company_indexes[company_id] = idx
    return _company_indexes[company_id]


def invalidate_company(company_id: int | None = None):
    """Clear the cached index for a company so the next query rebuilds it
    with fresh data (e.g. after a new department is created)."""
    if company_id is None:
        _company_indexes.clear()
    else:
        _company_indexes.pop(company_id, None)
        _company_indexes.pop("_global", None)


class _Index:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.backend: str = "none"
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._embeddings = None  # np.ndarray for gemini/faiss path

    # ---------------------------- build -------------------------------- #
    def build(self, db: Session, company_id: int | None = None) -> int:
        self.chunks = []

        # --- ESG Policies (chunked — can be long) ---
        pq = db.query(ESGPolicy)
        if company_id is not None:
            pq = pq.filter(ESGPolicy.company_id == company_id)
        for p in pq.all():
            header = f"{p.title} (v{p.version}, {p.category})"
            for c in _chunk_text(p.document):
                self.chunks.append(Chunk(title=header, text=c, company_id=p.company_id))

        # --- Environmental Goals ---
        gq = db.query(EnvironmentalGoal)
        if company_id is not None:
            gq = gq.filter(EnvironmentalGoal.company_id == company_id)
        for g in gq.all():
            dept = g.department.name if g.department else "Org-wide"
            txt = (f"Environmental Goal — {g.target_metric}: target {g.target_value} "
                   f"{g.unit} by {g.deadline} for {dept}. "
                   f"Current value {g.current_value} {g.unit}.")
            self.chunks.append(Chunk(title=f"Goal: {g.target_metric}", text=txt,
                                     company_id=g.company_id))

        # --- Departments ---
        dq = db.query(Department)
        if company_id is not None:
            dq = dq.filter(Department.company_id == company_id)
        for d in dq.all():
            parent_info = ""
            if d.parent:
                parent_info = f" It is a sub-department of {d.parent.name}."
            head_info = f" Department head: {d.head}." if d.head else ""
            txt = (f"Department: {d.name} (code: {d.code}). "
                   f"Status: {d.status}. "
                   f"Employee count: {d.employee_count}.{head_info}{parent_info}")
            self.chunks.append(Chunk(title=f"Department: {d.name}", text=txt,
                                     company_id=d.company_id))

        # --- Emission Factors ---
        eq = db.query(EmissionFactor)
        if company_id is not None:
            eq = eq.filter(EmissionFactor.company_id == company_id)
        for ef in eq.all():
            desc = f" Description: {ef.description}." if ef.description else ""
            txt = (f"Emission Factor: {ef.activity_type} — "
                   f"{ef.co2e_per_unit} kg CO₂e per {ef.unit}.{desc}")
            self.chunks.append(Chunk(title=f"Emission Factor: {ef.activity_type}",
                                     text=txt, company_id=ef.company_id))

        # --- Carbon Transactions (recent, summarised) ---
        cq = db.query(CarbonTransaction)
        if company_id is not None:
            cq = cq.filter(CarbonTransaction.company_id == company_id)
        for ct in cq.order_by(CarbonTransaction.date.desc()).limit(50).all():
            dept_name = ct.department.name if ct.department else "Unassigned"
            factor_name = ct.emission_factor.activity_type if ct.emission_factor else "N/A"
            txt = (f"Carbon Transaction on {ct.date}: source {ct.source_ref or 'N/A'} "
                   f"(type: {ct.source_type}), activity: {factor_name}, "
                   f"quantity: {ct.quantity}, CO₂e: {ct.co2e} kg. "
                   f"Department: {dept_name}.")
            self.chunks.append(Chunk(title=f"Carbon: {ct.source_ref or ct.source_type}",
                                     text=txt, company_id=ct.company_id))

        # --- CSR Activities ---
        sq = db.query(CSRActivity)
        if company_id is not None:
            sq = sq.filter(CSRActivity.company_id == company_id)
        for csr in sq.all():
            dept_name = csr.department.name if csr.department else "Org-wide"
            cat_name = csr.category.name if csr.category else "Uncategorised"
            txt = (f"CSR Activity: {csr.title}. Category: {cat_name}. "
                   f"Points: {csr.points}. Date: {csr.date}. "
                   f"Department: {dept_name}. "
                   f"Description: {csr.description or 'N/A'}.")
            self.chunks.append(Chunk(title=f"CSR: {csr.title}", text=txt,
                                     company_id=csr.company_id))

        # --- Challenges ---
        chq = db.query(Challenge)
        if company_id is not None:
            chq = chq.filter(Challenge.company_id == company_id)
        for ch in chq.all():
            cat_name = ch.category.name if ch.category else "Uncategorised"
            txt = (f"Challenge: {ch.title}. Category: {cat_name}. "
                   f"XP: {ch.xp}. Difficulty: {ch.difficulty}. Status: {ch.status}. "
                   f"Deadline: {ch.deadline or 'None'}. "
                   f"Description: {ch.description or 'N/A'}.")
            self.chunks.append(Chunk(title=f"Challenge: {ch.title}", text=txt,
                                     company_id=ch.company_id))

        # --- Compliance Issues ---
        ciq = db.query(ComplianceIssue)
        if company_id is not None:
            ciq = ciq.filter(ComplianceIssue.company_id == company_id)
        for ci in ciq.all():
            txt = (f"Compliance Issue: {ci.description}. "
                   f"Severity: {ci.severity}. Status: {ci.status}. "
                   f"Owner: {ci.owner}. Due date: {ci.due_date}.")
            self.chunks.append(Chunk(title=f"Compliance: {ci.severity} issue",
                                     text=txt, company_id=ci.company_id))

        if not self.chunks:
            self.backend = "none"
            return 0

        corpus = [c.text for c in self.chunks]
        if not self._try_build_gemini_faiss(corpus):
            self._build_tfidf(corpus)
        return len(self.chunks)

    def _build_tfidf(self, corpus: list[str]) -> None:
        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                           sublinear_tf=True)
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
    def retrieve(self, query: str, k: int = 4,
                 company_id: int | None = None) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        if self.backend == "faiss+gemini" and self._embeddings is not None:
            q = _gemini_embed([query])
            if q is not None:
                sims = cosine_similarity(q, self._embeddings)[0]
                return self._top(sims, k, company_id)
        # tfidf path (default / fallback)
        if self._vectorizer is None:
            self._build_tfidf([c.text for c in self.chunks])
        qv = self._vectorizer.transform([query])
        sims = cosine_similarity(qv, self._matrix)[0]
        return self._top(sims, k, company_id)

    def _top(self, sims, k: int, company_id: int | None = None) -> list[tuple[Chunk, float]]:
        res = []
        for i in np.argsort(sims)[::-1]:
            c = self.chunks[i]
            if company_id is not None and c.company_id != company_id:
                continue  # tenant isolation — never surface another company's docs
            if sims[i] <= 0.01:
                continue
            res.append((c, float(sims[i])))
            if len(res) >= k:
                break
        return res


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
