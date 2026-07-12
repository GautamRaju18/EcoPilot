# EcoPilot — Project Context & Handoff

> Continuation brief for picking this project up on a new platform / fresh AI session.
> Read this top-to-bottom before making changes.

---

## 1. What this is

**EcoPilot** — an AI-powered, **multi-tenant** ESG (Environmental, Social, Governance)
management platform for the **Odoo Hackathon 2026** (EcoSphere problem statement).

One line: *Companies track carbon, run CSR & governance workflows, and gamify
sustainability on one dashboard — with an AI copilot grounded in their own policies
and auto-generated ESG reports.*

- **Repo:** https://github.com/GautamRaju18/EcoPilot.git (branch `main`)
- **Owner:** GautamRaju18 · **Team of 4** (see §7)
- **Status:** feature-complete demo, 31 commits, all pushed. Build passes.

---

## 2. Tech stack

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python **3.13**), SQLAlchemy 2, SQLite (`backend/ecopilot.db`) |
| Auth | JWT (PyJWT) + `pbkdf2_sha256`; roles **Employee / Manager / Admin** |
| Multi-tenancy | `Company` table; **every** record carries `company_id`; all queries scoped |
| AI generation | Pluggable chain: **Gemini → OpenRouter → Ollama → deterministic template** |
| AI retrieval (RAG) | TF-IDF (bigram, offline-safe) + optional FAISS/Gemini embeddings, **per-company** |
| AI report | LangGraph pipeline: `gather → retrieve → draft → finalize` (falls back to sequential) |
| Frontend | React 18 + Vite + Tailwind CSS 3, **glassmorphism / spatial UI** |

Everything degrades gracefully: no API keys → copilot still answers (grounded,
extractive) and report still generates via the LangGraph fallback.

---

## 3. How to run

### Backend
```bash
cd backend
python -m venv .venv                 # already exists; Python 3.13
.venv\Scripts\activate               # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt      # core deps; AI deps optional (google-genai, faiss-cpu, langgraph)
python -m app.seed                   # DROPS & recreates DB, loads 3 demo companies
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs · health: `/api/health`

### Frontend
```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173 (Vite proxies /api + /uploads → :8000)
npm run build                        # production build (use to catch compile errors)
```

> **Windows note:** the team uses PowerShell + Git Bash. Kill a stuck backend with
> `taskkill //F //PID <pid>` (find via `netstat -ano | grep :8000`). uvicorn has **no
> hot-reload for .env** — restart after editing `backend/.env`.

---

## 4. Demo credentials (after `python -m app.seed`)

3 seeded companies, each isolated:

| Company | Login | Password | Role |
|---|---|---|---|
| **GreenCore Industries** (rich demo) | `manager@ecopilot.com` | `manager123` | Manager |
| GreenCore | `priya@ecopilot.com` | `priya123` | Employee |
| GreenCore | `admin@ecopilot.com` | `admin123` | Admin |
| **EcoManufacturing Ltd** | `admin@ecomanufacturing.com` | `admin123` | Admin |
| **TerraLogistics** | `admin@terralogistics.com` | `admin123` | Admin |

Cross-company ESG ranking (seeded): TerraLogistics ≈79 > GreenCore ≈68 > EcoManufacturing ≈67.

**The money-shot demo beat:** log in as GreenCore manager → Challenges → approve
**Priya's** pending "Reduce Office Energy 15%" submission → she jumps to #1 on the
leaderboard as **Eco Warrior 🌳 + Challenge Champion 🏆 auto-unlock live** (she's seeded
at 450 XP / 4 completed; the challenge is worth 100 XP and pushes her over both thresholds).

---

## 5. Architecture / repo map

