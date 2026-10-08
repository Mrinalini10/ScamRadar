# ScamRadar — Scam Genomic Surveillance System

> Tracks fraud campaign *lineages*, not clusters. Scam scripts mutate like pathogens — ScamRadar builds evolutionary trees, corrects for reporting delays, and alerts before losses scale.

---

## Quick Start (One Command)

```bash
bash setup.sh
```

Then open **http://localhost:5173** → click **Dataset Loader** → **Load Dataset** → explore.

---

## What It Does

| Component | Description |
|-----------|-------------|
| Dialog-Act Tagger | Converts raw SMS into manipulation act sequences (GREET → IMPERSONATE → URGENCY → PAYMENT_REQUEST). Language-independent — works in Hindi, Tamil, Telugu, Hinglish, English. |
| Lineage Engine | MinHash + Profile HMM groups complaints by *script similarity*, not identifier similarity. Builds an evolutionary tree of scam variants. |
| Nowcasting | Bayesian correction for reporting delays. Victims report 2–5 days late — ScamRadar shows the true estimated count, not just observed. |
| CUSUM Early Warning | Changepoint detection per lineage. Alarms when a campaign's growth rate crosses a calibrated threshold. |
| Cross-Bank Intel | PSI-based cross-institution linking. Shows campaigns seen across multiple banks without sharing raw data. |
| Audit Trail | HMAC-SHA256 signed log of all analyst actions. RBI FREE-AI framework compliant. |

---

## Architecture

```
kiro_thinkroot/
├── backend/                   # FastAPI Python backend
│   ├── main.py                # App entry point
│   ├── api/                   # Route handlers
│   │   ├── dashboard.py       # Stats + activity
│   │   ├── complaints.py      # Ingest + list
│   │   ├── lineages.py        # Lineage CRUD + detail
│   │   ├── alerts.py          # CUSUM alerts
│   │   ├── audit.py           # Audit trail
│   │   ├── crossbank.py       # PSI cross-bank
│   │   ├── admin.py           # Config
│   │   └── dataset.py         # Dataset loader
│   ├── ml/                    # ML pipeline
│   │   ├── tagger.py          # Dialog-act tagging
│   │   ├── lineage.py         # MinHash + Profile HMM
│   │   ├── nowcasting.py      # Bayesian nowcasting + Rt
│   │   ├── cusum.py           # CUSUM + BOCD
│   │   └── dataset.py         # Mendeley fetcher + synthetic corpus
│   ├── models/
│   │   ├── db_models.py       # SQLAlchemy models
│   │   └── database.py        # Async DB session
│   └── utils/
│       └── helpers.py         # Hashing, PSI, audit hash, poisoning detection
│
├── frontend/                  # React + Vite frontend
│   └── src/
│       ├── App.jsx            # Router
│       ├── components/        # Sidebar, UI primitives
│       └── pages/             # 8 screens
│           ├── Dashboard.jsx
│           ├── IngestComplaint.jsx
│           ├── Lineages.jsx
│           ├── LineageDetail.jsx
│           ├── Alerts.jsx
│           ├── CrossBank.jsx
│           ├── AuditTrail.jsx
│           ├── AdminConfig.jsx
│           └── DatasetLoader.jsx
│
└── setup.sh                   # One-command setup
```

---

## Dataset

- **Primary**: Mendeley SMS Phishing Dataset (DOI: [10.17632/f45bkkt8pr.1](https://data.mendeley.com/datasets/f45bkkt8pr/1)) — 5,971 messages, CC BY 4.0
- **Supplement**: 300 synthetic Indian-language scam messages (Hindi, Tamil, Telugu, Hinglish) with realistic metadata
- **Reporting delays** injected empirically: 20% same-day, 60% 2–5 days, 20% 10–30 days

---

## Screens

| # | Screen | Path |
|---|--------|------|
| 1 | Dashboard | `/` |
| 2 | Ingest Complaint | `/ingest` |
| 3 | Lineage Tree | `/lineages` |
| 3b | Lineage Detail | `/lineages/:id` |
| 4 | Early Warning Alerts | `/alerts` |
| 5 | Cross-Bank Intelligence | `/crossbank` |
| 6 | Audit Trail | `/audit` |
| 7 | Admin Config | `/admin` |
| 8 | Dataset Loader | `/dataset` |

---

## API Docs

FastAPI auto-generates interactive docs at: **http://localhost:8000/docs**

---

## Manual Run (without setup.sh)

**Backend:**
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Privacy & Security Design

- All phone numbers, UPI IDs, URLs are SHA-256 hashed on ingest — only last 4 characters displayed
- Cross-bank intelligence never reveals which bank reported what — only anonymized counts
- Poisoning detection: reporters filing > 5 complaints against same lineage in 24h are flagged
- Audit trail is HMAC-signed and append-only
- Designed as a **calculator/surveillance tool**, not personalized advice — no SEBI IA registration required

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy (async), SQLite |
| ML | datasketch (MinHash), hmmlearn (HMM), ruptures (CUSUM), scipy (Rt estimation), langdetect |
| Frontend | React 18, Vite, Recharts, React Router, Lucide Icons |
| Auth | HMAC-SHA256 for audit hashes |
| Deploy | Local now → Vercel (frontend) + Railway/Render (backend) |

---

## Deploying Later

**Frontend → Vercel:**
```bash
cd frontend && npm run build
# drag dist/ to vercel.com or use vercel CLI
```

**Backend → Railway:**
- Add `Procfile`: `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
- Push backend/ to a GitHub repo and connect to Railway
- Set `DATABASE_URL` env var to a Postgres URL for production

---

*Built for hackathon demonstration. References: Mendeley (DOI: 10.17632/f45bkkt8pr.1), RBI FREE-AI Framework, DPIP/I4C cross-institution fraud sharing.*
# ScamRadar
