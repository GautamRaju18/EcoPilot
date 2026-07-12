"""Pydantic v2 schemas for requests/responses."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

# Alias so fields literally named `date` don't shadow the `date` type within
# their own class body (which would make Pydantic resolve them to NoneType).
DateT = date


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ------------------------------- Auth -------------------------------------- #
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "Employee"
    department_id: Optional[int] = None


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    role: str
    department_id: Optional[int] = None
    points_balance: int = 0
    xp: int = 0
    completed_challenges: int = 0


# ----------------------------- Master data --------------------------------- #
class DepartmentCreate(BaseModel):
    name: str
    code: str
    head: Optional[str] = None
    parent_id: Optional[int] = None
    employee_count: int = 0
    status: str = "Active"


class DepartmentOut(ORM):
    id: int
    name: str
    code: str
    head: Optional[str] = None
    parent_id: Optional[int] = None
    employee_count: int = 0
    status: str


class CategoryCreate(BaseModel):
    name: str
    type: str
    status: str = "Active"


class CategoryOut(ORM):
    id: int
    name: str
    type: str
    status: str


class EmissionFactorCreate(BaseModel):
    activity_type: str
    unit: str = "unit"
    co2e_per_unit: float
    description: Optional[str] = None


class EmissionFactorOut(ORM):
    id: int
    activity_type: str
    unit: str
    co2e_per_unit: float
    description: Optional[str] = None


class ProductCreate(BaseModel):
    product: str
    carbon_footprint: float = 0.0
    recyclable_pct: float = 0.0
    ethical_sourcing: Optional[str] = None
    esg_rating: Optional[str] = None


class ProductOut(ORM):
    id: int
    product: str
    carbon_footprint: float
    recyclable_pct: float
    ethical_sourcing: Optional[str] = None
    esg_rating: Optional[str] = None


class GoalCreate(BaseModel):
    target_metric: str
    target_value: float
    unit: str = "tCO2e"
    deadline: Optional[date] = None
    department_id: Optional[int] = None
    current_value: float = 0.0


class GoalOut(ORM):
    id: int
    target_metric: str
    target_value: float
    unit: str
    deadline: Optional[date] = None
    department_id: Optional[int] = None
    current_value: float


class PolicyCreate(BaseModel):
    title: str
    document: str
    category: str
    version: str = "1.0"


class PolicyOut(ORM):
    id: int
    title: str
    document: str
    category: str
    version: str
    created_at: datetime


class BadgeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    rule_metric: str = "xp"
    rule_threshold: int = 100


class BadgeOut(ORM):
    id: int
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    rule_metric: str
    rule_threshold: int


class RewardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    points_required: int
    stock: int = 0
    status: str = "Active"


class RewardOut(ORM):
    id: int
    name: str
    description: Optional[str] = None
    points_required: int
    stock: int
    status: str


# --------------------------- Transactional --------------------------------- #
class CarbonTransactionCreate(BaseModel):
    source_ref: Optional[str] = None
    source_type: str = "Manual"
    emission_factor_id: Optional[int] = None
    quantity: float = 0.0
    co2e: Optional[float] = None  # if omitted and auto-calc on, computed from factor
    department_id: Optional[int] = None
    date: Optional[DateT] = None


class CarbonTransactionOut(ORM):
    id: int
    source_ref: Optional[str] = None
    source_type: str
    emission_factor_id: Optional[int] = None
    quantity: float
    co2e: float
    department_id: Optional[int] = None
    date: Optional[DateT] = None


class CSRActivityCreate(BaseModel):
    title: str
    category_id: Optional[int] = None
    description: Optional[str] = None
    points: int = 50
    date: Optional[DateT] = None
    department_id: Optional[int] = None


class CSRActivityOut(ORM):
    id: int
    title: str
    category_id: Optional[int] = None
    description: Optional[str] = None
    points: int
    date: Optional[DateT] = None
    department_id: Optional[int] = None


class ParticipationOut(ORM):
    id: int
    user_id: int
    activity_id: int
    proof_file: Optional[str] = None
    approval_status: str
    points_earned: int
    completion_date: Optional[date] = None


class ChallengeCreate(BaseModel):
    title: str
    category_id: Optional[int] = None
    description: Optional[str] = None
    xp: int = 100
    difficulty: str = "Medium"
    evidence_required: bool = True
    deadline: Optional[date] = None
    status: str = "Draft"


class ChallengeOut(ORM):
    id: int
    title: str
    category_id: Optional[int] = None
    description: Optional[str] = None
    xp: int
    difficulty: str
    evidence_required: bool
    deadline: Optional[date] = None
    status: str


class ChallengeParticipationOut(ORM):
    id: int
    challenge_id: int
    user_id: int
    progress: int
    proof_file: Optional[str] = None
    approval_status: str
    xp_awarded: int


class AuditCreate(BaseModel):
    scope: str
    date: Optional[DateT] = None
    auditor: Optional[str] = None
    findings: Optional[str] = None


class AuditOut(ORM):
    id: int
    scope: str
    date: Optional[DateT] = None
    auditor: Optional[str] = None
    findings: Optional[str] = None


class ComplianceIssueCreate(BaseModel):
    audit_id: Optional[int] = None
    severity: str = "Medium"
    description: str
    owner: str
    due_date: date
    status: str = "Open"


class ComplianceIssueOut(ORM):
    id: int
    audit_id: Optional[int] = None
    severity: str
    description: str
    owner: str
    due_date: date
    status: str
    overdue: bool = False  # computed in router


class DepartmentScoreOut(ORM):
    id: int
    department_id: int
    environmental_score: float
    social_score: float
    governance_score: float
    total_score: float


# ----------------------------- Gamification -------------------------------- #
class UserBadgeOut(BaseModel):
    badge: BadgeOut
    awarded_at: datetime
    model_config = ConfigDict(from_attributes=True)


class LeaderboardEntry(BaseModel):
    user_id: int
    full_name: str
    department: Optional[str] = None
    xp: int
    points_balance: int
    completed_challenges: int
    badge_count: int


class RedeemRequest(BaseModel):
    reward_id: int


# ---------------------------- Notifications -------------------------------- #
class NotificationOut(ORM):
    id: int
    title: str
    message: Optional[str] = None
    type: str
    is_read: bool
    created_at: datetime


# ------------------------------- AI ---------------------------------------- #
class CopilotQuery(BaseModel):
    question: str


class CopilotSource(BaseModel):
    title: str
    snippet: str
    score: float


class CopilotResponse(BaseModel):
    answer: str
    sources: list[CopilotSource]
    provider: str


class ReportRequest(BaseModel):
    department_id: Optional[int] = None  # None = whole-org report


class ReportResponse(BaseModel):
    title: str
    narrative: str
    overall_score: float
    provider: str
    generated_at: datetime


Token.model_rebuild()