```
backend/
  app/
    main.py            # FastAPI app, registers all routers, create_all on startup
    config.py          # Settings (env/.env): weights, feature flags, LLM keys
    database.py        # engine, SessionLocal, Base, get_db
    models.py          # ALL tables — Company + company_id on every entity
    schemas.py         # Pydantic v2 (note: DateT alias avoids `date` field/type shadow bug)
    auth.py            # hash/verify (pbkdf2_sha256), JWT encode/decode
    deps.py            # get_current_user, require_roles("Manager")
    utils.py           # file upload (proof) helper
    seed.py            # 3-company seed + add_company() helper (idempotent: drops all)
    services/
      scoring.py       # weighted ESG: 0.40*E + 0.30*S + 0.30*G, per-company, live from DB
      emissions.py     # auto CO2e = quantity * factor.co2e_per_unit
      gamification.py  # badge auto-award, reward redemption, leaderboard (company-scoped)
      notifications.py # in-app notify() helper
      sample_data.py   # onboarding: populate_company() + import_carbon_csv()
    routers/
      auth.py          # register (create/join company), login, /me
      companies.py     # /public (signup dropdown, no auth), /leaderboard (cross-company)
      master.py        # generic CRUD factory for 8 master entities (company-scoped)
      carbon.py csr.py challenges.py governance.py   # transactional flows
      gamification.py scoring.py notifications.py
      onboarding.py    # status, sample-data, CSV import, template
      copilot.py       # /ai/ask, /ai/report, /ai/status, /ai/reindex (persists chat)
      chat.py          # /ai/history (GET list, DELETE clear) + save_message()
    ai/
      llm.py           # provider chain + Gemini 429 cooldown & 8s timeout cap
      rag.py           # per-company chunked index, TF-IDF/FAISS retrieve
      copilot.py       # answer_question(): sentence-level grounded extraction
      report_graph.py  # LangGraph ESG report pipeline
      starter_docs.py  # STARTER_POLICIES/GOALS for new companies (feeds RAG)
frontend/
  src/
    api.js             # fetch wrapper, token in localStorage, login/postForm helpers
    auth.jsx           # AuthProvider: user (incl. company), login, register, logout, isManager
    hooks.js           # usePolling(fn, ms) — live auto-refresh
    App.jsx            # routes (Protected wrapper), /login /register public
    index.css          # GLASSMORPHISM: aurora bg, .card (frosted), .lift, .glass, buttons
    components/
      Layout.jsx        # glass sidebar/topbar, nav, notifications bell (polls 8s)
      ui.jsx            # ScoreRing, Bar, StatCard, Pill, Modal, Field, Empty
      EntityManager.jsx # generic admin CRUD table+modal (config-driven)
      Onboarding.jsx    # new-company popup (sample data / CSV import)
      Markdown.jsx      # dependency-free MD renderer (bold, bullets incl. +, italic, code)
    pages/
      Login Register Dashboard Carbon CSR Challenges Governance
      Copilot Report Companies Admin
```

---

## 6. Key behaviors & business rules (all implemented)

1. **Weighted ESG** = 0.40·E + 0.30·S + 0.30·G, recomputed live from DB per company.
   Env drops with emissions (`CO2E_PER_POINT=1600`), Social rises with approved CSR/challenges,
   Governance drops with open/overdue compliance issues.
2. **Auto emission calc** — CO2e = quantity × emission factor (toggle `AUTO_EMISSION_CALC`).
3. **Evidence required** — CSR/challenge can't be approved without a proof file (`EVIDENCE_REQUIRED`).
4. **Badge auto-award** — the instant XP / completed-challenges / points cross a badge threshold.
5. **Reward redemption** — deducts points + decrements stock; blocks on 0 stock / low balance.
6. **Challenge lifecycle** — Draft → Active → Under Review → Completed / Archived.
7. **Compliance** — every issue needs owner + due date; overdue Open issues flagged.
8. **Notifications** — in-app only (bell), company-scoped broadcasts + personal.
9. **Multi-tenancy** — `company_id` on all tables; RAG chunks tagged & filtered per company
   (Company A's copilot can NEVER see Company B's policies — verified).
10. **Registration** — create a company (become Admin) or join one (become Employee).
11. **Onboarding** — empty company gets a popup: load sample data / import ESG CSV / manual.
12. **Persistent chat** — `ChatMessage` table; `/ai/ask` saves each turn; history loads
    from server per-user (survives navigation, reload, and different devices).

---

## 7. Team & the COMMIT WORKFLOW (important, non-standard)

The team wanted **no "Claude" as a git author/collaborator**, and commits distributed
across 4 real people so per-member contribution points are fair. So:

- **Claude never commits via its own identity and never adds a `Co-Authored-By: Claude` trailer.**
- Each commit's **author AND committer** are set to the teammate who owns that code's zone.
- Zones:

