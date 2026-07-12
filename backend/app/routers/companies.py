"""Company (tenant) endpoints: public directory for signup + cross-company ESG ranking."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Company, User
from ..schemas import CompanyOut
from ..services import scoring

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("/public", response_model=list[CompanyOut])
def public_list(db: Session = Depends(get_db)):
    """Unauthenticated — used by the registration screen to pick a company to join."""
    return db.query(Company).order_by(Company.name).all()


@router.get("/leaderboard")
def company_leaderboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Cross-company ESG ranking — every company scored side by side."""
    scoring.recompute_all(db)  # refresh all companies' department scores
    rows = []
    for c in db.query(Company).all():
        s = scoring.overall_scores(db, c.id)
        rows.append({
            "company_id": c.id, "name": c.name, "industry": c.industry,
            "employees": db.query(User).filter(User.company_id == c.id).count(),
            **s,
        })
    rows.sort(key=lambda r: r["overall"], reverse=True)
    return rows
