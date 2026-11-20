# SentinelOps AI — Implementation Plan
## CICADA 2026 Hackathon | TechForcz × Atria Institute of Technology

---

## Top-Level Overview

**Goal:** Build a real, secure, functional end-to-end AIOps observability platform (SentinelOps AI) for the CICADA 2026 24-hour hackathon.

**Core constraint from PDF:** Raw logs, secrets, and sensitive data must NEVER leave the customer environment. Only an explicit allow-listed metadata payload travels to the central SaaS backend.

**Architecture:** Strict two-tier — Tier 1 (Local Collector) + Tier 2 (Central SaaS Platform).

**Stack:** React + Vite + Tailwind + Recharts (frontend), FastAPI + SQLAlchemy + SQLite (backend), Python + psutil (collector), NumPy/Pandas Z-score (AIOps), IBM watsonx AI (optional AI assistant).

**Judging weight:** Phase 3 (Implementation) = 35 marks, Phase 4 (Demo) = 30 marks — these two phases are where the most marks are earned.

---

## Project Directory Structure

```
ATRIA_PROJECT/
├── .env                        # Real credentials (never commit)
├── .env.example                # Safe template (commit this)
├── .gitignore
├── README.md
├── sentinelops-plan.md         # This file
│
├── frontend/                   # React + Vite + Tailwind
│   ├── src/
│   │   ├── pages/              # One file per sidebar page
│   │   ├── components/         # Shared UI components
│   │   ├── hooks/              # Custom React hooks
│   │   ├── services/           # API + WebSocket clients
│   │   ├── store/              # State management (Zustand or Context)
│   │   └── utils/
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
├── backend/                    # FastAPI
│   ├── app/
│   │   ├── main.py             # App entry point
│   │   ├── config.py           # Settings from .env
│   │   ├── database.py         # SQLAlchemy engine + session
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic schemas
│   │   ├── routers/            # FastAPI routers (one per domain)
│   │   ├── services/           # Business logic
│   │   ├── security/           # JWT, password hashing, RBAC
│   │   ├── aiops/              # Anomaly detection + correlation
│   │   └── utils/
│   ├── migrations/             # Alembic migrations (or init_db.py)
│   ├── seed_data.py            # Synthetic seed data
│   └── requirements.txt
│
├── collector/                  # Local Python collector
│   ├── collector.py            # Main entry point
│   ├── config.py               # Settings from .env
│   ├── sources/                # psutil, simulated telemetry
│   ├── pipeline/               # normalize → filter → redact → allowlist
│   ├── buffer/                 # SQLite local queue
│   ├── transport/              # HTTPS delivery + retry
│   ├── egress_proof/           # Egress log writer
│   └── requirements.txt
│
├── telemetry-simulator/        # Standalone scenario injector
│   ├── simulator.py
│   ├── scenarios/              # CPU spike, memory, latency, outage, etc.
│   └── requirements.txt
│
├── tests/                      # All automated tests
│   ├── test_allowlist.py
│   ├── test_secret_filter.py
│   ├── test_auth.py
│   ├── test_tenant_isolation.py
│   ├── test_anomaly.py
│   ├── test_buffering.py
│   ├── test_idempotent.py
│   ├── test_health_states.py
│   └── test_e2e_smoke.py
│
├── docs/
│   ├── architecture-diagram.md
│   ├── data-flow.md
│   ├── allow-list.md
│   ├── api-reference.md
│   └── demo-walkthrough.md
│
└── scripts/
    ├── start_all.ps1           # Start everything on Windows
    ├── demo_inject.py          # Demo scenario injection script
    └── perf_measure.py         # Latency measurement tool
```

---

## Sub-Task 1 — Project Scaffold + Environment Files

**Status:** [ ] pending

**Intent:** Create the directory tree, root config files, and environment setup so every subsequent sub-task has a valid base to build on.

**Expected Outcomes:**
- Full directory structure exists on disk
- `.env` contains real IBM watsonx credentials and all service config
- `.env.example` has safe placeholders
- `.gitignore` excludes `.env`, `*.db`, `__pycache__`, `node_modules`, `dist`
- `README.md` has project title and "getting started" section

