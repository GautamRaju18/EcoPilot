"""Weighted ESG scoring engine (Business Rule 1).

Scores are derived live from DB state so that logging a carbon transaction,
approving a CSR activity, or resolving a compliance issue visibly shifts them.
"""
from datetime import date

from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    CarbonTransaction, ChallengeParticipation, ComplianceIssue, CSRActivity,
    Department, DepartmentScore, EmployeeParticipation, PolicyAcknowledgement, User,
)

# Tunables — chosen so seeded demo data lands in a believable 50–90 range.
CO2E_PER_POINT = 1600.0     # kg CO2e that costs 1 environmental point
ENV_BASELINE = 100.0
SOCIAL_BASELINE = 45.0
GOV_BASELINE = 85.0


def _clamp(v: float) -> float:
    return round(max(0.0, min(100.0, v)), 1)


def compute_environmental(db: Session, department_id: int) -> float:
    total_co2e = (
        db.query(CarbonTransaction)
        .filter(CarbonTransaction.department_id == department_id)
        .with_entities(CarbonTransaction.co2e)
        .all()
    )
    total = sum(row[0] or 0.0 for row in total_co2e)
    return _clamp(ENV_BASELINE - total / CO2E_PER_POINT)


def compute_social(db: Session, department_id: int) -> float:
    # Approved CSR participations by employees of this department
    approved_csr = (
        db.query(EmployeeParticipation)
        .join(User, EmployeeParticipation.user_id == User.id)
        .filter(User.department_id == department_id,
                EmployeeParticipation.approval_status == "Approved")
        .count()
    )
    approved_challenges = (
        db.query(ChallengeParticipation)
        .join(User, ChallengeParticipation.user_id == User.id)
        .filter(User.department_id == department_id,
                ChallengeParticipation.approval_status == "Approved")
        .count()
    )
    return _clamp(SOCIAL_BASELINE + approved_csr * 6 + approved_challenges * 4)


def compute_governance(db: Session, department_id: int) -> float:
    today = date.today()
    open_issues = db.query(ComplianceIssue).filter(ComplianceIssue.status != "Resolved").all()
    open_count = len(open_issues)
    overdue = sum(1 for i in open_issues if i.due_date and i.due_date < today)

    emp_ids = [u.id for u in db.query(User).filter(User.department_id == department_id).all()]
    acks = 0
    if emp_ids:
        acks = (
            db.query(PolicyAcknowledgement)
            .filter(PolicyAcknowledgement.user_id.in_(emp_ids))
            .count()
        )
    ack_bonus = min(15, acks * 3)
    return _clamp(GOV_BASELINE - open_count * 3 - overdue * 6 + ack_bonus)


def recompute_department_score(db: Session, department_id: int) -> DepartmentScore:
    env = compute_environmental(db, department_id)
    soc = compute_social(db, department_id)
    gov = compute_governance(db, department_id)
    total = round(
        settings.WEIGHT_ENVIRONMENTAL * env
        + settings.WEIGHT_SOCIAL * soc
        + settings.WEIGHT_GOVERNANCE * gov,
        1,
    )

    score = db.query(DepartmentScore).filter(
        DepartmentScore.department_id == department_id
    ).first()
    if not score:
        score = DepartmentScore(department_id=department_id)
        db.add(score)
    score.environmental_score = env
    score.social_score = soc
    score.governance_score = gov
    score.total_score = total
    db.commit()
    db.refresh(score)
    return score


def recompute_all(db: Session) -> list[DepartmentScore]:
    return [recompute_department_score(db, d.id) for d in db.query(Department).all()]


def overall_scores(db: Session) -> dict:
    """Org-wide averages across departments (used by dashboard + report)."""
    scores = db.query(DepartmentScore).all()
    if not scores:
        return {"environmental": 0, "social": 0, "governance": 0, "overall": 0}
    n = len(scores)
    env = round(sum(s.environmental_score for s in scores) / n, 1)
    soc = round(sum(s.social_score for s in scores) / n, 1)
    gov = round(sum(s.governance_score for s in scores) / n, 1)
    overall = round(
        settings.WEIGHT_ENVIRONMENTAL * env
        + settings.WEIGHT_SOCIAL * soc
        + settings.WEIGHT_GOVERNANCE * gov,
        1,
    )
    return {"environmental": env, "social": soc, "governance": gov, "overall": overall}
