> **STATUS: DRAFT** — this doc is a structured outline of what needs to be answered. Sections without content are TODO for the owner. Fill in over time; do not delete until replaced with real content.

---

<!--
  WHY THIS DOC EXISTS
  -------------------
  RUNBOOK.md is the answer to every "how do I..." question about THIS
  specific project. README.md sells the project; RUNBOOK.md runs it.

  Audience: future-you at 2am when prod is down, a new dev on day 3, an
  on-call engineer who has never seen this codebase.

  Rule: every command must be copy-pasteable. No "you know what I mean"
  pseudo-commands. If a step requires judgment, write what the judgment is.

  How to use this template:
    1. Copy to your project root as RUNBOOK.md
    2. Fill in every {{PLACEHOLDER}}
    3. Delete any section that genuinely doesn't apply (e.g., no DB? drop the DB section)
    4. Test it: hand it to someone who has never touched the project. If they get stuck, fix the doc.
-->

# Big7Construction — Runbook

**Last updated:** 2026-06-29
**Owner:** Michael Martinez
**Repo:** {{REPO_URL}}

---

## Quick reference

| Task | Command |
|---|---|
| Run locally | `./build.sh && ./scripts/run.sh` |
| Run tests | `./scripts/test.sh` |
| Build Docker image | `docker build -t Big7Construction .` |
| Deploy | `{{DEPLOY_COMMAND}}` |
| Tail prod logs | `{{LOG_COMMAND}}` |
| Open prod dashboard | `{{DASHBOARD_URL}}` |

---

## 1. Local development

### 1.1 Prerequisites

These must be installed before `build.sh` will succeed.

| Tool | Version | Install |
|---|---|---|
| {{LANG_RUNTIME, e.g. Python 3.11}} | {{exact}} | {{install command or link}} |
| {{PKG_MANAGER, e.g. pip / npm / dotnet}} | {{exact}} | (bundled with runtime) |
| Docker Desktop | latest | https://docker.com/products/docker-desktop |
| {{DATABASE, e.g. Postgres 16}} | 16+ | `docker run -p 5432:5432 -e POSTGRES_PASSWORD=dev postgres:16` |
| {{OTHER_DEPENDENCY}} | {{ver}} | {{link}} |

### 1.2 First-time setup (clean clone)

```bash
git clone {{REPO_URL}}
cd {{PROJECT_DIR}}

# Unix / macOS
./build.sh

# Windows
build.bat
```

`build.sh` / `build.bat` will:
- Verify prerequisites
- Create the virtualenv / install packages / restore .NET packages
- Generate `.env` from `.env.example` if missing (you must fill in real values)
- Run migrations against your local DB
- Build any DLLs / compiled artifacts
- Print a "READY" banner when done

### 1.3 Environment variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description | Where to get it |
|---|---|---|---|
| `{{VAR_NAME}}` | yes | {{what it does}} | {{where to get the value}} |

**Never commit `.env`.** Verify it's in `.gitignore`.

### 1.4 Run the service

```bash
./scripts/run.sh        # Unix
scripts\run.bat         # Windows
```

Then open `{{LOCAL_URL, e.g. http://localhost:8000/docs}}`.

Healthcheck: `GET {{LOCAL_URL}}/health` → returns `200 OK` with JSON body `{"status": "ok"}`.

---

## 2. Tests

### 2.1 Run everything
```bash
./scripts/test.sh
```

### 2.2 Run by tier
```bash
./scripts/test.sh unit         # fast, no external services
./scripts/test.sh integration  # requires DB / message bus running
./scripts/test.sh e2e          # requires service running on {{LOCAL_URL}}
```

### 2.3 Run a single test
```bash
{{TEST_RUNNER_SINGLE_COMMAND, e.g. pytest tests/unit/test_invoice_service.py::test_calculates_tax}}
```

### 2.4 Coverage
```bash
./scripts/test.sh coverage
```
Opens `htmlcov/index.html`. CI fails if service-layer line coverage drops below 70%.

### 2.5 What each tier covers
- **Unit:** service layer, pure functions. Mocked deps. Must run in <30s total.
- **Integration:** real DB (testcontainer), real message bus, real HTTP client against mocked external APIs.
- **E2E:** Selenium / Playwright, real browser, screenshots on failure into `tests/e2e/screenshots/`.

---

## 3. Docker

### 3.1 Build image
```bash
docker build -t Big7Construction:local .
```

### 3.2 Run container
```bash
docker run --rm -p {{HOST_PORT}}:{{CONTAINER_PORT}} --env-file .env Big7Construction:local
```

### 3.3 docker-compose (full local stack)
```bash
docker compose up -d
docker compose logs -f {{SERVICE_NAME}}
docker compose down
```

