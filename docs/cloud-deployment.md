# SentinelOps deployment for tesseract.cv

The deployment branch is `cloud-deployment`. The local rollback point on `main` is `670ba0fefc972d5f749467d54a649297e3e67733`. Start the existing local system from that branch if you need the original version. The project contains separate backend and collector SQLite databases. Keep those files on the monitored machine.

## Services and credentials

| Service | Intended address | Configuration |
| --- | --- | --- |
| Vercel React dashboard | `https://tesseract.cv` | Build the contents of `frontend/`. The Vercel configuration supplies the public API origin and serves the SPA entry point for deep links. |
| Render FastAPI service | `https://api.tesseract.cv` | Use `render.yaml` on the deployment branch. The health endpoint is `/health`. Use one worker and one instance because notification connections are held in memory. |
| PostgreSQL | Private database connection | Supply a dedicated managed database through Render's protected `DATABASE_URL`. Use a same-region internal connection for Render Postgres or the external provider's TLS-verified connection settings. |
| Collector | Customer machine | Configure `collector/.env.cloud` from the example. The raw viewer remains on loopback port 8001. |

Revoke the exposed IBM watsonx key through IBM Cloud IAM. The historical project plan contains the key. The local demo collector key and seed-account passwords also occur in Git history. Generate independent production credentials. Configure replacement IBM settings only if enabling the optional assistant on Render.

## Build and check locally

From the project root in PowerShell, with the existing dependencies installed:

```powershell
backend/.venv/Scripts/python -X utf8 -m pytest tests -q
Push-Location frontend
$env:VITE_API_ORIGIN = 'https://api.tesseract.cv'
npm.cmd run build
Remove-Item Env:VITE_API_ORIGIN
Pop-Location
```

For a clean frontend checkout, run `npm ci` in the frontend directory before the build. Development uses the existing Vite proxy. The cloud notification stream uses `wss://api.tesseract.cv/api/v1/notifications/ws`. The client sends the access token in its first frame and the server takes the tenant from the authenticated account.

## Publish after approval

