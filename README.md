# SentinelOps AI
### CICADA 2026 Hackathon — TechForcz × Atria Institute of Technology

> End-to-end, secure AIOps observability delivering autonomous insights across enterprise, data center, cloud, and distributed architectures.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1 — Customer Environment (Local)                          │
│                                                                 │
│  Telemetry Simulator → Local Collector                          │
│                           ↓                                     │
│                    Normalize → Redact → Allow-list              │
│                           ↓              ↓                      │
│                    Local SQLite      Egress Proof Log           │
│                    (raw + buffer)    (never sent to SaaS)       │
└────────────────────────── ↓ ────────────────────────────────────┘
              Encrypted HTTP · API-Key Auth · Allow-listed fields only
┌────────────────────────── ↓ ────────────────────────────────────┐
│  TIER 2 — Central SaaS Platform                                 │
│                                                                 │
│  FastAPI Backend → AIOps Engine → Notifications (WebSocket)     │
│       ↓                                   ↓                     │
│  SQLite (metadata only)         React Dashboard                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start (Windows PowerShell)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git

### 1. Clone and configure
```powershell
cd C:\Users\anant\Desktop\ATRIA_PROJECT
Copy-Item .env.example .env   # already done — real credentials pre-filled
```

### 2. Backend setup
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed_data.py          # Initialize DB + seed tenants/users
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend setup
```powershell
cd frontend
npm install
npm run dev                  # Opens at http://localhost:5173
```

### 4. Local Collector
```powershell
cd collector
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python collector.py
```

### 5. Telemetry Simulator
```powershell
cd telemetry-simulator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python simulator.py --scenario normal
```

### 6. Run all tests
```powershell
cd C:\Users\anant\Desktop\ATRIA_PROJECT
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

### 7. Start everything at once
```powershell
.\scripts\start_all.ps1
```

---

## Default Login Credentials (seed data — change in production)

| Role | Email | Password | Tenant |
|---|---|---|---|
| Admin | admin@alpha.local | SentinelAdmin2026! | tenant-alpha |
| Operator | operator@alpha.local | SentinelOp2026! | tenant-alpha |
| Viewer | viewer@beta.local | SentinelView2026! | tenant-beta |

---

## Demo Scenarios

Inject a CPU spike:
```powershell
python scripts\demo_inject.py --scenario cpu_spike
```

Inject a correlated resource saturation incident:
```powershell
python scripts\demo_inject.py --scenario correlated
```

Simulate SaaS outage + recovery:
```powershell
python scripts\demo_inject.py --scenario outage
```

---

## Project Structure

```
ATRIA_PROJECT/
├── frontend/          React + Vite + Tailwind dashboard
├── backend/           FastAPI + SQLAlchemy SaaS platform
├── collector/         Local Python collector + privacy pipeline
├── telemetry-simulator/  Scenario-based telemetry generator
├── tests/             Automated test suite (20 categories)
├── docs/              Architecture, allow-list, demo walkthrough
└── scripts/           PowerShell start scripts + demo tools
```

---

## Security Notes

- Raw logs, passwords, tokens, and secrets **never** leave the collector environment
- Only allow-listed metadata fields are transmitted to the SaaS backend
- All transmitted payloads are logged in the egress proof file (`collector/egress_proof/egress.jsonl`)
- Multi-tenant isolation enforced at every database query
- JWT tokens expire after 60 minutes
- Passwords hashed with bcrypt

---

## Known Limitations

1. Local HTTP used for prototype; production requires TLS (nginx + mkcert documented in `docs/`)
2. Regional infrastructure simulated via config labels
3. IBM watsonx AI assistant requires internet access; falls back to rule-based recommendations
4. SQLite for prototype; PostgreSQL swap requires only changing `DATABASE_URL`
5. Organizer telemetry stream adapter requires mapping once official format is confirmed

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Tailwind CSS, Recharts, Lucide React, React Router |
| Backend | Python 3.11, FastAPI, Pydantic v2, SQLAlchemy 2, Uvicorn |
| Database | SQLite (prototype) → PostgreSQL (production) |
| Collector | Python, psutil, SQLite buffer |
| AIOps | NumPy, Pandas, Z-score anomaly detection, rule-based correlation |
| AI Assistant | IBM watsonx (granite model) — optional |
| Auth | JWT (python-jose), bcrypt (passlib) |
