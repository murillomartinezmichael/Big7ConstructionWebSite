# AGENTS.md

## What This Is
Static marketing website for Big 7 Construction — a full-service commercial, industrial, and residential contractor. Multi-page static HTML site served via **Cloudflare Workers static assets** (worker `big7`, auto-deploys from GitHub `main`; live at the apex `big7construction.com` — `www` intentionally decommissioned). nginx:alpine on Railway stays in-repo as a tested fallback. **Live paying-client site — treat every content change as client-visible.**

## Stack
Multi-page HTML5 + per-page inline CSS + shared `big7.js` (no framework, no build step) → Cloudflare Workers static assets (`_headers` + `_redirects`) with nginx:alpine Docker on Railway as fallback

## Key Files
- `index.html` (chooser homepage) + `commercial-industrial.html` / `residential-construction.html` (lane pages with own intake forms) + `south-fulton-distribution.html` (case study) + `accessibility.html` + `404.html`. Fonts: Fraunces + Barlow Condensed + Inter (Google Fonts, async pattern). Palette: warm off-white, orange-red, electric blue
- `big7.js` — shared money-path JS (Formspree submit, prefill, analytics). Test-locked money code (LAW #6/7) — do NOT treat this repo as "no JS"
- `site.config.json` — single source of truth for the business phone; `tests/test_phone.py` locks every surface against it (number is still the 555 placeholder — client-gated, see PENDING_MANUAL.md)
- `images/` — project photos and assets
- `nginx.conf` / `Dockerfile` — Railway fallback; PORT injected at runtime via `sed`

## Run Locally
```bash
cd Big7Construction
python -m http.server 8080
# Open http://localhost:8080
```

## Test
`make test` — 24 stdlib-only suites (golden + selftest each), or `python tests/test_<name>.py [--selftest]` directly.

## Deploy
Push to `main` → Cloudflare Workers Builds auto-deploys. Railway fallback: Docker build of nginx:alpine serving on `${PORT:-8080}`.

## Env Vars
None — fully static site. Railway injects `PORT` automatically for the nginx config substitution.

## Rules
- JS is allowed but minimal and dependency-free: shared money-path code lives in `big7.js` (one copy, test-locked); page-specific decorative JS stays inline on its page. No frameworks, no bundler
- Styles stay per-page in each file's `<style>` block (shared-CSS extraction is a parked follow-up)
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
