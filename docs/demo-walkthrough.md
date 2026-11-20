# SentinelOps AI — Demo Walkthrough
## 24-Step Hackathon Demonstration Guide

---

## Prerequisites
1. Backend running: `cd backend && uvicorn app.main:app --reload --port 8000`
2. Frontend running: `cd frontend && npm run dev`
3. Simulator ready: `cd telemetry-simulator`
4. Browser open: `http://localhost:5173`

---

## Step-by-Step Demo

### Phase 1 — System Overview

**Step 1: Open the dashboard**
Navigate to `http://localhost:5173` → Login with `admin@alpha.local / SentinelAdmin2026!`

**Step 2: Show healthy servers**
Overview page → 2 monitored sources with Excellent health → Live CPU/Memory charts from seeded data

**Step 3: Show collector status**
Navigate to Collector Fleet → Alpha-Collector-01 shows Online with heartbeat timestamps

### Phase 2 — Inject Events

**Step 4: Trigger a CPU spike**
```powershell
python scripts/demo_inject.py --scenario cpu_spike --ticks 15 --interval 2
```
Watch the Overview CPU chart rise in real-time

**Step 5: Show health status change**
Overview page → Health badge changes from Excellent → Fair → Poor as CPU exceeds thresholds

**Step 6: Notification bell updates**
Top-right bell shows red badge with count → Click to see the CPU anomaly notification

**Step 7: Open alert details**
Alerts page → See the anomaly alert with observed value, baseline, and Z-score deviation

**Step 8: Show anomaly explanation**
AI Insights page → Recommendation card shows:
- "CPU value of 92.0 is above the recent baseline of 28.0 (±3.0) by 21.3 standard deviations"
- Confidence basis: "rule-based: Z-score threshold (>2.5σ)"

### Phase 3 — Correlated Incident

**Step 9: Trigger correlated alerts**
```powershell
python scripts/demo_inject.py --scenario correlated --ticks 12 --interval 2
```

**Step 10: Show incident correlation**
Incidents page → Single incident "Possible src-alpha-01 Resource Issue (cpu, memory, network)"
- 3 alerts merged into 1 incident
- Severity escalates to Critical

**Step 11: Show recommendation**
Expand incident → AI recommendation with:
- Contributing signals from actual metric values
- 4-step investigation guide
- Confidence basis documented

### Phase 4 — Privacy Demonstration

**Step 12: Show raw collector data (LOCAL ONLY)**
Open: `http://localhost:8001/raw`
See: `"raw_config_snippet": "password=SuperSecret123"` present on collector side

**Step 13: Prove secret stays local**
Local UI: `http://localhost:8001/compare` shows:
- Raw record has `_raw_usernames`, `_raw_source_ips`, `raw_config_snippet`
- Approved payload has NONE of these

**Step 14: Open Egress Proof Panel**
SaaS Dashboard → Egress Proof / Privacy page → Transfer audit records

**Step 15: Compare payloads**
Privacy Center shows only 12 allow-listed fields → NO secrets, NO raw logs

### Phase 5 — Offline Buffering

**Step 16: Simulate backend outage**
Stop the backend (`Ctrl+C` in backend terminal)

**Step 17: Show local buffering**
Collector Fleet page → `buffered_count` increasing → Collector still running locally

**Step 18: Reconnect**
Restart backend: `uvicorn app.main:app --reload --port 8000`

**Step 19: Verify delivery without duplicates**
Privacy Center → All buffered payloads delivered → No duplicate event_ids

### Phase 6 — Multi-Tenant Isolation

**Step 20: Show tenant isolation**
Login as `viewer@beta.local / SentinelView2026!` → Can only see tenant-beta data
Login as admin@alpha.local → Sees tenant-alpha data only

### Phase 7 — Advanced Features

**Step 21: Show incident timeline**
Incidents page → Expand incident → Timeline shows: created → alerts added → severity changes

**Step 22: Analytics**
Analytics page → Incident frequency chart, health distribution, server alert comparison

**Step 23: Performance measurements**
Transfer audit records show timestamps → Calculate: event_time vs created_at shows <10s latency

**Step 24: Explain limitations**
Refer to Known Limitations section in README.md

---

## Judge Q&A Quick Reference

**Q: What leaves the collector?**
A: Only 12 allow-listed fields (tenant_id, pseudonymous source_id, event_id, UTC timestamps, metric category/value, severity, health_status, alert_context, collector_id)

**Q: How does anomaly detection work?**
A: Z-score analysis on a rolling 50-sample window. Threshold: 2.5σ. Warm-up state shown when <10 samples.

**Q: How are incidents correlated?**
A: Same source_id + 2+ alerts within a 5-minute window → grouped into one incident

**Q: What happens when SaaS is unreachable?**
A: SQLite queue buffers payloads. Exponential backoff retry. event_id uniqueness prevents duplicates on reconnect.

**Q: How is tenant isolation enforced?**
A: JWT token contains tenant_id. Every DB query filters by tenant_id from the token. Direct API bypass returns 403.
