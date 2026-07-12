"""ESG scoring endpoints — scoped to the caller's company."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Department, DepartmentScore, User
from ..schemas import DepartmentScoreOut
from ..services import scoring

router = APIRouter(prefix="/api/scores", tags=["scoring"])


@router.get("/overview")
def overview(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Company-wide ESG scores + per-department breakdown for the dashboard."""
    scoring.recompute_all(db, user.company_id)
    overall = scoring.overall_scores(db, user.company_id)
    departments = []
    for s in db.query(DepartmentScore).filter(DepartmentScore.company_id == user.company_id).all():
        dept = db.query(Department).get(s.department_id)
        departments.append({
            "department_id": s.department_id,
            "department": dept.name if dept else f"#{s.department_id}",
            "environmental": s.environmental_score,
            "social": s.social_score,
            "governance": s.governance_score,
            "total": s.total_score,
        })
    departments.sort(key=lambda d: d["total"], reverse=True)
    return {"overall": overall, "departments": departments}


@router.get("/departments", response_model=list[DepartmentScoreOut])
def department_scores(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(DepartmentScore).filter(DepartmentScore.company_id == user.company_id).all()


@router.post("/recompute")
def recompute(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    scoring.recompute_all(db, user.company_id)
    return {"ok": True, **scoring.overall_scores(db, user.company_id)}