**Todo List:**
1. Create all directories (frontend/src/pages, components, hooks, services, store, utils; backend/app/models, schemas, routers, services, security, aiops, utils, migrations; collector/sources, pipeline, buffer, transport, egress_proof; telemetry-simulator/scenarios; tests; docs; scripts)
2. Write `.env` with IBM watsonx API_KEY, PROJECT_ID, ENDPOINT, backend config, collector config, DB URLs
3. Write `.env.example` with placeholder values only
4. Write `.gitignore`
5. Write skeleton `README.md`

**Relevant Context:** IBM watsonx credentials from master prompt — API_KEY: `<set privately in IBM Cloud and Render>`, PROJECT_ID: `c7b9ea53-e828-4a9e-837a-7c7b78902c9b`, ENDPOINT: `https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29`

---

## Sub-Task 2 — Backend Foundation (FastAPI + DB + Auth)

**Status:** [ ] pending

**Intent:** Stand up the FastAPI application with database models, JWT authentication, tenant isolation, and core ingestion endpoint. This is the backbone every other sub-task depends on.

**Expected Outcomes:**
- `uvicorn backend.app.main:app --reload` starts without errors
- `GET /health` returns `{"status": "ok"}`
- `POST /api/v1/auth/login` returns a JWT token for seeded users
- `POST /api/v1/telemetry/ingest` accepts a valid collector payload and stores it
- All DB tables created on startup via `init_db()`
- Two tenants (alpha, beta) and three users (admin, operator, viewer) seeded
- Tenant-scoped queries enforced — user from tenant-alpha cannot read tenant-beta data

**Todo List:**
1. Write `backend/app/config.py` loading all vars from `.env` via `pydantic-settings`
2. Write `backend/app/database.py` — SQLAlchemy async engine for SQLite, designed to swap to PostgreSQL by changing `DATABASE_URL`
3. Write all ORM models in `backend/app/models/` (16 tables: tenants, users, roles, collectors, monitored_sources, telemetry_events, metrics, alerts, incidents, incident_alerts, notifications, recommendations, collector_heartbeats, transfer_audit, remediation_approvals, remediation_audit)
4. Write Pydantic schemas in `backend/app/schemas/` mirroring each model
5. Write `backend/app/security/auth.py` — bcrypt password hashing, JWT creation/validation, role extraction
6. Write `backend/app/routers/auth.py` — login, logout, /me endpoints
7. Write `backend/app/routers/telemetry.py` — ingest endpoint with allow-list schema validation
8. Write `backend/app/routers/collectors.py` — register, heartbeat, status, config endpoints
9. Write `backend/app/main.py` — register all routers, CORS, startup DB init, WebSocket manager
10. Write `backend/seed_data.py` — insert two tenants, three users, two collectors, synthetic metrics
11. Write `backend/requirements.txt`

**Relevant Context:**
- Allow-listed fields for ingest: tenant_id, source_id (pseudonymous), event_id (UUID), utc_timestamp, source_timezone, metric_category, metric_value, severity, health_status, alert_context, heartbeat_info
- Never store raw logs — only summaries and approved fields
- Backend DB: `sqlite:///./sentinelops.db` (from `.env`)

---

## Sub-Task 3 — Local Collector + Privacy Pipeline

**Status:** [ ] pending

**Intent:** Build the Python collector that runs in the customer environment, collects metrics via psutil, applies the allow-list filter, redacts secrets, writes the egress proof log, and delivers approved payloads to the backend.

**Expected Outcomes:**
- `python collector/collector.py` runs and starts collecting
- CPU, memory, disk, network metrics collected every 5 seconds
- Raw record (with simulated dummy secret) stays in local SQLite only
- Outgoing payload contains only allow-listed fields
- Egress proof log written to `collector/egress_proof/egress.jsonl`
- Payload delivered to `POST /api/v1/telemetry/ingest` with collector API key
- Heartbeat sent to `POST /api/v1/collectors/heartbeat` every 15 seconds
- Each payload has a UUID event_id for idempotency

