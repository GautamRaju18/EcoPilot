"""Ask EcoPilot — grounded RAG Q&A over ingested policies + goals."""
import re

from sqlalchemy.orm import Session

from . import llm
from .rag import get_or_build_index

SYSTEM = (
    "You are EcoPilot, an ESG assistant. Answer the user's question using ONLY "
    "the provided context from the organisation's ESG policies, environmental "
    "goals, departments, emission factors, carbon transactions, CSR activities, "
    "challenges, and compliance records. Be concise and well-structured: lead with "
    "a direct answer, then add supporting detail. Use Markdown (bold key numbers, "
    "bullet points where useful). Cite the source titles you used. If the answer "
    "is not in the context, say you don't have that information in the ingested "
    "documents."
)

_STOP = {"the", "a", "an", "is", "are", "our", "we", "of", "to", "for", "and", "in",
         "on", "what", "how", "does", "do", "your", "you", "with", "by", "at", "this",
         "that", "it", "as", "be", "or", "current", "whats"}


def _terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP and len(w) > 2}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _template_answer(question: str, results) -> str:
    """Extractive fallback when no LLM is available. Instead of dumping a whole
    chunk, it pinpoints the sentences most relevant to the question."""
    if not results:
        return ("I don't have information on that in the ingested ESG documents yet. "
                "Try asking about emission targets, CSR commitments, or governance policies.")

    q = _terms(question)
    scored = []
    for chunk, _ in results:
        for sent in _sentences(chunk.text):
            overlap = len(q & _terms(sent))
            if overlap:
                scored.append((overlap, sent, chunk.title))
    scored.sort(key=lambda x: -x[0])

    if not scored:  # nothing matched — summarise the best chunk's opening
        top = results[0][0]
        lead = " ".join(_sentences(top.text)[:2])
        return f"**{top.title}**\n\n{lead}"

    picked, seen = [], set()
    for _, sent, title in scored:
        if sent not in seen:
            seen.add(sent)
            picked.append((sent, title))
        if len(picked) >= 3:
            break
    title = picked[0][1]
    bullets = "\n".join(f"- {s}" for s, _ in picked)
    return f"**{title}**\n\n{bullets}"


def answer_question(db: Session, question: str, company_id: int | None = None) -> dict:
    idx = get_or_build_index(db, company_id)

    results = idx.retrieve(question, k=4, company_id=company_id)
    context = "\n\n".join(f"[{c.title}]\n{c.text}" for c, _ in results)

    prompt = (
        f"Context from ESG documents:\n{context or '(no matching documents)'}\n\n"
        f"Question: {question}\n\nAnswer concisely in Markdown and cite the document titles."
    )
    res = llm.generate(prompt, system=SYSTEM)
    if res.provider == "none":
        answer, provider = _template_answer(question, results), "template"
    else:
        answer, provider = res.text, res.provider

    sources = [
        {"title": c.title, "snippet": c.text[:220] + ("…" if len(c.text) > 220 else ""),
         "score": round(score, 3)}
        for c, score in results
    ]
    return {"answer": answer, "sources": sources, "provider": provider}

