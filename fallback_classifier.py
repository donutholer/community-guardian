"""
fallback_classifier.py — Rule-based fallback for alert classification.

When the AI service is unavailable or returns an error, this module provides
deterministic keyword-based classification and action generation.
"""

# keyword → category mapping (checked in order, first match wins)
CATEGORY_RULES = [
    {
        "category": "digital_threat",
        "keywords": [
            "phishing", "breach", "hack", "malware", "ransomware", "data leak",
            "unauthorized access", "spoofed", "rogue wifi", "wifi", "credential",
            "password", "encryption", "cyber", "sms phishing", "smishing",
        ],
    },
    {
        "category": "scam",
        "keywords": [
            "scam", "fraud", "impersonat", "fake", "gift card", "social security",
            "qr code", "phony", "con artist", "ponzi", "identity theft",
            "door-to-door", "medicare", "irs",
        ],
    },
    {
        "category": "physical_safety",
        "keywords": [
            "theft", "robbery", "assault", "vandal", "broken", "streetlight",
            "erosion", "collapse", "suspicious person", "trespass", "package",
            "burglary", "fire", "flood", "accident",
        ],
    },
]

# severity scoring: each keyword hit adds weight
SEVERITY_KEYWORDS = {
    "high": [
        "social security", "credit card", "breach", "unauthorized access",
        "spoofed", "identity", "weapon", "assault", "ransomware", "immediate",
    ],
    "medium": [
        "theft", "suspicious", "scam", "fake", "erosion", "broken",
        "intercept", "unencrypted", "phishing",
    ],
    "low": [
        "streetlight", "noise", "minor", "resolved", "old",
    ],
}

# static action checklists per category
ACTION_TEMPLATES = {
    "digital_threat": [
        "Change passwords on any potentially affected accounts.",
        "Enable two-factor authentication where available.",
        "Monitor your accounts for unusual activity over the next 30 days.",
        "Do not click links in suspicious messages — navigate to sites directly.",
    ],
    "scam": [
        "Do not share personal information (SSN, bank details) with unsolicited contacts.",
        "Verify the identity of anyone requesting sensitive information through official channels.",
        "Report the incident to the FTC at reportfraud.ftc.gov.",
        "Warn neighbors and family members about this scam.",
    ],
    "physical_safety": [
        "Avoid the affected area until the issue is resolved.",
        "Report the incident to local authorities if not already reported.",
        "Check doorbell camera or security footage if applicable.",
        "Share details with your neighborhood watch group.",
    ],
    "uncategorized": [
        "Stay aware of your surroundings.",
        "Report anything suspicious to local authorities.",
        "Share this alert with neighbors so they can stay informed.",
    ],
}


def classify_category(description: str) -> str:
    """Classify an alert description into a category using keyword matching."""
    text = description.lower()
    for rule in CATEGORY_RULES:
        if any(kw in text for kw in rule["keywords"]):
            return rule["category"]
    return "uncategorized"


def classify_severity(description: str) -> str:
    """Estimate severity based on keyword presence."""
    text = description.lower()
    score = {"high": 0, "medium": 0, "low": 0}
    for level, keywords in SEVERITY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                score[level] += 1
    # pick the level with the most keyword hits; default to medium
    if score["high"] >= score["medium"] and score["high"] > 0:
        return "high"
    elif score["medium"] > 0:
        return "medium"
    elif score["low"] > 0:
        return "low"
    return "medium"


from typing import List


def generate_actions(category: str) -> List[str]:
    """Return a static action checklist for the given category."""
    return ACTION_TEMPLATES.get(category, ACTION_TEMPLATES["uncategorized"])


def generate_summary(description: str) -> str:
    """Create a brief, plain-language summary by extracting the first sentence."""
    # simple heuristic: take first sentence
    first_sentence = description.split(". ")[0].strip()
    if not first_sentence.endswith("."):
        first_sentence += "."
    return first_sentence


def fallback_process(description: str) -> dict:
    """
    Full fallback pipeline: classify, assess severity, generate summary + actions.
    Returns a structured result matching the AI processor's output format.
    """
    category = classify_category(description)
    severity = classify_severity(description)
    summary = generate_summary(description)
    actions = generate_actions(category)

    return {
        "category": category,
        "severity": severity,
        "summary": summary,
        "actions": actions,
        "ai_processed": False,
        "processing_note": "Processed using rule-based fallback (AI unavailable).",
    }
