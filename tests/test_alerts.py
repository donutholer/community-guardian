"""
test_alerts.py — Tests for the Community Guardian platform.

Test 1 (happy path): submit an alert via the API and verify it's stored + processed.
Test 2 (edge case): AI failure triggers the fallback classifier.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, alerts, _load_alerts
from fallback_classifier import fallback_process, classify_category, classify_severity


@pytest.fixture(autouse=True)
def reset_alerts():
    """Reset the in-memory alert list before each test."""
    alerts.clear()
    _load_alerts()
    yield
    # no teardown needed


client = TestClient(app)


# ── Test 1: Happy path — submit and retrieve an alert ───────────────────

def test_submit_and_retrieve_alert():
    """
    Submit a new safety report and verify:
    - 201 status code
    - alert has required fields
    - alert appears in GET /alerts
    - fallback processed correctly (we don't require a live OpenAI key in tests)
    """
    payload = {
        "description": "A suspicious phishing email is circulating that impersonates the local water utility. It asks residents to click a link and enter payment details.",
        "location": "Citywide",
        "source": "Resident Report",
    }

    response = client.post("/alerts", json=payload)
    assert response.status_code == 201

    data = response.json()
    # check required fields exist
    assert "id" in data
    assert "timestamp" in data
    assert data["location"] == "Citywide"
    assert data["description"] == payload["description"]
    assert data["category"] in ("digital_threat", "scam", "physical_safety", "uncategorized")
    assert data["severity"] in ("high", "medium", "low")
    assert isinstance(data["actions"], list)
    assert len(data["actions"]) > 0
    assert "summary" in data
    assert "status" in data

    # verify it appears in the list
    list_response = client.get("/alerts")
    assert list_response.status_code == 200
    all_alerts = list_response.json()["alerts"]
    ids = [a["id"] for a in all_alerts]
    assert data["id"] in ids


# ── Test 2: Edge case — AI failure triggers fallback ────────────────────

def test_ai_failure_triggers_fallback():
    """
    Simulate an AI failure and verify the fallback classifier:
    - still returns a valid category
    - still returns severity
    - marks ai_processed as False
    - returns an actions list
    """
    # mock the internal _call_openai to raise an exception
    with patch("ai_processor._call_openai", side_effect=RuntimeError("API key not set")):
        payload = {
            "description": "Rogue WiFi access point detected at the community center. Users connecting may have had unencrypted traffic intercepted by an attacker.",
            "location": "Southside – Community Center",
        }

        response = client.post("/alerts", json=payload)
        assert response.status_code == 201

        data = response.json()
        # should have been processed by fallback
        assert data["ai_processed"] is False
        assert "fallback" in data["processing_note"].lower()
        assert data["category"] == "digital_threat"  # keywords: wifi, unencrypted, intercept
        assert data["severity"] in ("high", "medium", "low")
        assert isinstance(data["actions"], list)
        assert len(data["actions"]) > 0


# ── Test 3 (bonus): Input validation rejects bad submissions ────────────

def test_input_validation():
    """Verify that submitting with too-short description is rejected."""
    payload = {
        "description": "short",
        "location": "Downtown",
    }
    response = client.post("/alerts", json=payload)
    assert response.status_code == 422  # Pydantic validation error


# ── Test 4 (bonus): Fallback classifier unit tests ──────────────────────

def test_fallback_classify_category():
    assert classify_category("phishing email detected") == "digital_threat"
    assert classify_category("door-to-door scam artists") == "scam"
    assert classify_category("package theft on Main St") == "physical_safety"
    assert classify_category("nice sunny day in the park") == "uncategorized"


def test_fallback_classify_severity():
    assert classify_severity("credit card breach and identity theft") == "high"
    assert classify_severity("suspicious activity near school") == "medium"
    assert classify_severity("old streetlight flickering") == "low"


# ── Test 5 (bonus): Search and filter ───────────────────────────────────

def test_filter_alerts():
    """Verify that category filtering returns correct results."""
    response = client.get("/alerts?category=digital_threat")
    assert response.status_code == 200
    data = response.json()
    for alert in data["alerts"]:
        assert alert["category"] == "digital_threat"