**Todo List:**
1. Write `collector/config.py` — load from `.env` (SAAS_INGEST_URL, COLLECTOR_API_KEY, tenant_id, etc.)
2. Write `collector/sources/psutil_source.py` — collect CPU%, memory%, disk%, net bytes sent/recv, simulated latency/packet-loss
3. Write `collector/sources/security_source.py` — simulate failed login summaries (count + timestamp, never raw credentials)
4. Write `collector/pipeline/normalizer.py` — convert raw psutil dict to internal format with UTC timestamp + source_timezone
5. Write `collector/pipeline/redactor.py` — scan for secret patterns (password=, token=, key=, Bearer) and replace with `[REDACTED]`
6. Write `collector/pipeline/allowlist.py` — strict field allowlist: drop everything not in the approved set
7. Write `collector/egress_proof/logger.py` — append approved payload + metadata to `egress.jsonl` before every transmission
8. Write `collector/buffer/queue.py` — SQLite queue: insert on failure, mark delivered on ACK, never delete until ACK
9. Write `collector/transport/sender.py` — HTTP POST with retry (exponential backoff, max 10 attempts), duplicate detection via event_id
10. Write `collector/collector.py` — main loop orchestrating all pipeline steps
11. Write `collector/requirements.txt`

**Relevant Context:**
- Raw record example: `{"host": "server-01", "cpu": 45.2, "password": "secret123", "token": "Bearer abc"}` → after allowlist: `{"source_id": "src-a1b2", "metric_category": "cpu", "metric_value": 45.2, "utc_timestamp": "...", "event_id": "uuid"}`
- Egress proof log is NEVER fetched by the SaaS backend — it stays on the collector host only
- The SaaS Privacy Center page reads from `transfer_audit` table (safe transmission records only)

---

## Sub-Task 4 — Telemetry Simulator

**Status:** [ ] pending

**Intent:** Build a standalone scenario injector that emits realistic telemetry events into the collector pipeline, enabling live demos without real infrastructure.

**Expected Outcomes:**
- `python telemetry-simulator/simulator.py` starts and emits normal telemetry
- Operator can trigger named scenarios via CLI argument or REST endpoint
- Scenarios: cpu_spike, memory_spike, disk_pressure, latency_rise, packet_loss, auth_failures, collector_outage, recovery, correlated_resource_saturation
- Each scenario emits events with realistic timestamps + gradual ramp
- Duplicate and out-of-order event scenarios available for idempotency testing
- Organizer adapter stub documented for plugging in the official stream

**Todo List:**
1. Write `telemetry-simulator/scenarios/normal.py` — steady-state metrics for 2 simulated servers
2. Write `telemetry-simulator/scenarios/cpu_spike.py` — CPU ramps from 30% to 96% over 30 seconds
3. Write `telemetry-simulator/scenarios/memory_spike.py`
4. Write `telemetry-simulator/scenarios/disk_pressure.py`
5. Write `telemetry-simulator/scenarios/latency_rise.py`
6. Write `telemetry-simulator/scenarios/auth_failures.py` — emit failed login summary (count only, no credentials)
7. Write `telemetry-simulator/scenarios/collector_outage.py` — stop sending heartbeats for 90 seconds
8. Write `telemetry-simulator/scenarios/correlated.py` — CPU + memory + latency spike on same server simultaneously
9. Write `telemetry-simulator/scenarios/duplicates.py` — resend the same event_id to test idempotency
10. Write `telemetry-simulator/scenarios/out_of_order.py` — send events with timestamps 60 seconds in the past
11. Write `telemetry-simulator/simulator.py` — CLI + optional REST trigger endpoint
12. Write organizer adapter stub `telemetry-simulator/organizer_adapter.py` with mapping config docs

---

## Sub-Task 5 — AIOps Engine (Anomaly Detection + Incident Correlation)

**Status:** [ ] pending

**Intent:** Implement the statistical anomaly detection engine and alert correlation logic that transforms raw metrics into explainable incidents with recommendations.

**Expected Outcomes:**
- Z-score anomaly detection triggers when a metric deviates > 2.5σ from its rolling baseline
- Baselines computed from last 50 data points per source per metric
- "Warm-up" state displayed when fewer than 10 data points exist
- Correlated alerts from the same source within a 5-minute window grouped into one incident
- Each anomaly record contains: type, component, observed_value, expected_baseline, deviation, timestamp, contributing_signals, explanation, suggested_investigation
- No fabricated confidence scores — scoring formula documented

