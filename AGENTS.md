# AGENTS.md

## What This Is
Static marketing website for Big 7 Construction — a full-service commercial, industrial, and residential contractor. Single-file HTML site served via nginx:alpine on Railway.

## Stack
Single-file HTML5 + embedded CSS (no JS framework, no build step) → nginx:alpine Docker on Railway (port 8080)

## Key Files
- `index.html` — entire site: HTML + all CSS in `<style>` block. Fonts: Anton + Barlow (Google Fonts). Color palette: warm off-white, orange-red, electric blue
- `images/` — project photos and assets
- `nginx.conf` — nginx config; PORT is injected at runtime via `sed`
- `Dockerfile` — `FROM nginx:alpine`, copies site files, runs `sed` to set port

## Run Locally
```bash
cd Big7Construction
python -m http.server 8080
# Open http://localhost:8080
```

## Deploy
Railway — push to main triggers Docker build. nginx serves on `${PORT:-8080}`. Port is injected at container start via `sed -i s/NGINX_PORT/${PORT:-8080}/g nginx.conf`.

## Env Vars
None — fully static site. Railway injects `PORT` automatically for the nginx config substitution.

## Rules
- No JavaScript — pure HTML + CSS
- All styles in the `<style>` block inside `index.html`
- Images go in `images/` and are copied into the Docker image
- YAGNI — no CMS, no JS framework, no build tools


## Standards & docs

This project follows the cross-repo engineering standards:
- `../docs/ENGINEERING_STANDARDS.md` — principles + code quality + Definition of Done
- `../docs/*_STANDARDS.md` — API, testing, observability, security, database, hosting, microservices, accessibility, performance, release
- Local doc-tier: `BRD.md` · `TRD.md` · `RUNBOOK.md` · `ONBOARDING.md` · `CHANGELOG.md` · `CONTRIBUTING.md` · `SECURITY.md`
- ADRs in `docs/adr/`, postmortems in `docs/postmortems/`

---

## End-of-chunk: log to Cockpit

Every shipped chunk (feature end-to-end, doc rolled out, deploy that survives smoke test) gets a Work Log entry in `../COCKPIT.html` — press `l`. No entry = the chunk didn't happen. Full protocol in `../AGENTS.md § DEFINITION OF DONE — Cockpit Work Log`.


<!-- AI-HUB-SYNC:START -->
## Shared AI Hub

This project inherits ../AGENTS.md and the shared product brain at ../AI_HUB.md. Read local CLAUDE.md, TODO.md, and BRD.md before edits.

Current lane: large construction brand site
Current next action: Write and build the three-lane IA before any stack or microservice upgrade.
<!-- AI-HUB-SYNC:END -->
