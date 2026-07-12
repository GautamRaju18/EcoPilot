"""CSR activities + employee participation flow.
Enforces the Evidence Requirement (Rule 3), awards points on approval,
rescores Social, and checks badge unlocks (Rule 4)."""
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import CSRActivity, EmployeeParticipation, User
from ..schemas import CSRActivityCreate, CSRActivityOut, ParticipationOut
from ..services import gamification, scoring
from ..services.notifications import notify
from ..utils import save_upload

router = APIRouter(prefix="/api/csr", tags=["csr"])


# ------------------------------ Activities --------------------------------- #
@router.get("/activities", response_model=list[CSRActivityOut])
def list_activities(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(CSRActivity).order_by(CSRActivity.date.desc()).all()


@router.post("/activities", response_model=CSRActivityOut)
def create_activity(payload: CSRActivityCreate, db: Session = Depends(get_db),
                    _: User = Depends(require_roles("Manager"))):
    activity = CSRActivity(**payload.model_dump())
    if not activity.date:
        activity.date = date.today()
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


# ---------------------------- Participation -------------------------------- #
@router.get("/participations", response_model=list[ParticipationOut])
def list_participations(mine: bool = False, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    q = db.query(EmployeeParticipation)
    if mine:
        q = q.filter(EmployeeParticipation.user_id == user.id)
    return q.order_by(EmployeeParticipation.created_at.desc()).all()


@router.post("/activities/{activity_id}/participate", response_model=ParticipationOut)
def participate(activity_id: int, proof: UploadFile | None = File(default=None),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    activity = db.query(CSRActivity).get(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    part = EmployeeParticipation(
        user_id=user.id,
        activity_id=activity_id,
        proof_file=save_upload(proof) if proof else None,
        approval_status="Pending",
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


@router.post("/participations/{part_id}/proof", response_model=ParticipationOut)
def upload_proof(part_id: int, proof: UploadFile = File(...),
                 db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    part = db.query(EmployeeParticipation).get(part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Participation not found")
    part.proof_file = save_upload(proof)
    db.commit()
    db.refresh(part)
    return part


@router.post("/participations/{part_id}/approve", response_model=ParticipationOut)
def approve(part_id: int, db: Session = Depends(get_db),
            approver: User = Depends(require_roles("Manager"))):
    part = db.query(EmployeeParticipation).get(part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Participation not found")

    # Rule 3: cannot approve without evidence when required
    if settings.EVIDENCE_REQUIRED and not part.proof_file:
        raise HTTPException(status_code=400,
                            detail="Proof required before approval (Evidence Requirement)")

    activity = db.query(CSRActivity).get(part.activity_id)
    part.approval_status = "Approved"
    part.points_earned = activity.points if activity else 0
    part.completion_date = date.today()

    employee = db.query(User).get(part.user_id)
    employee.points_balance += part.points_earned
    db.commit()

    # Rule 4 + Social rescore + notify
    gamification.check_and_award_badges(db, employee)
    if employee.department_id:
        scoring.recompute_department_score(db, employee.department_id)
    notify(db, user_id=employee.id,
           title="CSR participation approved",
           message=f"+{part.points_earned} points for '{activity.title if activity else ''}'",
           type="approval")
    db.refresh(part)
    return part


@router.post("/participations/{part_id}/reject", response_model=ParticipationOut)
def reject(part_id: int, db: Session = Depends(get_db),
           approver: User = Depends(require_roles("Manager"))):
    part = db.query(EmployeeParticipation).get(part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Participation not found")
    part.approval_status = "Rejected"
    db.commit()
    notify(db, user_id=part.user_id, title="CSR participation rejected", type="approval")
    db.refresh(part)
    return part
