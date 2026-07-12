"""Onboarding data helpers: populate a company with a believable starter
dataset, or import ESG data from an uploaded CSV. Used by the onboarding flow
so a brand-new company never faces an empty dashboard."""
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..ai.rag import invalidate_company
from ..ai.starter_docs import STARTER_GOALS, STARTER_POLICIES
from ..auth import hash_password
from ..models import (
    Audit, Badge, CarbonTransaction, Category, Challenge, ChallengeParticipation,
    Company, ComplianceIssue, CSRActivity, Department, EmissionFactor,
    EmployeeParticipation, EnvironmentalGoal, ESGPolicy, Reward, User,
)
from . import gamification, scoring

BADGES = [("First Steps", "🌱", "xp", 50), ("Green Contributor", "🍃", "xp", 200),
          ("Eco Warrior", "🌳", "xp", 500), ("Challenge Champion", "🏆", "completed_challenges", 5)]


def _uniq_dept_code(db: Session, base: str) -> str:
    code, n = base, 1
    while db.query(Department).filter(Department.code == code).first():
        n += 1
        code = f"{base}{n}"
    return code


def company_has_data(db: Session, company_id: int) -> bool:
    return db.query(Department).filter(Department.company_id == company_id).count() > 0


def populate_company(db: Session, company_id: int) -> dict:
    """Create a starter ESG dataset for an (empty) company and rebuild the RAG index."""
    company = db.query(Company).get(company_id)
    if not company:
        raise ValueError("Company not found")
    cid = company_id
    today = date.today()

    # Departments (globally-unique codes prefixed by company id)
    depts = []
    for dn in ["Operations", "Sustainability", "Facilities"]:
        d = Department(company_id=cid, name=dn,
                       code=_uniq_dept_code(db, f"C{cid}-{dn[:3].upper()}"),
                       head=f"{dn} Lead", employee_count=random.randint(10, 60), status="Active")
        db.add(d)
        db.flush()
        depts.append(d)

    # Sample employees (non-login demo users) with varied XP for a live leaderboard
    names = ["Alex Rivera", "Sam Okoro", "Jordan Lee", "Priya Nair", "Marco Rossi", "Yuki Tanaka"]
    for i, nm in enumerate(names):
        db.add(User(company_id=cid, email=f"emp{i}.c{cid}@sample.local",
                    hashed_password=hash_password("password123"), full_name=nm,
                    role="Employee", department_id=random.choice(depts).id,
                    xp=random.randint(80, 560), points_balance=random.randint(40, 320),
                    completed_challenges=random.randint(0, 6)))

    # Emission factors
    factors = {}
    for at, unit, val in [("electricity_kwh", "kWh", 0.82), ("diesel_liter", "liter", 2.68),
                          ("air_travel_km", "km", 0.15)]:
        f = EmissionFactor(company_id=cid, activity_type=at, unit=unit, co2e_per_unit=val)
        db.add(f)
        db.flush()
        factors[at] = f

    # Policies + goals (grounds the AI copilot)
    for p in STARTER_POLICIES:
        db.add(ESGPolicy(company_id=cid, **p))
    for g in STARTER_GOALS:
        db.add(EnvironmentalGoal(company_id=cid, department_id=depts[0].id, **g))

    for name, icon, metric, thr in BADGES:
        db.add(Badge(company_id=cid, name=name, icon=icon, rule_metric=metric, rule_threshold=thr))
    db.add_all([
        Reward(company_id=cid, name="Reusable Bottle", points_required=100, stock=25, status="Active"),
        Reward(company_id=cid, name="Extra Day Off", points_required=500, stock=5, status="Active"),
        Reward(company_id=cid, name="Eco Tote Bag", points_required=80, stock=30, status="Active"),
    ])

    # Carbon transactions (randomised so each company looks different)
    for i in range(random.randint(4, 7)):
        at = random.choice(list(factors))
        qty = random.randint(1000, 15000)
        db.add(CarbonTransaction(company_id=cid, source_ref=f"SEED-{i+1}", source_type="Manual",
                                 emission_factor_id=factors[at].id, quantity=qty,
                                 co2e=round(qty * factors[at].co2e_per_unit, 1),
                                 department_id=random.choice(depts).id,
                                 date=today - timedelta(days=random.randint(1, 40))))

    # Categories + a CSR activity with approved participations
    cat_csr = Category(company_id=cid, name="Community Drive", type="CSR Activity")
    cat_ch = Category(company_id=cid, name="Energy Saving", type="Challenge")
    db.add_all([cat_csr, cat_ch])
    db.flush()
    act = CSRActivity(company_id=cid, title="Neighbourhood Tree Plantation", category_id=cat_csr.id,
                      description="Plant trees in the local park.", points=50,
                      date=today - timedelta(days=5), department_id=depts[0].id)
    db.add(act)
    db.flush()
    emps = db.query(User).filter(User.company_id == cid).all()
    for u in emps[:2]:
        db.add(EmployeeParticipation(company_id=cid, user_id=u.id, activity_id=act.id,
                                     proof_file="seed_proof_placeholder.jpg",
                                     approval_status="Approved", points_earned=50,
                                     completion_date=today - timedelta(days=3)))

    # An active challenge + a pending submission to approve
    ch = Challenge(company_id=cid, title="Reduce Office Energy 15%", category_id=cat_ch.id,
                   description="Cut workspace energy use by 15%.", xp=100, difficulty="Medium",
                   evidence_required=True, deadline=today + timedelta(days=7), status="Active")
    db.add(ch)
    db.flush()
    if emps:
        db.add(ChallengeParticipation(company_id=cid, challenge_id=ch.id, user_id=emps[0].id,
                                      progress=100, proof_file="seed_proof_placeholder.jpg",
                                      approval_status="Pending"))

    # Governance
    audit = Audit(company_id=cid, scope="Baseline ESG Audit", date=today - timedelta(days=15),
                  auditor="Internal team", findings="Initial assessment complete.")
    db.add(audit)
    db.flush()
    db.add(ComplianceIssue(company_id=cid, audit_id=audit.id, severity="Medium",
                           description="Emission tracking not yet automated for all departments.",
                           owner=depts[0].head, due_date=today + timedelta(days=30), status="Open"))
    db.commit()

    # Award badges, compute scores, refresh the RAG index
    for u in db.query(User).filter(User.company_id == cid).all():
        gamification.check_and_award_badges(db, u)
    scoring.recompute_all(db, cid)
    invalidate_company(cid)

    return {
        "departments": len(depts),
        "employees": len(names),
        "policies": len(STARTER_POLICIES),
        **scoring.overall_scores(db, cid),
    }


