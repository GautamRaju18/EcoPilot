"""Persistent Ask EcoPilot chat history (per user, survives across devices)."""
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import ChatMessage, User

router = APIRouter(prefix="/api/ai", tags=["chat"])


def save_message(db: Session, user: User, role: str, content: str,
                 sources: list | None = None, provider: str | None = None) -> None:
    """Persist one chat turn. Best-effort — never breaks the request on failure."""
    try:
        db.add(ChatMessage(
            company_id=user.company_id, user_id=user.id, role=role, content=content,
            sources=json.dumps(sources) if sources else None, provider=provider,
        ))
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()


@router.get("/history")
def get_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    msgs = (db.query(ChatMessage)
            .filter(ChatMessage.user_id == user.id)
            .order_by(ChatMessage.created_at.asc())
            .limit(300).all())
    return [{
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "sources": json.loads(m.sources) if m.sources else [],
        "provider": m.provider,
        "created_at": m.created_at,
    } for m in msgs]


@router.delete("/history")
def clear_history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"ok": True}
