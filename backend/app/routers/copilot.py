"""Ask EcoPilot + ESG report generation endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..ai import copilot, llm
from ..ai.rag import get_or_build_index, invalidate_company
from ..ai.report_graph import generate_report
from .chat import save_message
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import (
    CopilotQuery, CopilotResponse, ReportRequest, ReportResponse,
)

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/status")
def ai_status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    idx = get_or_build_index(db, user.company_id)
    return {
        "provider": llm.active_provider(),
        "retrieval_backend": idx.backend,
        "indexed_chunks": len(idx.chunks),
    }


@router.post("/reindex")
def reindex(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    invalidate_company(user.company_id)
    idx = get_or_build_index(db, user.company_id)
    return {"ok": True, "indexed_chunks": len(idx.chunks), "backend": idx.backend}


@router.post("/ask", response_model=CopilotResponse)
def ask(payload: CopilotQuery, db: Session = Depends(get_db),
        user: User = Depends(get_current_user)):
    result = copilot.answer_question(db, payload.question, user.company_id)
    # Persist the turn so the conversation survives across devices/sessions.
    save_message(db, user, "user", payload.question)
    save_message(db, user, "bot", result["answer"],
                 sources=result.get("sources"), provider=result.get("provider"))
    return result


@router.post("/report", response_model=ReportResponse)
def report(payload: ReportRequest, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    return generate_report(db, payload.department_id, user.company_id)

