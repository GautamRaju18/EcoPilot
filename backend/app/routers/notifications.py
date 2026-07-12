"""In-app notifications (Business Rule 8)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Notification, User
from ..schemas import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def my_notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # personal notifications, plus company-wide broadcasts for the caller's company
    return (
        db.query(Notification)
        .filter(or_(
            Notification.user_id == user.id,
            and_(Notification.user_id.is_(None), Notification.company_id == user.company_id),
        ))
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )


@router.post("/{notif_id}/read")
def mark_read(notif_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.query(Notification).get(notif_id)
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.query(Notification).filter(
        or_(Notification.user_id == user.id,
            and_(Notification.user_id.is_(None), Notification.company_id == user.company_id))
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return {"ok": True}
