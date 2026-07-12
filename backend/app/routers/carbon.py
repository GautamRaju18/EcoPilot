"""Carbon transactions — logging + auto emission calc (Business Rule 2).
Logging a transaction rescores the department so the Environmental score
visibly shifts (Definition of Done)."""
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CarbonTransaction, User
from ..schemas import CarbonTransactionCreate, CarbonTransactionOut
from ..services import scoring
from ..services.emissions import calculate_co2e

router = APIRouter(prefix="/api/carbon", tags=["carbon"])


@router.get("", response_model=list[CarbonTransactionOut])
def list_transactions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (db.query(CarbonTransaction)
            .filter(CarbonTransaction.company_id == user.company_id)
            .order_by(CarbonTransaction.date.desc()).all())


@router.post("", response_model=CarbonTransactionOut)
def create_transaction(payload: CarbonTransactionCreate, db: Session = Depends(get_db),
                       user: User = Depends(get_current_user)):
    co2e = calculate_co2e(
        db,
        emission_factor_id=payload.emission_factor_id,
        quantity=payload.quantity,
        provided_co2e=payload.co2e,
    )
    tx = CarbonTransaction(
        company_id=user.company_id,
        source_ref=payload.source_ref,
        source_type=payload.source_type,
        emission_factor_id=payload.emission_factor_id,
        quantity=payload.quantity,
        co2e=co2e,
        department_id=payload.department_id,
        date=payload.date or date.today(),
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # Rule 1 / DoD: recompute the affected department's environmental score
    if tx.department_id:
        scoring.recompute_department_score(db, tx.department_id)
    return tx