**Todo List:**
1. Write `backend/app/aiops/baseline.py` — per-source rolling window (mean, std, last N points)
2. Write `backend/app/aiops/anomaly_detector.py` — Z-score check, severity scoring, warm-up state
3. Write `backend/app/aiops/correlator.py` — group alerts by source_id + time window + metric category affinity
4. Write `backend/app/aiops/recommender.py` — rule-based explanation generator using metadata evidence (no fabrication)
5. Write `backend/app/aiops/health_classifier.py` — Excellent/Good/Fair/Poor with configurable thresholds + stale-data downgrade
6. Write `backend/app/services/aiops_service.py` — orchestrate detection → correlation → recommendation on each ingested batch
7. Write `backend/app/routers/aiops.py` — endpoints: GET /anomalies, GET /incidents/{id}/explanation, GET /recommendations
8. Update ingestion pipeline to call aiops_service after storing each metric

**Relevant Context:**
- Stale data (no heartbeat > 60s) must downgrade health to Poor — never show last-good as current
- Alert grouping rule: same source_id + overlapping signals within 5 minutes = one incident
- Explanation must cite actual metric values from the payload, not generic text

---

## Sub-Task 6 — Notifications System (WebSocket/SSE)

**Status:** [ ] pending

**Intent:** Build the real-time notification system that pushes alerts to the frontend notification bell without polling.

**Expected Outcomes:**
- `GET /api/v1/notifications/ws` WebSocket connection accepted
- New alert → notification pushed within 2 seconds to all connected frontend clients
- Frontend bell shows unread count badge
- Notification panel opens with filter, search, mark-read, mark-all-read
- No duplicate notifications for the same active incident
- Notifications persist in DB and survive page reload

**Todo List:**
1. Write `backend/app/services/notification_service.py` — create notification, deduplicate, broadcast via WebSocket
2. Write `backend/app/routers/notifications.py` — list, unread-count, mark-read, mark-all-read, filter endpoints
3. Write WebSocket manager in `backend/app/main.py` — connection registry, broadcast method
4. Write `frontend/src/services/websocket.js` — connect, reconnect on drop, dispatch to store
5. Write `frontend/src/components/NotificationBell.jsx` — badge + panel
6. Write `frontend/src/components/NotificationPanel.jsx` — list with severity filter, search, action buttons
7. Test: send CPU spike → verify notification appears within 2s in browser

---

## Sub-Task 7 — React Frontend (All 12 Pages)

**Status:** [ ] pending

**Intent:** Build the full dark-theme React application with all 12 sidebar pages connected to real API data.

**Expected Outcomes:**
- `npm run dev` in `frontend/` opens dashboard at `http://localhost:5173`
- All 12 sidebar nav items open implemented pages (no dead links)
- Login page authenticates via JWT and stores token
- Dashboard shows live metrics from backend (not hard-coded)
- Charts update when new telemetry arrives
- Health state badges (Excellent/Good/Fair/Poor) shown with reason
- Notification bell with unread count in header

**Todo List:**
1. Scaffold Vite + React + Tailwind + Recharts + Lucide + React Router + Axios
2. Write `frontend/src/App.jsx` — router, auth guard, layout
3. Write `frontend/src/components/Layout.jsx` — dark sidebar + header with notification bell
4. Write `frontend/src/pages/Overview.jsx` — summary cards + live charts
5. Write `frontend/src/pages/Infrastructure.jsx` — server list + per-server health
6. Write `frontend/src/pages/NetworkMonitoring.jsx` — latency, packet loss, bandwidth charts
7. Write `frontend/src/pages/SecurityMonitoring.jsx` — auth failure summaries, risk indicators
8. Write `frontend/src/pages/AIInsights.jsx` — anomaly list + explainable recommendation cards
9. Write `frontend/src/pages/AlertsNotifications.jsx` — full notification management
10. Write `frontend/src/pages/IncidentManagement.jsx` — incident list + timeline
11. Write `frontend/src/pages/CollectorFleet.jsx` — fleet table + heartbeat status
12. Write `frontend/src/pages/EgressProof.jsx` — Privacy Center: transfer audit table + payload inspector
13. Write `frontend/src/pages/Analytics.jsx` — incident trends, server health history, severity distribution
14. Write `frontend/src/pages/ActivityTimeline.jsx` — chronological event log
15. Write `frontend/src/pages/Settings.jsx` — threshold configuration, tenant/user management
16. Write `frontend/src/pages/Login.jsx` — login form
17. Write `frontend/src/services/api.js` — Axios instance with JWT interceptor
18. Write `frontend/src/store/` — notifications, auth, telemetry state

---

## Sub-Task 8 — Egress Proof Panel (Privacy Center)