1. With explicit push approval, run `git push -u origin cloud-deployment`. Keep the working version on `main`. The deployment files disable automatic Git deployment. Creating or syncing a provider project can still publish the first version.
2. Sign in to the Render dashboard and connect the repository through its GitHub authorization flow. Choose the deployment branch. Review the proposed web service and its name before applying the Blueprint. Get approval for publication before applying it. The proposed web tier is Free. Its idle spin-down affects cold starts. Get explicit cost approval before provisioning a paid database. A free Render database expires and is unsuitable for ongoing storage. Use an approved persistent database and configure backup retention in its dashboard. [Render free-tier limits](https://render.com/docs/free)
3. In Render's protected environment settings, set `DATABASE_URL`, `INITIAL_ADMIN_EMAIL`, `INITIAL_ADMIN_PASSWORD` and `INITIAL_COLLECTOR_KEY`. Use a password manager to generate independent random ASCII values of 32–64 characters for the password and collector key. The Blueprint generates the JWT signing key. Initial setup creates one tenant, administrator, collector and pseudonymous source in one transaction. Keep the administrator password and collector key securely, then remove their initial provisioning variables after a verified first start. Subsequent starts recognize the existing tenant. The service runs additive column migrations and replaces the old baseline uniqueness index with a tenant-scoped index. Bootstrap refuses demo tenants. Use a new database for the first release.
4. Render executes the following commands from `backend/`:

   ```sh
   python -m pip install -r requirements.txt
   python -m app.bootstrap && uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1
   ```

5. For the first Vercel deployment, use a standalone project with the Vite preset. To publish the exact branch without uploading the working directory, export its tracked frontend to an empty temporary directory. Run the following from the repository root **after public deployment approval**. Select the intended Vercel team and project in the interactive prompts. Set the Vercel root directory to `.` for this frontend-only export. A repository-connected deployment instead uses root directory `frontend` and production branch `cloud-deployment`.

   ```powershell
   $exportDir = Join-Path ([IO.Path]::GetTempPath()) ("sentinelops-vercel-" + [guid]::NewGuid())
   New-Item -Type Directory -Path $exportDir | Out-Null
   git archive --format=zip -o "$exportDir/frontend.zip" cloud-deployment:frontend
   Expand-Archive -LiteralPath "$exportDir/frontend.zip" -DestinationPath "$exportDir/site"
   Push-Location "$exportDir/site"
   npx vercel login
   npx vercel link
   npx vercel deploy --prod
   Pop-Location
   ```

## DNS and certificate issuance

Public delegation observed on 21 November 2026 was `ns1.hola.cv` and `ns2.hola.cv`. The root lookup returned no A/AAAA answer and the API lookup returned NXDOMAIN. Inspect the authenticated DNS zone at the registrar before proposing changes. Public delegation identifies the authoritative servers. It does not establish access to the registrar account.

| Name | Source of the requested record | Value |
| --- | --- | --- |
| `tesseract.cv` (apex) | Vercel project → Settings → Domains → add the apex → view the recommended record | Pending project creation and dashboard inspection |
| `api.tesseract.cv` | Render web service → Settings → Custom Domains → API hostname | Pending service creation and dashboard inspection |
| Ownership challenge, if requested | The provider showing the challenge supplies both the TXT name and value | Pending provider instructions |

Capture the exact type, name, target and displayed TTL or DNS host default. Compare with the existing zone, including MX, TXT, AAAA and CAA. Present the actual proposed changes and any conflicts to the owner for DNS approval. Apply only approved records at the current DNS host. Once the records propagate, verify the custom domains in both dashboards and wait for both managed certificates. [Vercel custom domains](https://vercel.com/docs/domains/set-up-custom-domain) · [Render custom domains](https://render.com/docs/custom-domains)

## Connect the collector after HTTPS verification

From the repository root, create the private cloud profile once and enter its assigned key locally:

```powershell
if (!(Test-Path collector/.env.cloud)) { Copy-Item collector/cloud.env.example collector/.env.cloud }
notepad collector/.env.cloud
$env:COLLECTOR_ENV_FILE = (Resolve-Path collector/.env.cloud).Path
collector/.venv/Scripts/python -m collector.collector
```

The cloud profile uses its own queue and egress log. Start it only after verifying the API certificate and the intended tenant. Its registration, heartbeat and ingest requests use HTTPS and refuse redirects. Run the optional raw viewer locally with the same profile. To return to the original local configuration, stop that collector, clear `COLLECTOR_ENV_FILE` in its shell, and use the existing local start procedure.

## Release verification

- Confirm both providers report domain ownership and valid certificates. Check the certificate names, chains and HTTP-to-HTTPS redirects on the two real hostnames.
- Load the root and refresh `/infrastructure` directly in a browser. Log in, check `/api/v1/auth/me`, confirm the exact CORS origin, and verify the authenticated WSS connection receives a tenant notification. Log out and verify the socket closes.
- Match a real CPU and RAM sample by timestamp between local egress and the dashboard. Check the collector heartbeat and online/offline transitions. Check network measurements and provenance separately. The security source may label permission-limited samples simulated.
- Use an isolated test tenant for simulated anomalies. Check alerts, linked incidents, and WebSocket messages. Compare approved fields and event IDs across local egress, transfer audit and PostgreSQL. Pause the test collector's outbound connection, reconnect, and verify one persisted event per buffered ID. Verify records after an approved service restart.
- Record the actual URLs, verification time, tested user role, sample IDs and outcomes without recording credentials. Preserve DNS values from the pre-change zone for any approved rollback.

## Local verification on 21 November 2026

The unchanged baseline passed 38 tests. The deployment branch passed 42 tests with 10 deprecation warnings. The Vite production build succeeded, contained the intended API origin, excluded the demo password, and served the same entry page for the root and a nested route in local preview. Vite reported a bundle-size warning.

A temporary PostgreSQL 18.6 instance ran the production bootstrap twice. The FastAPI test client verified login/logout, database-backed health, exact CORS, separate-tenant fleet access, collector enrollment, heartbeat, offline detection, authenticated notification delivery, and the transfer audit. Two simulated spikes produced alerts and an incident. Two real psutil CPU and RAM measurements passed through normalization, redaction, an isolated offline queue and replay. The transport outage was simulated. All four events survived an application and database restart. These tests used local test transport. Ownership, public TLS/WSS, physical collector delivery over the internet, Vercel routing, and Render persistence require the live project.

## Changed files

- `.gitignore`
- `backend/app/bootstrap.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/main.py`
- `backend/app/models/aiops_baseline.py`
- `backend/app/models/telemetry.py`
- `backend/app/routers/auth.py`
- `backend/app/routers/collectors.py`
- `backend/app/routers/remediation.py`
- `backend/app/routers/telemetry.py`
- `backend/app/schemas/telemetry.py`
- `backend/app/security/dependencies.py`
- `backend/app/services/audit_service.py`
- `backend/app/services/notification_service.py`
- `backend/app/services/watsonx_service.py`
- `backend/requirements.txt`
- `backend/seed_data.py`
- `collector/cloud.env.example`
- `collector/collector.py`
- `collector/config.py`
- `collector/transport/sender.py`
- `docs/cloud-deployment.md`
- `frontend/src/App.jsx`
- `frontend/src/pages/Login.jsx`
- `frontend/src/services/api.js`
- `frontend/src/services/websocket.js`
- `frontend/vercel.json`
- `frontend/vite.config.js`
- `render.yaml`
- `sentinelops-plan.md`
- `tests/conftest.py`
- `tests/test_cloud_deployment.py`