`docker-compose.yml` brings up the service + every dependency (DB, message bus, etc.) so a contributor can start without installing them.

---

## 4. Database

### 4.1 Migrations
```bash
./scripts/migrate.sh up          # apply pending migrations
./scripts/migrate.sh down 1      # roll back one
./scripts/migrate.sh new <name>  # create a new migration file
```

### 4.2 Seed data
```bash
./scripts/seed.sh
```
Idempotent — safe to re-run.

### 4.3 Connect to local DB
```bash
{{DB_CONNECT_COMMAND, e.g. psql -h localhost -U dev -d Big7Construction}}
```

### 4.4 Connect to prod DB (read-only)
**Use the read-only role**. Never query prod with a write-capable role unless you are running a planned migration.
```bash
{{PROD_DB_READ_COMMAND}}
```

---

## 5. Deploy

### 5.1 Environments

| Env | URL | Branch | Deploy trigger |
|---|---|---|---|
| local | http://localhost:{{PORT}} | any | manual |
| staging | {{STAGING_URL}} | `main` | auto on push |
| production | {{PROD_URL}} | tag `v*` | manual: `{{DEPLOY_COMMAND}}` |

### 5.2 Deploy to staging
Auto on every merge to `main` via CI.

### 5.3 Deploy to production
1. Verify staging is healthy (`{{STAGING_URL}}/health`)
2. Run smoke tests against staging: `./scripts/smoke.sh staging`
3. Tag the release: `git tag -a v{{X.Y.Z}} -m "release notes" && git push --tags`
4. {{DEPLOY_COMMAND}} (or watch CI for the tag-triggered deploy)
5. Verify prod is healthy (`{{PROD_URL}}/health`)
6. Run smoke tests against prod: `./scripts/smoke.sh prod`
7. Post in #releases channel

### 5.4 Rollback
```bash
{{ROLLBACK_COMMAND, e.g. git revert <sha> && git push, or platform-specific rollback}}
```
**Always rollback before debugging if prod is broken.** Fix forward only if rollback would lose data.

---

## 6. Debug

### 6.1 Local
- Logs print to stdout in dev. Set `LOG_LEVEL=DEBUG` in `.env` for more.
- Attach debugger: {{DEBUGGER_INSTRUCTIONS}}

### 6.2 Staging / prod logs
```bash
{{LOG_TAIL_COMMAND, e.g. railway logs --tail, az webapp log tail, fly logs}}
```

### 6.3 Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `build.sh` fails at "installing packages" | Wrong runtime version | Check § 1.1; install correct version |
| 500 on every request | Missing env var | Compare `.env` to `.env.example`, check prod config |
| Tests pass locally, fail in CI | OS-specific path / case sensitivity | Use forward slashes; case-sensitive imports |
| DB connection refused | DB container not running | `docker compose up -d {{DB_SERVICE}}` |
| {{ADD_PROJECT_SPECIFIC}} | | |

### 6.4 When stuck
1. Read the last 500 lines of logs, slowly
2. Reproduce locally with prod env values (sanitized)
3. Check the last 5 commits — did something change at the same time as the symptom?
4. Ask in {{CHANNEL}} with: the symptom, what you tried, the relevant log lines

---

## 7. On-call / incident response

### 7.1 Alerts route to
{{ALERTING_SETUP, e.g. PagerDuty service "X", Slack channel "#alerts-x"}}

### 7.2 Severity
- **SEV1** — full outage. Page on-call. Rollback immediately, investigate after.
- **SEV2** — degraded (>10% errors, slow). Page on-call. Investigate within 1 hour.
- **SEV3** — single feature broken, workaround exists. Open issue, fix next sprint.

### 7.3 During an incident
1. Acknowledge the alert
2. Post in {{INCIDENT_CHANNEL}}: "Investigating {{symptom}}"
3. Decide: rollback or fix-forward (default: rollback)
4. Communicate every 15 min until resolved
5. Post-incident: write a postmortem in `docs/postmortems/YYYY-MM-DD-{{slug}}.md` within 48h

---

## 8. Secrets

| Where | Used for | Managed by |
|---|---|---|
| `.env` (local) | Dev | Each developer; never committed |
| {{PROD_SECRET_STORE, e.g. Railway env, Azure Key Vault, AWS Secrets Manager}} | Staging, prod | {{OWNER}} |

**Rotation:** every 90 days, or immediately if leak is suspected. See `docs/secret-rotation.md`.

---

## 9. Useful one-liners

```bash
# Reset local DB completely
./scripts/db-reset.sh

# Generate OpenAPI spec from running service
curl {{LOCAL_URL}}/openapi.json > openapi.json

# Re-run last failed test
{{LAST_FAILED_COMMAND}}

# Format + lint everything
./scripts/lint.sh --fix
```