**Status:** [ ] pending

**Intent:** Prove — with actual pipeline data — that secrets never leave the collector. Show raw vs. approved side-by-side.

**Expected Outcomes:**
- Collector-local UI (served on port 8001) shows raw record including dummy secret
- SaaS Privacy Center page shows only the sanitized approved payload from `transfer_audit`
- Payload inspector shows exact JSON sent for each transmission
- Side-by-side comparison demonstrates redaction visually
- Transfer audit table shows: payload_id, timestamp, collector_id, fields_included, status, retry_count

**Todo List:**
1. Write `collector/local_ui.py` — minimal FastAPI on port 8001 showing egress.jsonl + raw telemetry buffer (never accessible from SaaS)
2. Add `transfer_audit` entries in backend on every acknowledged ingestion
3. Write `backend/app/routers/privacy.py` — GET /transfer-audit, GET /payloads/{payload_id}
4. Update `frontend/src/pages/EgressProof.jsx` to fetch from `/transfer-audit` and display payload inspector
5. Add "Raw vs Approved" demo mode in collector local UI

---

## Sub-Task 9 — Offline Buffering + Reliable Delivery

**Status:** [ ] pending

**Intent:** Ensure the collector never loses approved metadata when the SaaS backend is unreachable, and resumes cleanly without duplicates.

**Expected Outcomes:**
- Collector detects failed delivery (connection error / 5xx)
- Payload stored in `collector_buffer.db` SQLite queue with status=pending
- Exponential backoff retry: 2s, 4s, 8s … capped at 5 minutes, max 10 attempts
- On reconnect, all pending payloads delivered in order
- Backend rejects duplicate event_ids with HTTP 409 (idempotent)
- After delivery ACK, record marked delivered in local queue (not deleted)
- Demo script: `scripts/demo_inject.py --scenario outage` forces 30s outage then reconnects and prints ID comparison

**Todo List:**
1. Implement `collector/buffer/queue.py` SQLite queue (create table if not exists, insert, mark-delivered, count-pending)
2. Implement `collector/transport/sender.py` retry loop with exponential backoff
3. Add `event_id` uniqueness constraint to backend `telemetry_events` table
4. Add HTTP 409 response in ingest endpoint when event_id already exists
5. Write `scripts/demo_inject.py` outage demo script
6. Write test `tests/test_buffering.py` and `tests/test_idempotent.py`

---

## Sub-Task 10 — Multi-Tenant Auth + RBAC

**Status:** [ ] pending

**Intent:** Enforce that tenant-alpha users cannot see tenant-beta data, and that role permissions are enforced on every API endpoint.

**Expected Outcomes:**
- JWT token encodes tenant_id + role
- Every DB query filters by tenant_id from the token
- Admin can access all tenant management endpoints
- Operator can acknowledge/resolve incidents
- Viewer has read-only access
- Direct API test: login as tenant-alpha user, attempt GET /metrics?tenant=tenant-beta → 403 Forbidden
- Audit log records every login, config change, incident resolution

**Todo List:**
1. Add `tenant_id` claim to JWT payload
2. Write `backend/app/security/dependencies.py` — `get_current_user`, `require_role`, `require_tenant`
3. Apply tenant filter to all routers (telemetry, alerts, incidents, notifications, collectors)
4. Write `backend/app/services/audit_service.py` — append audit events to `audit_log` table
5. Write `tests/test_tenant_isolation.py` and `tests/test_auth.py`

---

## Sub-Task 11 — Optional Advanced Features

**Status:** [ ] pending

**Intent:** Add the highest-value extras in priority order after core is stable.

**Expected Outcomes (in order of priority):**
- A: Incident timeline with detection → severity change → ack → resolution events
- B: Predictive warning bar when trend extrapolation hits threshold within 10 minutes
- C: Alert noise reduction — suppress duplicate notifications for active incident
- D: Safe remediation simulator with approval step, audit record, rollback demo
- H: IBM watsonx AI assistant answering metadata-grounded questions using the provided API key

