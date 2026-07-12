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
    Company, ComplianceIssue, CSRActivity, Department, EmissionFactor,
    EmployeeParticipation, EnvironmentalGoal, ESGPolicy, PolicyAcknowledgement,
    ProductESGProfile, Reward, User,
)

# Models that carry a company_id (used to tag the primary demo company in bulk)
TENANT_MODELS = [
    Department, Category, EmissionFactor, ProductESGProfile, EnvironmentalGoal,
    ESGPolicy, Badge, Reward, CarbonTransaction, CSRActivity, EmployeeParticipation,
    Challenge, ChallengeParticipation, Audit, ComplianceIssue, User,
]
from .auth import hash_password
from .services import gamification, scoring
from .ai.rag import invalidate_company

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


def add_company(db, *, name, code, industry, admin_email, admin_pw,
                dept_specs, employees, carbon_specs, policies, goals,
                overdue_issues=1, approved_csr=2):
    """Build a compact but complete second/third tenant so the cross-company
    ESG ranking and per-company isolation are demonstrable."""
    company = Company(name=name, code=code, industry=industry)
    db.add(company)
    db.commit()
    db.refresh(company)
    cid = company.id
    today = date.today()

    depts = {}
    for dname, dcode, head, count in dept_specs:
        d = Department(company_id=cid, name=dname, code=dcode, head=head,
                       employee_count=count, status="Active")
        db.add(d)
        db.flush()
        depts[dcode] = d

    admin = User(company_id=cid, email=admin_email, hashed_password=hash_password(admin_pw),
                 full_name=f"{name.split()[0]} Admin", role="Admin",
                 department_id=list(depts.values())[0].id, xp=280, points_balance=140,
                 completed_challenges=2)
    db.add(admin)
    users = [admin]
    for fname, mail, dcode, xp, pts, done in employees:
        u = User(company_id=cid, email=mail, hashed_password=hash_password("password123"),
                 full_name=fname, role="Employee", department_id=depts[dcode].id,
                 xp=xp, points_balance=pts, completed_challenges=done)
        db.add(u)
        users.append(u)
    db.commit()

    cat_csr = Category(company_id=cid, name="Community Drive", type="CSR Activity")
    cat_ch = Category(company_id=cid, name="Energy Saving", type="Challenge")
    db.add_all([cat_csr, cat_ch])

    factors = {}
    for at, unit, val in [("electricity_kwh", "kWh", 0.82), ("diesel_liter", "liter", 2.68)]:
        f = EmissionFactor(company_id=cid, activity_type=at, unit=unit, co2e_per_unit=val)
        db.add(f)
        db.flush()
        factors[at] = f

    for p in policies:
        db.add(ESGPolicy(company_id=cid, **p))
    for g in goals:
        db.add(EnvironmentalGoal(company_id=cid, department_id=list(depts.values())[0].id, **g))

    for bname, icon, metric, thr in [
        ("First Steps", "🌱", "xp", 50), ("Green Contributor", "🍃", "xp", 200),
        ("Eco Warrior", "🌳", "xp", 500), ("Challenge Champion", "🏆", "completed_challenges", 5),
    ]:
        db.add(Badge(company_id=cid, name=bname, icon=icon, rule_metric=metric, rule_threshold=thr))

    db.add_all([
        Reward(company_id=cid, name="Reusable Bottle", points_required=100, stock=20, status="Active"),
        Reward(company_id=cid, name="Extra Day Off", points_required=500, stock=3, status="Active"),
    ])

    for ref, at, qty, co2e, dcode, days in carbon_specs:
        db.add(CarbonTransaction(company_id=cid, source_ref=ref, source_type="Manual",
                                 emission_factor_id=factors[at].id, quantity=qty, co2e=co2e,
                                 department_id=depts[dcode].id, date=today - timedelta(days=days)))
    db.commit()

    # A CSR activity with some approved participations (lifts Social)
    act = CSRActivity(company_id=cid, title="Neighbourhood Clean-up", category_id=cat_csr.id,
                      description="Local clean-up drive.", points=50,
                      date=today - timedelta(days=4), department_id=list(depts.values())[0].id)
    db.add(act)
    db.flush()
    for u in users[1:1 + approved_csr]:
        db.add(EmployeeParticipation(company_id=cid, user_id=u.id, activity_id=act.id,
                                     proof_file="seed_proof_placeholder.jpg",
                                     approval_status="Approved", points_earned=50,
                                     completion_date=today - timedelta(days=2)))

    ch = Challenge(company_id=cid, title="Cut Energy 10%", category_id=cat_ch.id,
                   description="Reduce energy use.", xp=100, difficulty="Medium",
                   evidence_required=True, deadline=today + timedelta(days=7), status="Active")
    db.add(ch)
    db.flush()
    db.add(ChallengeParticipation(company_id=cid, challenge_id=ch.id, user_id=users[1].id,
                                  progress=100, proof_file="seed_proof_placeholder.jpg",
                                  approval_status="Pending"))

    audit = Audit(company_id=cid, scope="Internal ESG Audit", date=today - timedelta(days=20),
                  auditor="Internal team", findings="Routine review.")
    db.add(audit)
    db.flush()
    for i in range(overdue_issues):
        db.add(ComplianceIssue(company_id=cid, audit_id=audit.id, severity="High",
                               description=f"Open finding #{i + 1} pending resolution.",
                               owner=list(depts.values())[0].head or "Owner",
                               due_date=today - timedelta(days=3), status="Open"))
    db.commit()
    return company


