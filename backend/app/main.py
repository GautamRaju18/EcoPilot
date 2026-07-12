"""EcoPilot API entrypoint."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import (
    auth, carbon, challenges, chat, companies, copilot, csr, gamification,
    governance, master, notifications, onboarding, scoring,
)
from .utils import UPLOAD_DIR

# Create tables on startup (hackathon — no migration tooling)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EcoPilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth, companies, master, carbon, csr, challenges, governance,
          gamification, scoring, notifications, onboarding, copilot, chat):
    app.include_router(r.router)

# Serve uploaded proof files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
def root():
    return {"service": "EcoPilot API", "docs": "/docs", "status": "ok"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
