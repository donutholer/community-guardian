# 🛡 Community Guardian

**AI-powered community safety alert platform** that aggregates local safety and digital security reports, uses AI to filter noise, categorize threats, and provide calm, actionable safety digests.

> Built for the Palo Alto Networks FY26 IT New Grad Case Study — Scenario 3: Community Safety & Digital Wellness.

---

**Candidate Name:** Nic  
**Scenario Chosen:** 3 — Community Safety & Digital Wellness  
**Estimated Time Spent:** ~5 hours  

---

## 📸 Overview

Community Guardian addresses the problem of **alert fatigue** — the overwhelming, fragmented stream of safety information people encounter across news, social media, and community forums. Rather than adding to the noise, the platform acts as a calm, intelligent filter:

1. **Submit** safety reports (phishing scams, package thefts, data breaches, etc.)
2. **AI processes** each report — categorizing it, assessing severity, generating a plain-language summary, and producing actionable steps residents should take.
3. **Browse and filter** alerts by category, severity, or keyword search.
4. If AI is unavailable, a **deterministic fallback classifier** ensures the system still functions.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- An OpenAI API key (optional — the app works without one via the fallback classifier)

### Run Commands

```bash
# 1. Clone the repo
git clone https://github.com/donutholer/community-guardian.git
cd community-guardian

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY (or leave it blank to use fallback mode)

# 5. Run the server
uvicorn app:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser.

### Test Commands

```bash
pytest tests/ -v
```

---

## 🏗 Architecture

```
community-guardian/
├── app.py                  # FastAPI server — routes, data persistence, validation
├── ai_processor.py         # OpenAI integration — classification + summarization
├── fallback_classifier.py  # Rule-based fallback — keyword matching + heuristics
├── data/
│   └── seed_alerts.json    # Synthetic dataset (10 sample alerts)
├── static/
│   └── index.html          # Single-page dashboard UI
├── tests/
│   └── test_alerts.py      # 6 tests (happy path, fallback, validation, filters)
├── requirements.txt
├── .env.example
└── README.md
```

### Data Flow

```
User submits report
        │
        ▼
  Input Validation (Pydantic)
        │
        ▼
  AI Processor (OpenAI API)
     ┌──┴──┐
  success  fail
     │      │
     ▼      ▼
  AI Result  Fallback Classifier
     │       (keyword rules)
     └──┬──┘
        ▼
  Structured Alert
  (category, severity, summary, actions)
        │
        ▼
  Stored + Returned to UI
```

### AI Integration

**AI Capability:** Categorization + Summarization + Action Generation

When a report is submitted, the OpenAI API receives the description and returns:
- **Category:** `digital_threat`, `scam`, `physical_safety`, or `uncategorized`
- **Severity:** `high`, `medium`, or `low`
- **Summary:** A calm, 1–2 sentence plain-language summary
- **Actions:** 2–4 specific, actionable safety steps

**Fallback:** If the API call fails (network error, missing key, bad response, timeout), the system automatically falls back to a keyword-based classifier (`fallback_classifier.py`) that uses:
- Keyword → category mapping with prioritized rule sets
- Severity scoring based on keyword density
- Static action checklists per category
- First-sentence extraction for summaries

The fallback is deterministic and requires no external services.

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Dashboard UI |
| `GET` | `/health` | Health check |
| `POST` | `/alerts` | Submit a new safety report |
| `GET` | `/alerts` | List alerts (supports `?category=`, `?severity=`, `?status=`, `?q=` filters) |
| `GET` | `/alerts/{id}` | Get a single alert |
| `PATCH` | `/alerts/{id}` | Update alert status |

---

## 🧪 Testing

The test suite includes:

1. **Happy path** — Submit an alert, verify it's stored and processed with correct fields.
2. **AI failure → fallback** — Mock OpenAI to throw an error, verify the fallback classifier activates and returns valid output.
3. **Input validation** — Reject submissions with insufficient description length.
4. **Fallback unit tests** — Verify keyword classification for each category.
5. **Severity classification** — Verify severity scoring heuristics.
6. **Filter functionality** — Verify category filtering returns correct subsets.

Run with: `pytest tests/ -v`

---

## 🤖 AI Disclosure

- **Did you use an AI assistant?** Yes — Claude (Anthropic) was used for code generation and architectural planning.
- **How did you verify the suggestions?** All generated code was reviewed, tested, and iterated on. I verified the AI classification output format, tested the fallback path independently, and ran the full test suite.
- **Example of a suggestion I rejected/changed:** Initial suggestion included authentication and user accounts — I scoped this down to focus on the core alert flow since the rubric explicitly says auth is not scored.

---

## ⚖️ Tradeoffs & Prioritization

### What I cut to stay within the timebox:
- **Authentication / user accounts** — not in the scoring rubric.
- **Real-time push notifications** — WebSocket support would add complexity without demonstrating the core AI integration.
- **Map visualization** — would be a great future feature but doesn't demonstrate the AI capability.
- **Database** — used a JSON file instead of SQLite/Postgres. For a prototype with <100 alerts, this is sufficient.

### What I would build next with more time:
- **Location-based filtering** with geocoding, showing alerts on a map.
- **Alert deduplication** — AI-powered detection of similar/duplicate reports.
- **Digest mode** — scheduled AI-generated daily/weekly safety summaries via email.
- **Verification workflow** — community upvoting to help surface verified incidents.
- **Encrypted "Safe Circles"** — privacy-first group alert sharing.

### Known limitations:
- Data is stored in a JSON file (no concurrent write safety).
- No user authentication — anyone can submit or update alerts.
- AI classification quality depends on the model and prompt; the fallback is simpler but always available.
- Synthetic data only — no real community data is collected or scraped.

---

## 🔒 Security Considerations

- API keys are loaded from `.env` and never committed to the repository.
- Input validation prevents oversized or empty submissions.
- The dashboard escapes all user-provided content to prevent XSS.
- No real personal data is used — the dataset is entirely synthetic.
- The AI prompt constrains output format to prevent injection.

---

## 📺 Video

🔗 [Watch the 5–7 minute demo video](#) *(link to be added after recording)*

---
