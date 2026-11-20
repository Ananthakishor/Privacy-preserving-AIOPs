# SentinelOps AI — Architecture Diagram
## Two-Tier AIOps Observability Platform

## Trust Boundary

```
┌──────────────────────────────────────────────────────────────────────┐
│  TIER 1 — CUSTOMER ENVIRONMENT (Local)                               │
│  Everything inside this box NEVER leaves unless explicitly approved   │
│                                                                        │
│  ┌─────────────────┐    ┌─────────────────────────────────────────┐  │
│  │ Telemetry       │    │ Local Collector (collector.py)           │  │
│  │ Simulator /     │───▶│                                          │  │
│  │ psutil          │    │  1. Collect: psutil + security signals   │  │
│  └─────────────────┘    │  2. Normalize: UTC timestamps, pseudoID  │  │
│                          │  3. Redact: secrets/passwords/tokens     │  │
│  ┌─────────────────┐    │  4. Allow-list: drop non-approved fields │  │
│  │ Raw Local Store │◀───│  5. Log to egress_proof/egress.jsonl     │  │
│  │ (stays local)   │    │  6. Buffer in SQLite on failure          │  │
│  │                 │    │  7. Retry with exponential backoff       │  │
│  │ - raw logs      │    └─────────────────┬───────────────────────┘  │
│  │ - secrets       │                      │                           │
│  │ - passwords     │    ┌─────────────────▼───────────────────────┐  │
│  │ - raw auth logs │    │ Egress Proof Log (LOCAL ONLY)            │  │
│  │ - hostnames     │    │ http://localhost:8001                    │  │
│  └─────────────────┘    └─────────────────────────────────────────┘  │
└──────────────────────────────────│───────────────────────────────────┘
                                   │
              ╔══════════════════════════════════════╗
              ║  TRUST BOUNDARY                       ║
              ║  - HTTPS/TLS (HTTP for local demo)    ║
              ║  - X-Collector-API-Key auth           ║
              ║  - Only 12 allow-listed fields        ║
              ║  - event_id uniqueness enforced       ║
              ╚══════════════════════════════════════╝
                                   │
┌──────────────────────────────────▼───────────────────────────────────┐
│  TIER 2 — CENTRAL SAAS PLATFORM (backend/)                           │
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────┐     │
│  │ FastAPI Backend (app/main.py)                               │     │
│  │                                                              │     │
│  │  POST /api/v1/telemetry/ingest                              │     │
│  │    ├── Schema validation (TelemetryIngestPayload)           │     │
│  │    ├── Duplicate check (event_id UNIQUE → 409)              │     │
│  │    ├── Store TelemetryEvent + Metric                        │     │
│  │    ├── Write TransferAudit (Privacy Center)                 │     │
│  │    └── Trigger AIOps pipeline                              │     │
│  │                                                              │     │
│  │  AIOps Pipeline:                                            │     │
│  │    baseline.py → anomaly_detector.py → correlator.py        │     │
│  │    → recommender.py → notification_service.py               │     │
│  │                                                              │     │
│  │  WebSocket /api/v1/notifications/ws                         │     │
│  │    → Push to tenant-scoped connected clients                │     │
│  └─────────────────────────────────────────────────────────────┘     │
│                                                                        │
│  ┌──────────────────┐  ┌────────────────────────────────────────┐    │
│  │ SQLite (SaaS DB) │  │ Background: Heartbeat Monitor (10s)    │    │
│  │ (metadata only)  │  │ → Mark offline if no heartbeat > 60s  │    │
│  └──────────────────┘  └────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                                   │
                     ┌─────────────▼──────────────┐
                     │ React Frontend (frontend/)   │
                     │ http://localhost:5173         │
                     │                              │
                     │ 12 Pages:                    │
                     │  Overview · Infrastructure   │
                     │  Network · Security          │
                     │  AI Insights · Alerts        │
                     │  Incidents · Fleet           │
                     │  Egress Proof · Analytics    │
                     │  Timeline · Settings         │
                     └──────────────────────────────┘
```

## Data Flow

1. **Collect** → psutil reads CPU/mem/disk/net from OS
2. **Normalize** → Assign pseudonymous source_id, UTC timestamp
3. **Redact** → Scan for secret patterns, drop sensitive fields
4. **Allow-list** → Keep only 12 approved fields
5. **Log** → Write to egress.jsonl (LOCAL ONLY)
6. **Send** → HTTP POST to SaaS with API key
7. **Ingest** → Schema validate, idempotency check, store metadata
8. **AIOps** → Z-score anomaly detection, correlation, recommendation
9. **Notify** → WebSocket push to frontend
10. **Display** → Dashboard updates within 10 seconds

## Allowed Metadata Fields (Trust Boundary)

| Field | Description |
|---|---|
| tenant_id | Tenant identifier |
| source_id | Pseudonymous server ID |
| event_id | UUID, idempotency key |
| utc_timestamp | ISO-8601 UTC, transmission time |
| event_time | ISO-8601 UTC, original event time |
| source_timezone | IANA timezone |
| metric_category | cpu/memory/disk/network/security |
| metric_value | Numeric value |
| severity | info/warning/critical/resolved |
| health_status | excellent/good/fair/poor |
| alert_context | Max 200 chars, pre-screened |
| collector_id | Collector identifier |

## Security Controls

- **Collector auth**: X-Collector-API-Key header, bcrypt-hashed
- **User auth**: JWT (HS256), 60-min expiry, bcrypt passwords
- **Tenant isolation**: tenant_id in JWT, enforced on every DB query
- **Allow-list**: Pydantic schema rejects undeclared fields
- **Secret redaction**: Regex patterns + field name exclusion
- **Audit log**: Append-only JSONL, never includes passwords

## Performance Targets (from PDF)

| Measure | Target | Implementation |
|---|---|---|
| Collection to dashboard | < 10s p95 | Timestamps at: gen, ingest, WS push |
| Threshold to alert | < 15s | Z-score checked on ingest |
| Offline detection | < 60s | Background task checks every 10s |
| Post-outage delivery | 0 loss, 0 dupes | SQLite queue + 409 idempotency |
