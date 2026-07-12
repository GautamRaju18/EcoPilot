"""In-app notifications (Business Rule 8 — no email)."""
from sqlalchemy.orm import Session

from ..models import Notification


def notify(db: Session, *, title: str, message: str = "", type: str = "info",
           user_id: int | None = None, company_id: int | None = None,
           commit: bool = True) -> Notification:
    n = Notification(user_id=user_id, company_id=company_id, title=title,
                     message=message, type=type)
    db.add(n)
    if commit:
        db.commit()
        db.refresh(n)
    return n