def run():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # ---------------- Primary company (GreenCore) ----------------
        greencore = Company(name="GreenCore Industries", code="GRC", industry="Manufacturing")
        db.add(greencore)
        db.commit()
        db.refresh(greencore)

        # ---------------- Departments ----------------
        manufacturing = Department(name="Manufacturing", code="MFG", head="R. Kapoor",
                                   employee_count=120, status="Active")
        operations = Department(name="Operations", code="OPS", head="S. Mehta",
                                employee_count=80, status="Active")
        hr = Department(name="Human Resources", code="HR", head="A. Nair",
                        employee_count=25, status="Active")
        rnd = Department(name="R&D", code="RND", head="K. Sharma",
                         employee_count=40, status="Active")
        logistics = Department(name="Logistics", code="LOG", head="D. Costa",
                               employee_count=60, status="Active")
        finance = Department(name="Finance", code="FIN", head="P. Verma",
                             employee_count=30, status="Active")
        db.add_all([manufacturing, operations, hr, rnd, logistics, finance])
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

        # More employees for a fuller leaderboard / directory
        extra = [
            ("Diego Costa", "diego@ecopilot.com", "Manager", logistics.id, 410, 200, 4),
            ("Mei Lin", "mei@ecopilot.com", "Employee", rnd.id, 360, 160, 3),
            ("Omar Haddad", "omar@ecopilot.com", "Employee", operations.id, 240, 110, 2),
            ("Sara Blomqvist", "sara@ecopilot.com", "Employee", hr.id, 150, 300, 1),
            ("Tom Becker", "tom@ecopilot.com", "Employee", finance.id, 90, 60, 0),
            ("Nadia Rahman", "nadia@ecopilot.com", "Employee", logistics.id, 300, 130, 3),
            ("Kenji Tanaka", "kenji@ecopilot.com", "Employee", manufacturing.id, 200, 95, 2),
        ]
        for name, mail, role, dept, xp, pts, done in extra:
            db.add(User(email=mail, hashed_password=hash_password("password123"),
                        full_name=name, role=role, department_id=dept,
                        xp=xp, points_balance=pts, completed_challenges=done))
        db.commit()

        # ---------------- Categories ----------------
        cat_tree = Category(name="Tree Plantation", type="CSR Activity")
        cat_clean = Category(name="Clean-up Drive", type="CSR Activity")
        cat_energy = Category(name="Energy Saving", type="Challenge")
        cat_waste = Category(name="Waste Reduction", type="Challenge")
        cat_blood = Category(name="Blood Donation", type="CSR Activity")
        cat_edu = Category(name="Community Education", type="CSR Activity")
        cat_water = Category(name="Water Conservation", type="Challenge")
        cat_commute = Category(name="Green Commute", type="Challenge")
        db.add_all([cat_tree, cat_clean, cat_energy, cat_waste,
                    cat_blood, cat_edu, cat_water, cat_commute])
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
        ef_gas = EmissionFactor(activity_type="natural_gas_m3", unit="m³",
                                co2e_per_unit=2.02, description="Natural gas heating")
        ef_paper = EmissionFactor(activity_type="paper_kg", unit="kg",
                                  co2e_per_unit=0.94, description="Office paper")
        ef_water = EmissionFactor(activity_type="water_m3", unit="m³",
                                  co2e_per_unit=0.34, description="Municipal water")
        db.add_all([ef_elec, ef_diesel, ef_flight, ef_steel, ef_gas, ef_paper, ef_water])
        db.commit()

        # ---------------- Products ----------------
        db.add_all([
            ProductESGProfile(product="EcoWidget A", carbon_footprint=12.4,
                              recyclable_pct=85, ethical_sourcing="Fair Trade", esg_rating="A"),
            ProductESGProfile(product="Standard Widget", carbon_footprint=41.0,
                              recyclable_pct=40, ethical_sourcing="Conventional", esg_rating="C"),
            ProductESGProfile(product="GreenPack Container", carbon_footprint=6.1,
                              recyclable_pct=95, ethical_sourcing="Recycled", esg_rating="A"),
            ProductESGProfile(product="Legacy Casing", carbon_footprint=58.3,
                              recyclable_pct=20, ethical_sourcing="Conventional", esg_rating="D"),
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
            EnvironmentalGoal(target_metric="Fleet Electrification",
                              target_value=100, unit="%",
                              deadline=date(2028, 6, 30), department_id=logistics.id,
                              current_value=45),
            EnvironmentalGoal(target_metric="Waste Diverted from Landfill",
                              target_value=80, unit="%",
                              deadline=date(2026, 12, 31), department_id=operations.id,
                              current_value=63),
            EnvironmentalGoal(target_metric="Paper Reduction",
                              target_value=40, unit="%",
                              deadline=date(2026, 12, 31), department_id=finance.id,
                              current_value=18),
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
        b_points = Badge(name="Point Collector", description="Accumulate 300 points",
                         icon="🪙", rule_metric="points_balance", rule_threshold=300)
        b_legend = Badge(name="Sustainability Legend", description="Reach 1000 XP",
                         icon="🌟", rule_metric="xp", rule_threshold=1000)
        db.add_all([b_first, b_green, b_warrior, b_champion, b_points, b_legend])
        db.commit()

        # ---------------- Rewards ----------------
        db.add_all([
            Reward(name="Reusable Water Bottle", description="Branded steel bottle",
                   points_required=100, stock=25, status="Active"),
            Reward(name="Extra Day Off", description="One paid day off",
                   points_required=500, stock=5, status="Active"),
            Reward(name="Plant a Tree in Your Name", description="We plant a tree for you",
                   points_required=50, stock=0, status="Active"),  # out of stock (demo block)
            Reward(name="Eco Tote Bag", description="Organic cotton tote",
                   points_required=80, stock=40, status="Active"),
            Reward(name="Lunch Voucher", description="Sustainable café voucher",
                   points_required=120, stock=15, status="Active"),
            Reward(name="Charity Donation (₹500)", description="Donate to a green NGO in your name",
                   points_required=200, stock=100, status="Active"),
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
            CarbonTransaction(source_ref="MFG-GAS", source_type="Manufacturing",
                              emission_factor_id=ef_gas.id, quantity=6000, co2e=12120,
                              department_id=manufacturing.id, date=today - timedelta(days=30)),
            CarbonTransaction(source_ref="LOG-FLEET1", source_type="Fleet",
                              emission_factor_id=ef_diesel.id, quantity=9000, co2e=24120,
                              department_id=logistics.id, date=today - timedelta(days=25)),
            CarbonTransaction(source_ref="LOG-FLEET2", source_type="Fleet",
                              emission_factor_id=ef_diesel.id, quantity=3500, co2e=9380,
                              department_id=logistics.id, date=today - timedelta(days=8)),
            CarbonTransaction(source_ref="OPS-ELEC", source_type="Expense",
                              emission_factor_id=ef_elec.id, quantity=9000, co2e=7380,
                              department_id=operations.id, date=today - timedelta(days=12)),
            CarbonTransaction(source_ref="FIN-PAPER", source_type="Purchase",
                              emission_factor_id=ef_paper.id, quantity=1200, co2e=1128,
                              department_id=finance.id, date=today - timedelta(days=18)),
            CarbonTransaction(source_ref="HR-ELEC", source_type="Expense",
                              emission_factor_id=ef_elec.id, quantity=2500, co2e=2050,
                              department_id=hr.id, date=today - timedelta(days=14)),
        ])
        db.commit()

        # ---------------- CSR activity + PENDING participation (with proof) ----------------
        tree_drive = CSRActivity(title="City Tree Plantation Drive", category_id=cat_tree.id,
                                 description="Plant 500 saplings in the city park.",
                                 points=60, date=today - timedelta(days=3),
                                 department_id=manufacturing.id)
        beach_clean = CSRActivity(title="Riverside Clean-up Campaign", category_id=cat_clean.id,
                                  description="Remove litter along the riverbank.",
                                  points=50, date=today - timedelta(days=6),
                                  department_id=operations.id)
        blood_camp = CSRActivity(title="Company Blood Donation Camp", category_id=cat_blood.id,
                                 description="Donate blood at the on-site camp.",
                                 points=40, date=today - timedelta(days=1),
                                 department_id=hr.id)
        edu_drive = CSRActivity(title="STEM Workshop for Local School", category_id=cat_edu.id,
                                description="Teach a hands-on science session to students.",
                                points=70, date=today + timedelta(days=4),
                                department_id=rnd.id)
        db.add_all([tree_drive, beach_clean, blood_camp, edu_drive])
        db.commit()

        # Raj's PENDING CSR (with proof) — approve live for +60 points
        db.add(EmployeeParticipation(user_id=raj.id, activity_id=tree_drive.id,
                                     proof_file="seed_proof_placeholder.jpg",
                                     approval_status="Pending"))
        # A pending one WITHOUT proof — demonstrates the evidence-required block
        db.add(EmployeeParticipation(user_id=db.query(User).filter_by(email="omar@ecopilot.com").first().id,
                                     activity_id=beach_clean.id,
                                     proof_file=None, approval_status="Pending"))
        # Several already-approved participations so Social scores are realistic
        approved_csr = [
            (priya.id, tree_drive.id, 60), (lena.id, beach_clean.id, 50),
            (db.query(User).filter_by(email="mei@ecopilot.com").first().id, edu_drive.id, 70),
            (db.query(User).filter_by(email="sara@ecopilot.com").first().id, blood_camp.id, 40),
            (db.query(User).filter_by(email="nadia@ecopilot.com").first().id, beach_clean.id, 50),
        ]
        for uid, aid, pts in approved_csr:
            db.add(EmployeeParticipation(user_id=uid, activity_id=aid, proof_file="seed_proof_placeholder.jpg",
                                         approval_status="Approved", points_earned=pts,
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
        ch_draft = Challenge(title="Carpool Challenge", category_id=cat_commute.id,
                             description="Organise a carpool for your team.",
                             xp=120, difficulty="Hard", evidence_required=True,
                             status="Draft")
        ch_water = Challenge(title="Cut Water Use 20%", category_id=cat_water.id,
                             description="Reduce your facility water consumption by 20%.",
                             xp=90, difficulty="Medium", evidence_required=True,
                             deadline=today + timedelta(days=10), status="Active")
        ch_done = Challenge(title="Paperless February", category_id=cat_waste.id,
                            description="A full month with no printed documents.",
                            xp=110, difficulty="Medium", evidence_required=True,
                            deadline=today - timedelta(days=5), status="Completed")
        db.add_all([ch_active, ch_review, ch_draft, ch_water, ch_done])
        db.commit()

        # Priya's PENDING challenge submission — approving unlocks 2 badges live
        db.add(ChallengeParticipation(challenge_id=ch_active.id, user_id=priya.id,
                                      progress=100, proof_file="seed_proof_placeholder.jpg",
                                      approval_status="Pending"))
        # Another pending submission for variety
        db.add(ChallengeParticipation(challenge_id=ch_water.id,
                                      user_id=db.query(User).filter_by(email="kenji@ecopilot.com").first().id,
                                      progress=100, proof_file="seed_proof_placeholder.jpg",
                                      approval_status="Pending"))
        # Approved historic submissions
        for mail, ch in [("lena@ecopilot.com", ch_done), ("mei@ecopilot.com", ch_done),
                         ("diego@ecopilot.com", ch_water)]:
            u = db.query(User).filter_by(email=mail).first()
            db.add(ChallengeParticipation(challenge_id=ch.id, user_id=u.id, progress=100,
                                          proof_file="seed_proof_placeholder.jpg",
                                          approval_status="Approved", xp_awarded=ch.xp))
        db.commit()

        # ---------------- Governance: audit + compliance issues ----------------
        audit = Audit(scope="Annual ESG Internal Audit", date=today - timedelta(days=30),
                      auditor="Deloitte (external)",
                      findings="Renewable share below target; two open safety issues.")
        audit2 = Audit(scope="Supply-Chain Ethics Review", date=today - timedelta(days=12),
                       auditor="Internal Compliance Team",
                       findings="One supplier lacks Fair Trade certification.")
        db.add_all([audit, audit2])
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
            ComplianceIssue(audit_id=audit2.id, severity="Critical",
                            description="Supplier 'CastCo' missing Fair Trade certification.",
                            owner="D. Costa", due_date=today - timedelta(days=2),  # OVERDUE
                            status="Open"),
            ComplianceIssue(audit_id=audit2.id, severity="Low",
                            description="Whistle-blower policy page outdated on intranet.",
                            owner="A. Nair", due_date=today + timedelta(days=15),
                            status="Open"),
            ComplianceIssue(audit_id=audit.id, severity="Medium",
                            description="Waste diversion at 63%, below 80% target.",
                            owner="S. Mehta", due_date=today + timedelta(days=45),
                            status="Resolved"),
        ])
        db.commit()

        # ---------------- Policy acknowledgements ----------------
        first_policy = db.query(ESGPolicy).first()
        db.add_all([
            PolicyAcknowledgement(user_id=priya.id, policy_id=first_policy.id),
            PolicyAcknowledgement(user_id=raj.id, policy_id=first_policy.id),
        ])
        db.commit()

        # ---------------- Tag all of the above as GreenCore, then add more companies ----
        for M in TENANT_MODELS:
            db.query(M).filter(M.company_id.is_(None)).update(
                {"company_id": greencore.id}, synchronize_session=False)
        db.commit()

        add_company(
            db, name="EcoManufacturing Ltd", code="ECOM", industry="Heavy Manufacturing",
            admin_email="admin@ecomanufacturing.com", admin_pw="admin123",
            dept_specs=[("Assembly", "EM-ASM", "T. Wong", 90),
                        ("Packaging", "EM-PKG", "L. Ortiz", 45),
                        ("Quality", "EM-QA", "H. Singh", 30)],
            employees=[("Wei Chen", "wei@ecomanufacturing.com", "EM-ASM", 340, 150, 3),
                       ("Ivan Petrov", "ivan@ecomanufacturing.com", "EM-PKG", 210, 90, 2),
                       ("Fatima Zahra", "fatima@ecomanufacturing.com", "EM-QA", 120, 60, 1)],
            # heavy emitter -> lower Environmental -> lower overall
            carbon_specs=[("EM-A1", "electricity_kwh", 60000, 49200, "EM-ASM", 30),
                          ("EM-A2", "diesel_liter", 12000, 32160, "EM-PKG", 20)],
            policies=[dict(title="EcoManufacturing Emissions Policy", category="Environmental",
                           version="1.0",
                           document=("EcoManufacturing Ltd targets a 20% cut in factory "
                                     "emissions by 2027. The Assembly line, our biggest "
                                     "emitter, must reach 800 tCO2e or lower by 2027. Waste "
                                     "heat recovery is mandatory on all furnaces.")),
                      dict(title="EcoManufacturing Ethics Code", category="Governance",
                           version="1.0",
                           document=("All EcoManufacturing suppliers must pass an annual "
                                     "ethics audit. Compliance issues are reviewed monthly "
                                     "and high-severity items resolved within 45 days."))],
            goals=[dict(target_metric="Assembly Emissions", target_value=800, unit="tCO2e",
                        deadline=date(2027, 12, 31), current_value=1150)],
            overdue_issues=2, approved_csr=1,
        )

        add_company(
            db, name="TerraLogistics", code="TERRA", industry="Logistics",
            admin_email="admin@terralogistics.com", admin_pw="admin123",
            dept_specs=[("Fleet", "TL-FLT", "M. Diallo", 70),
                        ("Warehouse", "TL-WH", "E. Novak", 50)],
            employees=[("Grace Kim", "grace@terralogistics.com", "TL-FLT", 480, 260, 4),
                       ("Pablo Ruiz", "pablo@terralogistics.com", "TL-WH", 330, 170, 3),
                       ("Aisha Bello", "aisha@terralogistics.com", "TL-FLT", 260, 120, 2)],
            # cleaner operation -> higher Environmental -> higher overall
            carbon_specs=[("TL-1", "diesel_liter", 3000, 8040, "TL-FLT", 15),
                          ("TL-2", "electricity_kwh", 5000, 4100, "TL-WH", 10)],
            policies=[dict(title="TerraLogistics Green Fleet Policy", category="Environmental",
                           version="2.0",
                           document=("TerraLogistics will electrify 100% of its delivery "
                                     "fleet by 2028. Idling over 3 minutes is prohibited and "
                                     "route optimisation is mandatory to cut fuel use 25%.")),
                      dict(title="TerraLogistics Community Policy", category="Social",
                           version="1.0",
                           document=("TerraLogistics sponsors two community clean-up drives "
                                     "per quarter and grants staff 20 paid volunteer hours "
                                     "per year."))],
            goals=[dict(target_metric="Fleet Electrification", target_value=100, unit="%",
                        deadline=date(2028, 6, 30), current_value=55)],
            overdue_issues=0, approved_csr=2,
        )

        # ---------------- Auto-award existing badges + compute scores ----------------
        for u in db.query(User).all():
            gamification.check_and_award_badges(db, u)
        scoring.recompute_all(db)

        # ---------------- Invalidate RAG index (will rebuild lazily) --------
        invalidate_company()  # clear all

        print("\n=== EcoPilot seed complete ===")
        print(f"Companies: {db.query(Company).count()}  "
              f"Departments: {db.query(Department).count()}  Users: {db.query(User).count()}")
        print("RAG indexes cleared — will rebuild per-company on first copilot query.")
        print("\nCross-company ESG ranking:")
        for c in db.query(Company).all():
            s = scoring.overall_scores(db, c.id)
            print(f"  {c.name:24s} overall {s['overall']:5}  "
                  f"(E {s['environmental']} / S {s['social']} / G {s['governance']})")
        print("\nLogin credentials:")
        print("  [GreenCore]        manager@ecopilot.com / manager123   (Manager)")
        print("                     priya@ecopilot.com   / priya123     (approve her challenge -> 2 badges)")
        print("                     admin@ecopilot.com   / admin123     (Admin)")
        print("  [EcoManufacturing] admin@ecomanufacturing.com / admin123")
        print("  [TerraLogistics]   admin@terralogistics.com   / admin123")
        print("\nNew: register your own company at /register, or join an existing one.\n")
    finally:
        db.close()


if __name__ == "__main__":
    run()
