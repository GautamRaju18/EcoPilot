"""New-company onboarding: check state, load sample data, or import an ESG CSV."""
import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import User
from ..services import sample_data

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

TEMPLATE = (
    "department,activity_type,unit,quantity,co2e_per_unit,co2e,date,source_ref\n"
    "Operations,electricity_kwh,kWh,12000,0.82,,2026-01-15,OPS-Q1\n"
    "Logistics,diesel_liter,liter,3000,2.68,,2026-01-20,FLEET-1\n"
    "Facilities,,,,,1500,2026-02-01,BUILDING-A\n"
)


@router.get("/status")
def status(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Frontend uses this to decide whether to show the onboarding popup."""
    return {
        "company_id": user.company_id,
        "company": user.company.name if user.company else None,
        "has_data": sample_data.company_has_data(db, user.company_id),
    }


@router.get("/template", response_class=PlainTextResponse)
def template():
    return PlainTextResponse(
        TEMPLATE, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ecopilot_esg_template.csv"},
    )


@router.post("/sample-data")
def load_sample_data(db: Session = Depends(get_db),
                     user: User = Depends(require_roles("Manager"))):
    if sample_data.company_has_data(db, user.company_id):
        raise HTTPException(status_code=400, detail="Company already has data")
    return {"ok": True, **sample_data.populate_company(db, user.company_id)}


@router.post("/import")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db),
                     user: User = Depends(require_roles("Manager"))):
    raw = (await file.read()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(raw))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV is empty or has no data rows")
    return {"ok": True, **sample_data.import_carbon_csv(db, user.company_id, rows)}