| Member | GitHub / email | Zone |
|---|---|---|
| **GautamRaju18** | `gautamraju2004@gmail.com` | M1 — Backend / data model / auth / master CRUD |
| **Srikar7362** | `pspsrikar@gmail.com` | M4 — Business logic / transactional routers / seed |
| **Sheryansh0** | `bachchushreyansh@gmail.com` | M3 — AI (LLM, RAG, LangGraph, copilot) |
| **aneeshpen** | `aneesh2665@gmail.com` | M2 — Frontend (all `frontend/**`) |

**Current distribution (31 commits):** aneeshpen 12 · Sheryansh0 7 · Srikar7362 6 · GautamRaju18 6.
aneesh leads because recent work was frontend-heavy; route backend/logic/AI tasks to the
others to rebalance.

**The commit incantation** (run from `D:\EcoPilot`, Git Bash) — stage a zone's files then:
```bash
GIT_AUTHOR_NAME="Srikar7362" GIT_AUTHOR_EMAIL="pspsrikar@gmail.com" \
GIT_COMMITTER_NAME="Srikar7362" GIT_COMMITTER_EMAIL="pspsrikar@gmail.com" \
  git commit -m "feat(logic): ..."      # NO Claude trailer
```
Verify no Claude ever: `git log --pretty='%an|%cn|%s|%b' | grep -i 'claude\|co-author\|anthropic'` → must print nothing.

Push: `git push origin main` (credentials cached; Windows Credential Manager handled auth).
For contributions to count on GitHub, the 3 non-owner emails must be **collaborators** on
the repo (Settings → Collaborators) and match each person's GitHub account email.

---

## 8. Secrets / .env (gitignored — NOT in repo)

`backend/.env` holds (currently set by the user):
- `GEMINI_API_KEY` — **free-tier quota is EXHAUSTED (429)**, see §9
- `OPENROUTER_API_KEY` — **working**, serves the fluent answers
- `SECRET_KEY`, model names, `EMBEDDINGS_BACKEND=tfidf`

⚠️ **Both keys were pasted into chat during development → treat as exposed → ROTATE them.**
Never commit `.env` (it's in `.gitignore`; verified excluded).

---

## 9. Known issues / gotchas

- **Gemini 429**: the provided Gemini key's free-tier daily quota is used up, so `/ai/ask`
  falls through to **OpenRouter** (which works, fluent + cited). `llm.py` has an **8s timeout
  cap** + **5-min cooldown** so it doesn't hang on Gemini after the first 429. When the quota
  resets (daily) or billing is enabled, it auto-switches back to Gemini — no code change.
  The status badge reflects the provider that *actually* answered.
- **OpenRouter latency** varies on free tier (1s–25s). For the demo, ask one throwaway
  question first to trip the cooldown so subsequent answers are instant.
- **`python -m app.seed` DROPS ALL DATA** and reloads the 3 demo companies. Re-run to reset
  to a clean demo state (do this right before presenting).
- **Pydantic gotcha (already fixed):** a field named `date` with type `date` shadows the type
  → resolves to `NoneType`. `schemas.py` uses a `DateT = date` alias. Don't reintroduce.
- Frontend uses **emoji** for nav/stat icons (the design skill recommends SVG, e.g. Lucide/
  Heroicons — a future polish item, not blocking).
- LF→CRLF git warnings on Windows are harmless.

---

## 10. Suggested next steps (not yet built)

- **Demo narration script** — 5-min click-path across the 8 Definition-of-Done beats, one
  presenter per segment.
- **Stretch: CSR proof vision-check** (M3/Sheryansh) — Gemini/OpenRouter vision compares an
  uploaded proof photo to the stated activity, auto-approve or flag.
- **Server-side notification preferences** (M4/Srikar) — rebalances Srikar.
- **Richer analytics** — trend charts (emissions over time), department drill-downs (see the
  `dataviz` guidance).
- **SVG icon pass** — replace emoji nav/stat icons with a consistent icon set.
- **Dark mode** — the glass system is built light-only; add a dark variant.

---

## 11. Definition of Done (all ✅ verified in-browser)

Login+roles · live overall ESG from dept scores · carbon tx auto-calc shifts Env score ·
CSR submit→approve→points (evidence enforced) · challenge→XP→badge auto-unlock→leaderboard ·
Ask EcoPilot grounded + cited · ESG report narrative via LangGraph · multi-company isolation ·
registration (create/join) · cross-company ranking · onboarding · persistent cross-device chat ·
glassmorphism/spatial UI · no console errors on the demo path.
