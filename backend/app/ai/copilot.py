"""Ask EcoPilot — grounded RAG Q&A over ingested policies + goals."""
from sqlalchemy.orm import Session

from . import llm
from .rag import index

SYSTEM = (
    "You are EcoPilot, an ESG assistant. Answer the user's question using ONLY "
    "the provided context from the organisation's ESG policies and environmental "
    "goals. Cite the policy/goal titles you used. If the answer is not in the "
    "context, say you don't have that information in the ingested documents."
)


def _template_answer(results) -> str:
    """Deterministic extractive fallback when no LLM provider is available.
    Still grounded — it quotes the retrieved policy text."""
    if not results:
        return ("I don't have information on that in the ingested ESG documents yet. "
                "Try asking about emission targets, CSR, or governance policies.")
    top = results[0][0]
    body = top.text
    extra = f"\n\nRelated: {results[1][0].title}." if len(results) > 1 else ""
    return f"Based on **{top.title}**:\n\n{body}{extra}"


def answer_question(db: Session, question: str, company_id: int | None = None) -> dict:
    if index.backend == "none" or not index.chunks:
        index.build(db)

    results = index.retrieve(question, k=4, company_id=company_id)
    context = "\n\n".join(f"[{c.title}]\n{c.text}" for c, _ in results)

    prompt = (
        f"Context from ESG documents:\n{context or '(no matching documents)'}\n\n"
        f"Question: {question}\n\nAnswer concisely and cite the document titles."
    )
    res = llm.generate(prompt, system=SYSTEM)
    if res.provider == "none":
        answer, provider = _template_answer(results), "template"
    else:
        answer, provider = res.text, res.provider

    sources = [
        {"title": c.title, "snippet": c.text[:220] + ("…" if len(c.text) > 220 else ""),
         "score": round(score, 3)}
        for c, score in results
    ]
    return {"answer": answer, "sources": sources, "provider": provider}
