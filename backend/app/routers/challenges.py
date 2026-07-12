"""Challenges: lifecycle (Rule 6), participation, approval -> XP + badge unlock
(Rule 4). Approving a challenge awards XP, increments completed_challenges,
rescores Social, and auto-awards badges."""
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import Challenge, ChallengeParticipation, User
from ..schemas import ChallengeCreate, ChallengeOut, ChallengeParticipationOut
from ..services import gamification, scoring
from ..services.notifications import notify
from ..utils import save_upload

router = APIRouter(prefix="/api/challenges", tags=["challenges"])

VALID_STATUSES = {"Draft", "Active", "Under Review", "Completed", "Archived"}


@router.get("", response_model=list[ChallengeOut])
def list_challenges(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Challenge).all()


@router.post("", response_model=ChallengeOut)
def create_challenge(payload: ChallengeCreate, db: Session = Depends(get_db),
                     _: User = Depends(require_roles("Manager"))):
    ch = Challenge(**payload.model_dump())
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return ch


@router.post("/{challenge_id}/status", response_model=ChallengeOut)
def set_status(challenge_id: int, status: str = Body(..., embed=True),
               db: Session = Depends(get_db), _: User = Depends(require_roles("Manager"))):
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. One of {VALID_STATUSES}")
    ch = db.query(Challenge).get(challenge_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Challenge not found")
    ch.status = status
    db.commit()
    db.refresh(ch)
    return ch


# ---------------------------- Participation -------------------------------- #
@router.get("/participations", response_model=list[ChallengeParticipationOut])
def list_participations(mine: bool = False, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    q = db.query(ChallengeParticipation)
    if mine:
        q = q.filter(ChallengeParticipation.user_id == user.id)
    return q.order_by(ChallengeParticipation.created_at.desc()).all()


@router.post("/{challenge_id}/join", response_model=ChallengeParticipationOut)
def join(challenge_id: int, proof: UploadFile | None = File(default=None),
         progress: int = Body(default=100, embed=True),
         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    ch = db.query(Challenge).get(challenge_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Challenge not found")
    part = ChallengeParticipation(
        challenge_id=challenge_id,
        user_id=user.id,
        progress=progress,
        proof_file=save_upload(proof) if proof else None,
        approval_status="Pending",
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


@router.post("/participations/{part_id}/approve", response_model=ChallengeParticipationOut)
def approve(part_id: int, db: Session = Depends(get_db),
            approver: User = Depends(require_roles("Manager"))):
    part = db.query(ChallengeParticipation).get(part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Participation not found")
    ch = db.query(Challenge).get(part.challenge_id)

    if ch and ch.evidence_required and settings.EVIDENCE_REQUIRED and not part.proof_file:
        raise HTTPException(status_code=400, detail="Proof required before approval")

    part.approval_status = "Approved"
    part.xp_awarded = ch.xp if ch else 0

    employee = db.query(User).get(part.user_id)
    employee.xp += part.xp_awarded
    employee.completed_challenges += 1
    db.commit()

    # Rule 4: auto-award badges the moment thresholds are met
    newly = gamification.check_and_award_badges(db, employee)
    if employee.department_id:
        scoring.recompute_department_score(db, employee.department_id)
    notify(db, user_id=employee.id, title="Challenge approved",
           message=f"+{part.xp_awarded} XP for '{ch.title if ch else ''}'", type="approval")

    db.refresh(part)
    return part


@router.post("/participations/{part_id}/reject", response_model=ChallengeParticipationOut)
def reject(part_id: int, db: Session = Depends(get_db),
           approver: User = Depends(require_roles("Manager"))):
    part = db.query(ChallengeParticipation).get(part_id)
    if not part:
        raise HTTPException(status_code=404, detail="Participation not found")
    part.approval_status = "Rejected"
    db.commit()
    notify(db, user_id=part.user_id, title="Challenge submission rejected", type="approval")
    db.refresh(part)
    return part
