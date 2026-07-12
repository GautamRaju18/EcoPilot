"""Seed EcoPilot with realistic, demo-choreographed data.

Run:  python -m app.seed        (from the backend/ directory)

Choreography for the live demo (maps to the Definition of Done):
  * Overall ESG score is populated from real department scores.
  * Manufacturing has high emissions -> lowest Environmental score (log a new
    carbon transaction live to push it lower).
  * A CSR activity has a PENDING participation *with proof* -> approve it live
    to award points and lift Social.
  * Employee 'Priya' sits at 450 XP / 4 completed challenges with a PENDING
    challenge worth 100 XP. Approving it -> 550 XP + 5 completed, which unlocks
    TWO badges (Eco Warrior, Challenge Champion) and moves the leaderboard.
  * Policies + goals are ingested so 'Ask EcoPilot' answers are grounded, e.g.
    "what's our current emission target for manufacturing?".
"""
from datetime import date, timedelta

from .database import Base, SessionLocal, engine
from .models import (
    Audit, Badge, CarbonTransaction, Category, Challenge, ChallengeParticipation,
    ComplianceIssue, CSRActivity, Department, EmissionFactor, EmployeeParticipation,
    EnvironmentalGoal, ESGPolicy, PolicyAcknowledgement, ProductESGProfile, Reward,
    User,
)
from .auth import hash_password
from .services import gamification, scoring
from .ai.rag import index

POLICIES = [
    dict(
        title="Environmental Sustainability Policy",
        category="Environmental",
        version="2.1",
        document=(
            "GreenCore Industries is committed to achieving net-zero carbon emissions "
            "by 2040. Our interim target is a 30% reduction in Scope 1 and Scope 2 "
            "emissions by 2026 against a 2022 baseline. The Manufacturing division, our "
            "largest emitter, must reduce its annual footprint to 500 tCO2e by December "
            "2026. All facilities are required to source at least 50% of electricity from "
            "renewable providers by 2026 and to divert 80% of operational waste from "
            "landfill. Fleet vehicles must transition to electric or hybrid by 2028. "
            "Department heads are accountable for quarterly emission reporting, and any "
            "capital purchase above 10,000 units must include a carbon impact assessment."
        ),
    ),
    dict(
        title="Corporate Social Responsibility & Community Policy",
        category="Social",
        version="1.4",
        document=(
            "GreenCore encourages every employee to contribute at least 16 volunteer "
            "hours per year to approved CSR activities. Recognised activities include "
            "tree plantation drives, community education, blood donation, and local "
            "clean-up campaigns. Participation is rewarded with points redeemable for "
            "company rewards. The company matches employee charitable donations up to "
            "200 units per person annually. Diversity commitments include maintaining at "
            "least 40% women in the workforce and 30% women in leadership by 2027. All "
            "CSR participation must be evidenced with photographic or documentary proof "
            "before points are awarded."
        ),
    ),
    dict(
        title="Governance, Ethics & Compliance Policy",
        category="Governance",
        version="3.0",
        document=(
            "GreenCore maintains a zero-tolerance stance on bribery and corruption. All "
            "employees must acknowledge the Code of Conduct annually. Internal ESG audits "
            "are conducted twice per year, and every identified compliance issue must have "
            "a named owner and a resolution due date. High-severity issues must be resolved "
            "within 30 days. The Board's ESG committee reviews the weighted ESG scorecard "
            "quarterly, where the overall score is calculated as 40% Environmental, 30% "
            "Social, and 30% Governance. Whistle-blower reports are handled confidentially "
            "and investigated within 14 days."
        ),
    ),
]


