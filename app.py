"""
app.py — Community Guardian: a lightweight safety alert platform.

FastAPI server that provides:
  - POST /alerts           → submit a new safety report
  - GET  /alerts           → list alerts with optional filters
  - GET  /alerts/{id}      → get a single alert
  - PATCH /alerts/{id}     → update alert status
  - GET  /                 → serve the dashboard UI
  - GET  /health           → health check
"""

from __future__ import annotations

import json
import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

from ai_processor import process_alert
from fallback_classifier import fallback_process

# ── Config ──────────────────────────────────────────────────────────────────

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
ALERTS_FILE = DATA_DIR / "alerts_dataset.json"
SEED_FILE = DATA_DIR / "seed_alerts.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_alerts()
    yield


app = FastAPI(
    title="Community Guardian",
    description="AI-powered community safety alert platform",
    version="1.0.0",
    lifespan=lifespan,
)

# serve static files (the frontend)
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ── In-memory data store (loaded from / saved to JSON) ─────────────────────

alerts: List = []


def _load_alerts():
    """Load alerts from the dataset file, or fall back to seed data."""
    global alerts
    if ALERTS_FILE.exists():
        with open(ALERTS_FILE, "r") as f:
            alerts = json.load(f)
    elif SEED_FILE.exists():
        with open(SEED_FILE, "r") as f:
            alerts = json.load(f)
        _save_alerts()
    logger.info(f"Loaded {len(alerts)} alerts.")


def _save_alerts():
    """Persist the current alerts list to disk."""
    DATA_DIR.mkdir(exist_ok=True)
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


# ── Pydantic models ────────────────────────────────────────────────────────

class AlertSubmission(BaseModel):
    """Schema for submitting a new safety report."""
    description: str = Field(..., min_length=10, max_length=2000)
    location: str = Field(..., min_length=2, max_length=200)
    source: str = Field(default="Community Report", max_length=200)

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Description cannot be blank.")
        return v.strip()

    @field_validator("location")
    @classmethod
    def location_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Location cannot be blank.")
        return v.strip()


class AlertUpdate(BaseModel):
    """Schema for updating an alert's status."""
    status: str = Field(..., pattern="^(verified|unverified|resolved|dismissed)$")


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Serve the single-page dashboard."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text())
    return HTMLResponse(content="<h1>Community Guardian API is running.</h1>")


@app.get("/health")
def health():
    return {"status": "ok", "alert_count": len(alerts)}


@app.post("/alerts", status_code=201)
def create_alert(submission: AlertSubmission):
    """
    Submit a new safety report.
    The system processes it with AI (or fallback) and stores the result.
    """
    # run AI classification
    analysis = process_alert(submission.description)

    alert = {
        "id": f"alert-{uuid.uuid4().hex[:8]}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": submission.location,
        "source": submission.source,
        "description": submission.description,
        "category": analysis["category"],
        "severity": analysis["severity"],
        "summary": analysis["summary"],
        "actions": analysis["actions"],
        "ai_processed": analysis["ai_processed"],
        "processing_note": analysis["processing_note"],
        "status": "unverified",
    }

    alerts.insert(0, alert)  # newest first
    _save_alerts()
    logger.info(f"Created alert {alert['id']} (category={alert['category']}, ai={alert['ai_processed']})")
    return alert


@app.get("/alerts")
def list_alerts(
    category: Optional[str] = Query(None, description="Filter by category"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    q: Optional[str] = Query(None, description="Search in description and location"),
):
    """List all alerts with optional filtering and search."""
    results = alerts

    if category:
        results = [a for a in results if a.get("category") == category]
    if severity:
        results = [a for a in results if a.get("severity") == severity]
    if status:
        results = [a for a in results if a.get("status") == status]
    if q:
        q_lower = q.lower()
        results = [
            a for a in results
            if q_lower in a.get("description", "").lower()
            or q_lower in a.get("location", "").lower()
            or q_lower in a.get("summary", "").lower()
        ]

    return {"count": len(results), "alerts": results}


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: str):
    """Retrieve a single alert by ID."""
    for a in alerts:
        if a["id"] == alert_id:
            return a
    raise HTTPException(status_code=404, detail="Alert not found.")


@app.patch("/alerts/{alert_id}")
def update_alert(alert_id: str, update: AlertUpdate):
    """Update the status of an existing alert."""
    for a in alerts:
        if a["id"] == alert_id:
            a["status"] = update.status
            _save_alerts()
            return a
    raise HTTPException(status_code=404, detail="Alert not found.")
