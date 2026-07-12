"""Governance — thin CRUD (Scope Cut): audits + compliance issues.
Compliance issues require Owner + Due Date (Rule 7); overdue Open issues
are flagged. Creating an issue raises an in-app notification (Rule 8)."""
from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_roles
from ..models import Audit, ComplianceIssue, User
from ..schemas import (
    AuditCreate, AuditOut, ComplianceIssueCreate, ComplianceIssueOut,
)
from ..services.notifications import notify

router = APIRouter(prefix="/api/governance", tags=["governance"])


# ------------------------------- Audits ------------------------------------ #
@router.get("/audits", response_model=list[AuditOut])
def list_audits(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return (db.query(Audit).filter(Audit.company_id == user.company_id)
            .order_by(Audit.date.desc()).all())


@router.post("/audits", response_model=AuditOut)
def create_audit(payload: AuditCreate, db: Session = Depends(get_db),
                 user: User = Depends(require_roles("Manager"))):
    audit = Audit(**payload.model_dump(), company_id=user.company_id)
    if not audit.date:
        audit.date = date.today()
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return audit


# -------------------------- Compliance issues ------------------------------ #
def _to_out(issue: ComplianceIssue) -> ComplianceIssueOut:
    out = ComplianceIssueOut.model_validate(issue)
    out.overdue = bool(issue.status != "Resolved" and issue.due_date
                       and issue.due_date < date.today())
    return out


@router.get("/issues", response_model=list[ComplianceIssueOut])
def list_issues(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return [_to_out(i) for i in
            db.query(ComplianceIssue).filter(ComplianceIssue.company_id == user.company_id).all()]


@router.post("/issues", response_model=ComplianceIssueOut)
def create_issue(payload: ComplianceIssueCreate, db: Session = Depends(get_db),
                 user: User = Depends(require_roles("Manager"))):
    # Rule 7 — Owner + Due Date are required (enforced by the schema types too)
    if not payload.owner or not payload.due_date:
        raise HTTPException(status_code=400, detail="Owner and Due Date are required")
    issue = ComplianceIssue(**payload.model_dump(), company_id=user.company_id)
    db.add(issue)
    db.commit()
    db.refresh(issue)
    notify(db, title=f"New compliance issue: {issue.severity}",
           message=f"{issue.description[:80]} — owner {issue.owner}, due {issue.due_date}",
           type="compliance", company_id=user.company_id)
    return _to_out(issue)


@router.post("/issues/{issue_id}/status", response_model=ComplianceIssueOut)
def update_status(issue_id: int, status: str = Body(..., embed=True),
                  db: Session = Depends(get_db), _: User = Depends(require_roles("Manager"))):
    issue = db.query(ComplianceIssue).get(issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.status = status
    db.commit()
    db.refresh(issue)
    return _to_out(issue)
