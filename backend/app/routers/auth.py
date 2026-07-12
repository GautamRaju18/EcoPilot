"""Auth: register (create or join a company), login (JWT), current user."""
import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db
from ..deps import get_current_user
from ..models import Company, User
from ..schemas import RegisterRequest, Token, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _make_code(db: Session, name: str) -> str:
    base = "".join(w[0] for w in re.findall(r"[A-Za-z]+", name)).upper()[:5] or name[:4].upper()
    code, n = base, 1
    while db.query(Company).filter(Company.code == code).first():
        n += 1
        code = f"{base}{n}"
    return code


@router.post("/register", response_model=Token)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    if payload.mode == "create":
        if not payload.company_name:
            raise HTTPException(status_code=400, detail="Company name is required to create a company")
        if db.query(Company).filter(Company.name == payload.company_name).first():
            raise HTTPException(status_code=400, detail="A company with that name already exists")
        company = Company(name=payload.company_name,
                          code=_make_code(db, payload.company_name),
                          industry=payload.industry)
        db.add(company)
        db.commit()
        db.refresh(company)
        role = "Admin"          # creator owns the company
    else:  # join existing
        company = db.query(Company).get(payload.company_id) if payload.company_id else None
        if not company:
            raise HTTPException(status_code=400, detail="Select a valid company to join")
        role = "Employee"

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=role,
        company_id=company.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role, "company_id": company.id})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form uses `username` — we treat it as the email.
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token({"sub": str(user.id), "role": user.role, "company_id": user.company_id})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