**Todo List:**
1. Write incident timeline events table + `GET /incidents/{id}/timeline` endpoint
2. Write `frontend/src/components/IncidentTimeline.jsx`
3. Write linear trend extrapolation in `backend/app/aiops/predictor.py`
4. Add predictive warning badge to Overview page
5. Add deduplication logic in `notification_service.py` (suppress if same incident already has open notification)
6. Write `backend/app/routers/remediation.py` — propose, approve, audit, rollback simulation
7. Write `frontend/src/pages/RemediationSimulator.jsx`
8. Write `backend/app/services/watsonx_service.py` — call IBM watsonx chat endpoint with approved metadata context only (never raw logs/secrets)
9. Write `frontend/src/components/AskSentinelAI.jsx` — chat widget

---

## Sub-Task 12 — Automated Tests

**Status:** [ ] pending

**Intent:** Satisfy the 20 required test categories with meaningful automated tests using pytest.

**Expected Outcomes:**
- `pytest tests/` passes with ≥ 20 test functions covering all required categories
- End-to-end smoke test exercises the full pipeline in one test

**Todo List:**
1. `tests/test_allowlist.py` — verify non-allow-listed fields are dropped
2. `tests/test_secret_filter.py` — verify password/token/key patterns are redacted
3. `tests/test_auth.py` — login success, wrong password, expired token
4. `tests/test_tenant_isolation.py` — cross-tenant data access returns 403
5. `tests/test_anomaly.py` — Z-score triggers at correct deviation, warm-up state
6. `tests/test_health_states.py` — Excellent/Good/Fair/Poor thresholds
7. `tests/test_alert_generation.py` — anomaly → alert created
8. `tests/test_duplicate_grouping.py` — correlated alerts → single incident
9. `tests/test_notifications.py` — alert → notification created
10. `tests/test_buffering.py` — failed delivery → queued in SQLite
11. `tests/test_idempotent.py` — duplicate event_id rejected with 409
12. `tests/test_event_ordering.py` — out-of-order events sorted by event_time
13. `tests/test_utc_timestamps.py` — all stored timestamps are UTC ISO-8601
14. `tests/test_offline_detection.py` — missing heartbeat → Poor status within 60s
15. `tests/test_egress_payload.py` — egress log matches what backend received
16. `tests/test_e2e_smoke.py` — full pipeline: simulator → collector → backend → alert → notification

---

## Sub-Task 13 — Documentation + Demo Scripts

**Status:** [ ] pending

**Intent:** Produce all documentation required for hackathon judges plus a reproducible demo walkthrough.

**Expected Outcomes:**
- `README.md` has complete Windows PowerShell setup + run commands
- `docs/architecture-diagram.md` has Mermaid two-tier diagram
- `docs/allow-list.md` lists every approved field with explanation
- `docs/demo-walkthrough.md` covers all 24 steps from Section 26 of master prompt
- `scripts/start_all.ps1` starts backend + frontend + collector + simulator in order
- `scripts/demo_inject.py` can inject any named scenario

**Todo List:**
1. Write `README.md` with install, configure, run, test, demo sections
2. Write `docs/architecture-diagram.md`
3. Write `docs/allow-list.md`
4. Write `docs/data-flow.md` with trust boundary explanation
5. Write `docs/demo-walkthrough.md` (24-step judge demo)
6. Write `docs/judge-qa.md` (Q&A answers for Section 26)
7. Write `scripts/start_all.ps1`
8. Write `scripts/demo_inject.py` with --scenario flag

---

## Database Schema Summary

| Table | Key Columns |
|---|---|
| tenants | id, name, region, data_residency_region, created_at |
| users | id, tenant_id, email, hashed_password, role_id, created_at |
| roles | id, name (admin/operator/viewer), permissions JSON |
| collectors | id, tenant_id, name, api_key_hash, status, region, version, last_heartbeat_at |
| monitored_sources | id, tenant_id, collector_id, source_id (pseudonymous), display_name, type |
| telemetry_events | id, tenant_id, source_id, event_id (unique), utc_timestamp, event_time, metric_category, metric_value, severity, health_status, alert_context |
| metrics | id, tenant_id, source_id, category, value, utc_timestamp, event_time |
| alerts | id, tenant_id, source_id, type, severity, message, baseline, observed, deviation, created_at, acknowledged_at |
| incidents | id, tenant_id, title, severity, status, source_id, created_at, resolved_at, health_state_before, health_state_after |
| incident_alerts | incident_id, alert_id |
| notifications | id, tenant_id, source_id, title, severity, description, utc_timestamp, is_read, incident_id, recommended_action |
| recommendations | id, tenant_id, incident_id, explanation, contributing_signals JSON, suggested_steps JSON, created_at |
| collector_heartbeats | id, collector_id, tenant_id, received_at, cpu_pct, mem_pct, buffered_count, version |
| transfer_audit | id, tenant_id, collector_id, payload_id (unique), utc_timestamp, fields_included JSON, status, retry_count, payload_preview JSON |
| remediation_approvals | id, tenant_id, incident_id, proposed_action, proposed_by, approved_by, status, created_at, approved_at |
| remediation_audit | id, approval_id, action_taken, result, audit_log JSON, created_at, rolled_back_at |

