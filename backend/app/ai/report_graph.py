"""Auto-generated ESG Summary Report — a LangGraph pipeline.

Graph:  gather_scores -> retrieve_context -> draft_narrative -> finalize
If langgraph isn't installed, the same nodes run sequentially (identical output).
"""
from datetime import datetime

from sqlalchemy.orm import Session

from . import llm
from .rag import index
from ..models import Department, DepartmentScore
from ..services import scoring


# ----------------------------- nodes --------------------------------------- #
def gather_scores(state: dict) -> dict:
    db: Session = state["db"]
    dept_id = state.get("department_id")
    company_id = state.get("company_id")
    scoring.recompute_all(db, company_id)
    overall = scoring.overall_scores(db, company_id)

    breakdown = []
    q = db.query(DepartmentScore)
    if company_id is not None:
        q = q.filter(DepartmentScore.company_id == company_id)
    if dept_id:
        q = q.filter(DepartmentScore.department_id == dept_id)
    for s in q.all():
        dept = db.query(Department).get(s.department_id)
        breakdown.append({
            "department": dept.name if dept else f"#{s.department_id}",
            "environmental": s.environmental_score,
            "social": s.social_score,
            "governance": s.governance_score,
            "total": s.total_score,
        })
    state["overall"] = overall
    state["breakdown"] = breakdown
    return state


def retrieve_context(state: dict) -> dict:
    if index.backend == "none" or not index.chunks:
        index.build(state["db"])
    hits = index.retrieve(
        "sustainability targets emission reduction governance social responsibility", k=4,
        company_id=state.get("company_id"),
    )
    state["policy_context"] = "\n".join(f"- {c.title}: {c.text[:200]}" for c, _ in hits)
    return state


def _facts_block(state: dict) -> str:
    lines = [f"Overall ESG score: {state['overall']['overall']}/100 "
             f"(E {state['overall']['environmental']}, "
             f"S {state['overall']['social']}, "
             f"G {state['overall']['governance']})."]
    for b in state["breakdown"]:
        lines.append(f"{b['department']}: total {b['total']} "
                     f"(E {b['environmental']}, S {b['social']}, G {b['governance']}).")
    return "\n".join(lines)


def draft_narrative(state: dict) -> dict:
    facts = _facts_block(state)
    prompt = (
        "Write a concise, professional ESG summary report (4-6 short paragraphs) "
        "for company leadership. Use the metrics and policy context below. "
        "Interpret the weighted scores (Environmental 40%, Social 30%, Governance 30%), "
        "call out the strongest and weakest departments, relate performance to the "
        "stated policies/goals, and end with 2-3 concrete recommendations.\n\n"
        f"METRICS:\n{facts}\n\nPOLICY CONTEXT:\n{state.get('policy_context', '')}\n"
    )
    res = llm.generate(prompt, system="You are an ESG reporting analyst.")
    if res.provider == "none":
        state["narrative"] = _template_narrative(state, facts)
        state["provider"] = "template"
    else:
        state["narrative"] = res.text
        state["provider"] = res.provider
    return state


def _template_narrative(state: dict, facts: str) -> str:
    o = state["overall"]
    b = sorted(state["breakdown"], key=lambda x: x["total"], reverse=True)
    best = b[0]["department"] if b else "N/A"
    worst = b[-1]["department"] if b else "N/A"
    return (
        f"ESG Performance Summary\n\n"
        f"The organisation's overall weighted ESG score stands at {o['overall']}/100, "
        f"composed of Environmental {o['environmental']}, Social {o['social']}, and "
        f"Governance {o['governance']} (weighted 40/30/30 respectively).\n\n"
        f"Departmental performance ranges from a high at {best} to the lowest at "
        f"{worst}. Full breakdown:\n{facts}\n\n"
        f"Recommendations: (1) prioritise emission-reduction initiatives in "
        f"lower-scoring departments; (2) sustain CSR and challenge participation to "
        f"lift the Social dimension; (3) close open compliance issues before their "
        f"due dates to protect the Governance score."
    )


def finalize(state: dict) -> dict:
    scope = "Organisation-wide"
    if state.get("department_id"):
        dept = state["db"].query(Department).get(state["department_id"])
        scope = dept.name if dept else scope
    state["title"] = f"ESG Summary Report — {scope}"
    return state


# ----------------------------- runner -------------------------------------- #
def _build_graph():
    from langgraph.graph import StateGraph, END
    g = StateGraph(dict)
    g.add_node("gather", gather_scores)
    g.add_node("retrieve", retrieve_context)
    g.add_node("draft", draft_narrative)
    g.add_node("finalize", finalize)
    g.set_entry_point("gather")
    g.add_edge("gather", "retrieve")
    g.add_edge("retrieve", "draft")
    g.add_edge("draft", "finalize")
    g.add_edge("finalize", END)
    return g.compile()


def generate_report(db: Session, department_id: int | None = None,
                    company_id: int | None = None) -> dict:
    state = {"db": db, "department_id": department_id, "company_id": company_id}
    try:
        graph = _build_graph()
        state = graph.invoke(state)
    except Exception as e:  # noqa: BLE001 — langgraph missing/incompatible
        print(f"[report] langgraph unavailable, running sequentially: {e}")
        for node in (gather_scores, retrieve_context, draft_narrative, finalize):
            state = node(state)

    return {
        "title": state["title"],
        "narrative": state["narrative"],
        "overall_score": state["overall"]["overall"],
        "provider": state["provider"],
        "generated_at": datetime.utcnow(),
    }
