# Big7Construction
Marketing website for Big 7 Construction — full-service commercial, industrial, and residential contractor. Static HTML site on Railway.

## Stack
- HTML5 + embedded CSS (no build step, no JS framework)
- Google Fonts: Anton + Barlow
- nginx:alpine → Railway (port 8080)

## Setup
```bash
cd Big7Construction

# Serve locally
python -m http.server 8080
# Open http://localhost:8080
```

## Environment Variables
None — fully static site. Railway injects `PORT` for nginx config.

## Deploy
Railway — push to main triggers Docker build. nginx:alpine serves on `${PORT:-8080}`.

## Status
Live. Single-page site covering commercial, industrial, and residential construction services.

<!-- standards-block-v1 -->
## Standards & docs

This project follows the cross-repo engineering standards. See top-level docs at `C:\Users\Michael\Documents\GitHub\`:

| Doc | Purpose |
|---|---|
| `ENGINEERING_STANDARDS.md` | Principles + code quality + stack picking + Definition of Done |
| `docs/TESTING_STANDARDS.md` | Test pyramid, coverage gates |
| `docs/API_STANDARDS.md` | REST + Swagger + Postman conventions |
| `docs/OBSERVABILITY_STANDARDS.md` | Logs / metrics / traces / health / alerts |
| `docs/SECURITY_STANDARDS.md` | OWASP top 10, auth, secrets, supply chain |
| `docs/DATABASE_STANDARDS.md` | Schema, migrations, indexing |
| `docs/HOSTING_STANDARDS.md` | Hosting picks + cost ladder |
| `docs/MICROSERVICES_STANDARDS.md` | When to split, contracts, fitness function |

Project-specific docs live in this repo at the root: `BRD.md` · `TRD.md` · `RUNBOOK.md` · `ONBOARDING.md` · `CHANGELOG.md` · `CONTRIBUTING.md` · `SECURITY.md`.

ADRs live in `docs/adr/`. Postmortems live in `docs/postmortems/`.