---

## Metadata Allow-List (Exact Fields Sent to SaaS)

| Field | Description |
|---|---|
| tenant_id | Tenant identifier |
| source_id | Pseudonymous server/device identifier (never hostname with PII) |
| event_id | UUID — unique per event, used for idempotent delivery |
| utc_timestamp | ISO-8601 UTC time of transmission |
| event_time | ISO-8601 UTC time of original event (for ordering) |
| source_timezone | IANA timezone string |
| metric_category | cpu / memory / disk / network / security |
| metric_value | Numeric value |
| severity | info / warning / critical / resolved |
| health_status | excellent / good / fair / poor |
| alert_context | Short text, max 200 chars, pre-screened for secrets |
| heartbeat_info | collector version, buffered_count, cpu_pct, mem_pct |

**Everything else stays local.** Raw log lines, process names, usernames, passwords, tokens, hostnames with PII, full stack traces — all stay in the collector's local SQLite.

---

## Real-Time Performance Targets

| Measure | Target | Implementation |
|---|---|---|
| Collection to dashboard | < 10s p95 | Timestamps at: generation, ingest ACK, dashboard render via WS |
| Threshold to alert | < 15s | Timestamps at: event_time, alert created_at |
| Offline detection | < 60s | Heartbeat timeout check every 10s in backend scheduler |
| Post-outage delivery | 0 loss, 0 duplicates | SQLite queue + idempotent event_id on backend |

---

## IBM watsonx AI Integration Notes

- Used ONLY for the optional "Ask Sentinel AI" assistant (Sub-Task 11, Feature H)
- The assistant receives ONLY: incident summaries, metric values, alert titles, health states — all from the allow-list
- Raw logs, secrets, hostnames with PII, passwords, tokens are NEVER sent to watsonx
- API call: POST to `https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29`
- Auth header: `Authorization: Bearer <IAM_TOKEN>` (exchanged from API_KEY via IBM IAM token endpoint)
- Project ID sent as `project_id` in request body
- If watsonx is unavailable, the deterministic rule-based recommender is used as fallback
- Core system works 100% without watsonx — it is an enhancement only

---

## Implementation Order for 24-Hour Hackathon

```
Hour 0–2:   Sub-Task 1 (Scaffold) + Sub-Task 2 (Backend Foundation)
Hour 2–4:   Sub-Task 3 (Collector + Privacy Pipeline)
Hour 4–5:   Sub-Task 4 (Telemetry Simulator)
Hour 5–7:   Sub-Task 5 (AIOps Engine)
Hour 7–8:   Sub-Task 6 (Notifications WebSocket)
Hour 8–13:  Sub-Task 7 (React Frontend — all 12 pages)
Hour 13–14: Sub-Task 8 (Egress Proof Panel)
Hour 14–15: Sub-Task 9 (Offline Buffering)
Hour 15–16: Sub-Task 10 (Auth + RBAC + Tenant Isolation)
Hour 16–19: Sub-Task 11 (Advanced Features)
Hour 19–21: Sub-Task 12 (Automated Tests)
Hour 21–24: Sub-Task 13 (Docs + Demo Scripts + Final Polish)
```

---

## Known Limitations to Disclose Honestly

1. TLS is documented but uses HTTP locally — a production deployment needs a reverse proxy (nginx + Let's Encrypt or mkcert for local)
2. Regional infrastructure is simulated via config labels, not actual multi-region deployment
3. psutil on Windows may not expose network interface statistics for all adapters
4. IBM watsonx assistant requires internet access — falls back to rule-based if offline
5. SQLite has concurrency limits — PostgreSQL swap is documented but not implemented in prototype
6. The organizer's official telemetry stream format is unknown — the adapter stub requires mapping once the format is confirmed
