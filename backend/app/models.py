"""SQLAlchemy models — the full EcoPilot data model (Section 3).

Naming keeps close to the spec. `User` doubles as the Employee record
(auth + points balance + XP + completed-challenge count for badge rules).
"""
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from .database import Base


# --------------------------------------------------------------------------- #
# Company (tenant) — every other record belongs to exactly one company
# --------------------------------------------------------------------------- #
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    code = Column(String, unique=True, index=True)
    industry = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# --------------------------------------------------------------------------- #
# Users / Employees
# --------------------------------------------------------------------------- #
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="Employee")  # Employee / Manager / Admin
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)

    # Gamification state
    points_balance = Column(Integer, default=0)   # spendable CSR points
    xp = Column(Integer, default=0)               # experience from challenges
    completed_challenges = Column(Integer, default=0)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="employees")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    company = relationship("Company")


# --------------------------------------------------------------------------- #
# Master Data
# --------------------------------------------------------------------------- #
class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    name = Column(String, nullable=False)
    code = Column(String, unique=True, index=True)
    head = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    employee_count = Column(Integer, default=0)
    status = Column(String, default="Active")

    employees = relationship("User", back_populates="department")
    parent = relationship("Department", remote_side=[id])


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)   # "CSR Activity" | "Challenge"
    status = Column(String, default="Active")


class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    activity_type = Column(String, index=True, nullable=False)  # e.g. "electricity_kwh"
    unit = Column(String, default="unit")                        # e.g. "kWh", "liter", "km"
    co2e_per_unit = Column(Float, nullable=False)                # kg CO2e per unit
    description = Column(String, nullable=True)


class ProductESGProfile(Base):
    __tablename__ = "product_esg_profiles"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    product = Column(String, nullable=False)
    carbon_footprint = Column(Float, default=0.0)     # kg CO2e
    recyclable_pct = Column(Float, default=0.0)
    ethical_sourcing = Column(String, nullable=True)  # e.g. "Fair Trade"
    esg_rating = Column(String, nullable=True)        # A / B / C


class EnvironmentalGoal(Base):
    __tablename__ = "environmental_goals"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    target_metric = Column(String, nullable=False)    # e.g. "Manufacturing CO2e"
    target_value = Column(Float, nullable=False)
    unit = Column(String, default="tCO2e")
    deadline = Column(Date, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    current_value = Column(Float, default=0.0)

    department = relationship("Department")


class ESGPolicy(Base):
    __tablename__ = "esg_policies"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    title = Column(String, nullable=False)
    document = Column(Text, nullable=False)            # full policy text (ingested by RAG)
    category = Column(String, nullable=False)          # Environmental / Social / Governance
    version = Column(String, default="1.0")
    created_at = Column(DateTime, default=datetime.utcnow)


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True)               # emoji or icon name
    # Unlock rule (Business Rule 4): metric + threshold
    rule_metric = Column(String, default="xp")         # "xp" | "completed_challenges" | "points_balance"
    rule_threshold = Column(Integer, default=100)


class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    points_required = Column(Integer, nullable=False)
    stock = Column(Integer, default=0)
    status = Column(String, default="Active")


# --------------------------------------------------------------------------- #
# Transactional Data
# --------------------------------------------------------------------------- #
class CarbonTransaction(Base):
    __tablename__ = "carbon_transactions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    source_ref = Column(String, nullable=True)         # e.g. "PO-1042" / "Fleet-7"
    source_type = Column(String, default="Manual")     # Purchase/Manufacturing/Expense/Fleet/Manual
    emission_factor_id = Column(Integer, ForeignKey("emission_factors.id"), nullable=True)
    quantity = Column(Float, default=0.0)              # units of activity
    co2e = Column(Float, default=0.0)                  # calculated kg CO2e
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    date = Column(Date, default=date.today)

    emission_factor = relationship("EmissionFactor")
    department = relationship("Department")


class CSRActivity(Base):
    __tablename__ = "csr_activities"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    title = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    description = Column(Text, nullable=True)
    points = Column(Integer, default=50)               # points awarded on approval
    date = Column(Date, default=date.today)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)

    category = relationship("Category")
    department = relationship("Department")


class EmployeeParticipation(Base):
    """Employee participation in a CSR Activity."""
    __tablename__ = "employee_participations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("csr_activities.id"), nullable=False)
    proof_file = Column(String, nullable=True)         # uploaded evidence path
    approval_status = Column(String, default="Pending")  # Pending / Approved / Rejected
    points_earned = Column(Integer, default=0)
    completion_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    activity = relationship("CSRActivity")


class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    title = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    description = Column(Text, nullable=True)
    xp = Column(Integer, default=100)
    difficulty = Column(String, default="Medium")      # Easy / Medium / Hard
    evidence_required = Column(Boolean, default=True)
    deadline = Column(Date, nullable=True)
    status = Column(String, default="Draft")           # Draft/Active/Under Review/Completed/Archived

    category = relationship("Category")


class ChallengeParticipation(Base):
    __tablename__ = "challenge_participations"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    progress = Column(Integer, default=0)              # 0-100
    proof_file = Column(String, nullable=True)
    approval_status = Column(String, default="Pending")  # Pending / Approved / Rejected
    xp_awarded = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    challenge = relationship("Challenge")
    user = relationship("User")


class PolicyAcknowledgement(Base):
    __tablename__ = "policy_acknowledgements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    policy_id = Column(Integer, ForeignKey("esg_policies.id"), nullable=False)
    date_acknowledged = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    policy = relationship("ESGPolicy")


class Audit(Base):
    __tablename__ = "audits"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    scope = Column(String, nullable=False)
    date = Column(Date, default=date.today)
    auditor = Column(String, nullable=True)
    findings = Column(Text, nullable=True)


class ComplianceIssue(Base):
    __tablename__ = "compliance_issues"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    audit_id = Column(Integer, ForeignKey("audits.id"), nullable=True)
    severity = Column(String, default="Medium")        # Low / Medium / High / Critical
    description = Column(Text, nullable=False)
    owner = Column(String, nullable=False)             # Business Rule 7: required
    due_date = Column(Date, nullable=False)            # Business Rule 7: required
    status = Column(String, default="Open")            # Open / In Progress / Resolved

    audit = relationship("Audit")


class DepartmentScore(Base):
    __tablename__ = "department_scores"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    department_id = Column(Integer, ForeignKey("departments.id"), unique=True, nullable=False)
    environmental_score = Column(Float, default=0.0)
    social_score = Column(Float, default=0.0)
    governance_score = Column(Float, default=0.0)
    total_score = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    department = relationship("Department")


# --------------------------------------------------------------------------- #
# Supporting tables (gamification + notifications)
# --------------------------------------------------------------------------- #
class UserBadge(Base):
    """Badges auto-awarded to a user (Business Rule 4)."""
    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    awarded_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="badges")
    badge = relationship("Badge")


class Redemption(Base):
    """Reward redemption record (Business Rule 5)."""
    __tablename__ = "redemptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reward_id = Column(Integer, ForeignKey("rewards.id"), nullable=False)
    points_spent = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    reward = relationship("Reward")


class Notification(Base):
    """In-app notification (Business Rule 8 — no email)."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = broadcast
    title = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    type = Column(String, default="info")   # info / approval / badge / compliance / reminder
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    """Persisted Ask EcoPilot conversation, per user — survives across devices."""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), index=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    role = Column(String, nullable=False)          # "user" | "bot"
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)          # JSON-encoded list of source dicts
    provider = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