def run():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ---------------- Departments ----------------
        manufacturing = Department(name="Manufacturing", code="MFG", head="R. Kapoor",
                                   employee_count=120, status="Active")
        operations = Department(name="Operations", code="OPS", head="S. Mehta",
                                employee_count=80, status="Active")
        hr = Department(name="Human Resources", code="HR", head="A. Nair",
                        employee_count=25, status="Active")
        rnd = Department(name="R&D", code="RND", head="K. Sharma",
                         employee_count=40, status="Active")
        db.add_all([manufacturing, operations, hr, rnd])
        db.commit()

        # ---------------- Users ----------------
        admin = User(email="admin@ecopilot.com", hashed_password=hash_password("admin123"),
                     full_name="Ava Admin", role="Admin", department_id=operations.id,
                     xp=300, points_balance=150, completed_challenges=3)
        manager = User(email="manager@ecopilot.com", hashed_password=hash_password("manager123"),
                       full_name="Marcus Manager", role="Manager",
                       department_id=manufacturing.id, xp=260, points_balance=120,
                       completed_challenges=2)
        priya = User(email="priya@ecopilot.com", hashed_password=hash_password("priya123"),
                     full_name="Priya Sharma", role="Employee", department_id=manufacturing.id,
                     xp=450, points_balance=280, completed_challenges=4)
        raj = User(email="raj@ecopilot.com", hashed_password=hash_password("password123"),
                   full_name="Raj Patel", role="Employee", department_id=operations.id,
                   xp=180, points_balance=90, completed_challenges=1)
        lena = User(email="lena@ecopilot.com", hashed_password=hash_password("password123"),
                    full_name="Lena Fischer", role="Employee", department_id=rnd.id,
                    xp=520, points_balance=340, completed_challenges=5)
        db.add_all([admin, manager, priya, raj, lena])
        db.commit()

        # ---------------- Categories ----------------
        cat_tree = Category(name="Tree Plantation", type="CSR Activity")
        cat_clean = Category(name="Clean-up Drive", type="CSR Activity")
        cat_energy = Category(name="Energy Saving", type="Challenge")
        cat_waste = Category(name="Waste Reduction", type="Challenge")
        db.add_all([cat_tree, cat_clean, cat_energy, cat_waste])
        db.commit()

        # ---------------- Emission factors ----------------
        ef_elec = EmissionFactor(activity_type="electricity_kwh", unit="kWh",
                                 co2e_per_unit=0.82, description="Grid electricity")
        ef_diesel = EmissionFactor(activity_type="diesel_liter", unit="liter",
                                   co2e_per_unit=2.68, description="Fleet diesel")
        ef_flight = EmissionFactor(activity_type="air_travel_km", unit="km",
                                   co2e_per_unit=0.15, description="Business air travel")
        ef_steel = EmissionFactor(activity_type="steel_kg", unit="kg",
                                  co2e_per_unit=1.85, description="Raw steel")
        db.add_all([ef_elec, ef_diesel, ef_flight, ef_steel])
        db.commit()

        # ---------------- Products ----------------
        db.add_all([
            ProductESGProfile(product="EcoWidget A", carbon_footprint=12.4,
                              recyclable_pct=85, ethical_sourcing="Fair Trade", esg_rating="A"),
            ProductESGProfile(product="Standard Widget", carbon_footprint=41.0,
                              recyclable_pct=40, ethical_sourcing="Conventional", esg_rating="C"),
        ])

        # ---------------- Environmental goals ----------------
        db.add_all([
            EnvironmentalGoal(target_metric="Manufacturing CO2e Reduction",
                              target_value=500, unit="tCO2e",
                              deadline=date(2026, 12, 31), department_id=manufacturing.id,
                              current_value=720),
            EnvironmentalGoal(target_metric="Renewable Electricity Share",
                              target_value=50, unit="%",
                              deadline=date(2026, 12, 31), department_id=operations.id,
                              current_value=32),
        ])

        # ---------------- Policies (RAG corpus) ----------------
        for p in POLICIES:
            db.add(ESGPolicy(**p))
        db.commit()

        # ---------------- Badges (unlock rules) ----------------
        b_first = Badge(name="First Steps", description="Earn your first 50 XP",
                        icon="🌱", rule_metric="xp", rule_threshold=50)
        b_green = Badge(name="Green Contributor", description="Reach 200 XP",
                        icon="🍃", rule_metric="xp", rule_threshold=200)
        b_warrior = Badge(name="Eco Warrior", description="Reach 500 XP",
                          icon="🌳", rule_metric="xp", rule_threshold=500)
        b_champion = Badge(name="Challenge Champion", description="Complete 5 challenges",
                           icon="🏆", rule_metric="completed_challenges", rule_threshold=5)
        db.add_all([b_first, b_green, b_warrior, b_champion])
        db.commit()

        # ---------------- Rewards ----------------
        db.add_all([
            Reward(name="Reusable Water Bottle", description="Branded steel bottle",
                   points_required=100, stock=25, status="Active"),
            Reward(name="Extra Day Off", description="One paid day off",
                   points_required=500, stock=5, status="Active"),
            Reward(name="Plant a Tree in Your Name", description="We plant a tree for you",
                   points_required=50, stock=0, status="Active"),  # out of stock (demo block)
        ])
        db.commit()

        # ---------------- Carbon transactions ----------------
        today = date.today()
        db.add_all([
            CarbonTransaction(source_ref="MFG-Q1", source_type="Manufacturing",
                              emission_factor_id=ef_steel.id, quantity=30000, co2e=55500,
                              department_id=manufacturing.id, date=today - timedelta(days=40)),
            CarbonTransaction(source_ref="MFG-ELEC", source_type="Expense",
                              emission_factor_id=ef_elec.id, quantity=20000, co2e=16400,
                              department_id=manufacturing.id, date=today - timedelta(days=20)),
            CarbonTransaction(source_ref="OPS-FLEET", source_type="Fleet",
                              emission_factor_id=ef_diesel.id, quantity=4000, co2e=10720,
                              department_id=operations.id, date=today - timedelta(days=15)),
            CarbonTransaction(source_ref="RND-TRAVEL", source_type="Expense",
                              emission_factor_id=ef_flight.id, quantity=8000, co2e=1200,
                              department_id=rnd.id, date=today - timedelta(days=10)),
        ])
        db.commit()

        # ---------------- CSR activity + PENDING participation (with proof) ----------------
        tree_drive = CSRActivity(title="City Tree Plantation Drive", category_id=cat_tree.id,
                                 description="Plant 500 saplings in the city park.",
                                 points=60, date=today - timedelta(days=3),
                                 department_id=manufacturing.id)
        db.add(tree_drive)
        db.commit()
        db.add(EmployeeParticipation(user_id=raj.id, activity_id=tree_drive.id,
                                     proof_file="seed_proof_placeholder.jpg",
                                     approval_status="Pending"))
        # An already-approved one so Social isn't zero
        db.add(EmployeeParticipation(user_id=priya.id, activity_id=tree_drive.id,
                                     proof_file="seed_proof_placeholder.jpg",
                                     approval_status="Approved", points_earned=60,
                                     completion_date=today - timedelta(days=2)))
        db.commit()

        # ---------------- Challenges + PENDING participation (badge trigger) -------------
        ch_active = Challenge(title="Reduce Office Energy 15%", category_id=cat_energy.id,
                              description="Cut your workspace energy use by 15% this month.",
                              xp=100, difficulty="Medium", evidence_required=True,
                              deadline=today + timedelta(days=7), status="Active")
        ch_review = Challenge(title="Zero Single-Use Plastic Week", category_id=cat_waste.id,
                              description="Go a full week without single-use plastic.",
                              xp=80, difficulty="Easy", evidence_required=True,
                              deadline=today + timedelta(days=3), status="Under Review")
        ch_draft = Challenge(title="Carpool Challenge", category_id=cat_energy.id,
                             description="Organise a carpool for your team.",
                             xp=120, difficulty="Hard", evidence_required=True,
                             status="Draft")
        db.add_all([ch_active, ch_review, ch_draft])
        db.commit()

        # Priya's PENDING challenge submission — approving unlocks 2 badges live
        db.add(ChallengeParticipation(challenge_id=ch_active.id, user_id=priya.id,
                                      progress=100, proof_file="seed_proof_placeholder.jpg",
                                      approval_status="Pending"))
        db.commit()

        # ---------------- Governance: audit + compliance issues ----------------
        audit = Audit(scope="Annual ESG Internal Audit", date=today - timedelta(days=30),
                      auditor="Deloitte (external)",
                      findings="Renewable share below target; two open safety issues.")
        db.add(audit)
        db.commit()
        db.add_all([
            ComplianceIssue(audit_id=audit.id, severity="High",
                            description="Renewable electricity share (32%) below 2026 target of 50%.",
                            owner="S. Mehta", due_date=today - timedelta(days=5),  # OVERDUE
                            status="Open"),
            ComplianceIssue(audit_id=audit.id, severity="Medium",
                            description="Three department heads missed Q1 emission reporting.",
                            owner="R. Kapoor", due_date=today + timedelta(days=20),
                            status="In Progress"),
        ])
        db.commit()

        # ---------------- Policy acknowledgements ----------------
        first_policy = db.query(ESGPolicy).first()
        db.add_all([
            PolicyAcknowledgement(user_id=priya.id, policy_id=first_policy.id),
            PolicyAcknowledgement(user_id=raj.id, policy_id=first_policy.id),
        ])
        db.commit()

        # ---------------- Auto-award existing badges + compute scores ----------------
        for u in db.query(User).all():
            gamification.check_and_award_badges(db, u)
        scoring.recompute_all(db)

        # ---------------- Build RAG index ----------------
        n = index.build(db)

        overall = scoring.overall_scores(db)
        print("\n=== EcoPilot seed complete ===")
        print(f"Departments: {db.query(Department).count()}  Users: {db.query(User).count()}")
        print(f"RAG indexed chunks: {n} (backend: {index.backend})")
        print(f"Overall ESG score: {overall['overall']}  "
              f"(E {overall['environmental']} / S {overall['social']} / G {overall['governance']})")
        print("\nLogin credentials:")
        print("  Admin    : admin@ecopilot.com   / admin123")
        print("  Manager  : manager@ecopilot.com / manager123")
        print("  Employee : priya@ecopilot.com   / priya123   (450 XP — approve her challenge to unlock 2 badges)")
        print("  Employee : raj@ecopilot.com     / password123 (has a pending CSR to approve)")
        print("  Employee : lena@ecopilot.com    / password123")
        print("\nDemo: log in as manager -> approve Priya's 'Reduce Office Energy 15%' challenge "
              "-> watch Eco Warrior + Challenge Champion unlock on the leaderboard.\n")
    finally:
        db.close()


if __name__ == "__main__":
    run()
