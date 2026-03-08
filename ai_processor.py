"""
ai_processor.py — AI-powered alert classification and summarization.

Uses the OpenAI API to categorize alerts, assess severity, generate a
plain-language summary, and produce actionable safety steps.

If the API call fails for any reason, the fallback_classifier module
provides a deterministic, keyword-based alternative.
"""

import json
import os
import logging

from fallback_classifier import fallback_process

logger = logging.getLogger(__name__)

# valid values the AI is allowed to return
VALID_CATEGORIES = {"digital_threat", "scam", "physical_safety", "uncategorized"}
VALID_SEVERITIES = {"high", "medium", "low"}

SYSTEM_PROMPT = """You are a community safety analyst. Given a safety alert description,
return a JSON object with exactly these fields:

{
  "category": one of "digital_threat", "scam", "physical_safety", or "uncategorized",
  "severity": one of "high", "medium", or "low",
  "summary": a calm, 1-2 sentence plain-language summary of the alert,
  "actions": a list of 2-4 specific, actionable safety steps residents should take
}

Respond ONLY with valid JSON. No markdown, no explanation, no preamble."""


def _call_openai(description: str) -> dict:
    """Make a request to the OpenAI API and parse the structured response."""
    # import here so the app still loads even without the openai package
    import openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment.")

    client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this community safety alert:\n\n{description}"},
        ],
        temperature=0.2,
        max_tokens=400,
    )

    raw = response.choices[0].message.content.strip()
    # strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    result = json.loads(raw)

    # validate the AI returned expected fields and values
    if result.get("category") not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category from AI: {result.get('category')}")
    if result.get("severity") not in VALID_SEVERITIES:
        raise ValueError(f"Invalid severity from AI: {result.get('severity')}")
    if not isinstance(result.get("actions"), list) or len(result["actions"]) == 0:
        raise ValueError("AI did not return a valid actions list.")

    return result


def process_alert(description: str) -> dict:
    """
    Process an alert description with AI, falling back to rules on failure.

    Returns a dict with: category, severity, summary, actions, ai_processed, processing_note
    """
    try:
        result = _call_openai(description)
        result["ai_processed"] = True
        result["processing_note"] = "Processed by AI."
        logger.info("Alert processed successfully by AI.")
        return result

    except Exception as e:
        logger.warning(f"AI processing failed ({type(e).__name__}: {e}). Using fallback.")
        return fallback_process(description)
