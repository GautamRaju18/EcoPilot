# 🌱 EcoPilot — AI-Powered ESG Management Platform

Unifies **carbon accounting**, **CSR & governance workflows**, and **gamified
sustainability** in one dashboard — with an **AI copilot grounded in your own
policies** and **auto-generated ESG reports**.

_Odoo Hackathon 2026 · EcoSphere problem statement._

---

## Tech Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI (Python 3.13), SQLAlchemy, SQLite |
| Auth | JWT (PyJWT) + `pbkdf2_sha256`, roles: Employee / Manager / Admin |
| AI — generation | **Pluggable**: Gemini → OpenRouter → Ollama → deterministic template |
| AI — retrieval (RAG) | TF-IDF (offline-safe) + optional FAISS + Gemini embeddings |
| AI — report pipeline | LangGraph (`gather → retrieve → draft → finalize`) |
| Frontend | React 18 + Vite + Tailwind CSS |

The AI layer **degrades gracefully**: with no API keys the copilot still answers
(grounded, extractive) and the report still generates via the LangGraph pipeline.
Add a Gemini key for fluent natural-language output — nothing else changes.

---

## Run it

### 1. Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows (use source .venv/bin/activate on mac/linux)
pip install -r requirements.txt
python -m app.seed                # create + populate the demo database
uvicorn app.main:app --reload --port 8000
```
API docs at http://localhost:8000/docs

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
App at http://localhost:5173 (Vite proxies `/api` → backend:8000)

### 3. (Optional) Enable Gemini
Edit `backend/.env` and set `GEMINI_API_KEY=...`. Restart the backend.
The copilot/report provider badge will switch from `template` to `gemini`.
To use FAISS + Gemini embeddings for retrieval, also set `EMBEDDINGS_BACKEND=gemini`.

---

## Demo credentials

| Role | Email | Password |
|---|---|---|
| Admin | `admin@ecopilot.com` | `admin123` |
| Manager | `manager@ecopilot.com` | `manager123` |
| Employee (Priya) | `priya@ecopilot.com` | `priya123` |
| Employee (Raj) | `raj@ecopilot.com` | `password123` |

---

## Demo click-path (Definition of Done)

1. **Login** as Manager → role-based dashboard.
2. **Dashboard** shows live Overall ESG **71.1**, pillar bars, 4 department scorecards, leaderboard.
3. **Carbon** → log a transaction (pick `steel_kg`, qty 5000) → CO₂e auto-calcs to 9250 → Manufacturing Environmental score visibly drops.
4. **CSR** → approve Raj's pending "City Tree Plantation Drive" participation → +60 points (blocked without proof).
5. **Challenges** → approve **Priya's** "Reduce Office Energy 15%" submission → she jumps to **#1** on the leaderboard as **Eco Warrior 🌳 + Challenge Champion 🏆** auto-unlock.
6. **Ask EcoPilot** → _"What is our current emission target for manufacturing?"_ → grounded answer citing the goal doc (500 tCO₂e by 2026).
7. **ESG Report** → Generate → LangGraph produces a written narrative from live scores.
8. **🔔 Notifications** show every approval and badge unlock.

---

## Business rules implemented

Weighted ESG scoring (40/30/30) · auto emission calc · evidence-required approvals ·
badge auto-award · reward redemption (stock + balance guards) · challenge lifecycle ·
compliance-issue ownership + overdue flagging · in-app notifications.

---

## Repository layout

```
backend/
  app/
    models.py         # full data model (Section 3)
    services/         # scoring, emissions, gamification, notifications  (business logic)
    routers/          # auth, master CRUD, carbon, csr, challenges, governance, ai …
    ai/               # llm (providers), rag, copilot, report_graph (LangGraph)
    seed.py           # demo data + 3 grounded ESG policy docs
frontend/
  src/pages/          # Login, Dashboard, Carbon, CSR, Challenges, Governance, Copilot, Report
  src/components/     # Layout, shared UI
```