# --------------------------------------------------------------------------- #
def _num(v):
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def import_carbon_csv(db: Session, company_id: int, rows: list[dict]) -> dict:
    """Import ESG carbon rows. Recognised columns (case-insensitive):
    department, activity_type, unit, quantity, co2e_per_unit, co2e, date, source_ref.
    Departments and emission factors are created on demand."""
    dept_cache = {d.name.lower(): d for d in
                  db.query(Department).filter(Department.company_id == company_id).all()}
    factor_cache = {f.activity_type.lower(): f for f in
                    db.query(EmissionFactor).filter(EmissionFactor.company_id == company_id).all()}
    created, skipped = 0, 0

    for raw in rows:
        row = {(k or "").strip().lower(): v for k, v in raw.items()}
        dept_name = (row.get("department") or "General").strip()
        key = dept_name.lower()
        dept = dept_cache.get(key)
        if not dept:
            dept = Department(company_id=company_id, name=dept_name,
                              code=_uniq_dept_code(db, f"C{company_id}-{dept_name[:3].upper()}"),
                              status="Active")
            db.add(dept)
            db.flush()
            dept_cache[key] = dept

        activity = (row.get("activity_type") or "").strip()
        cpu = _num(row.get("co2e_per_unit"))
        qty = _num(row.get("quantity")) or 0.0
        co2e = _num(row.get("co2e"))

        factor = None
        if activity:
            factor = factor_cache.get(activity.lower())
            if not factor:
                factor = EmissionFactor(company_id=company_id, activity_type=activity,
                                        unit=(row.get("unit") or "unit").strip(),
                                        co2e_per_unit=cpu or 0.0)
                db.add(factor)
                db.flush()
                factor_cache[activity.lower()] = factor

        if co2e is None:
            co2e = round(qty * (cpu if cpu is not None else (factor.co2e_per_unit if factor else 0.0)), 3)
        if co2e is None:
            skipped += 1
            continue

        db.add(CarbonTransaction(company_id=company_id,
                                 source_ref=(row.get("source_ref") or "CSV").strip(),
                                 source_type="Import",
                                 emission_factor_id=factor.id if factor else None,
                                 quantity=qty, co2e=co2e, department_id=dept.id,
                                 date=date.today()))
        created += 1

    db.commit()
    scoring.recompute_all(db, company_id)
    return {"imported": created, "skipped": skipped, **scoring.overall_scores(db, company_id)}
