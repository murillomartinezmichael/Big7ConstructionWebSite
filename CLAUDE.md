# CLAUDE.md

## What This Is
Static marketing website for Big 7 Construction — a full-service commercial, industrial, and residential contractor. Multi-page static HTML site served via nginx:alpine on Railway.

## Site Architecture Direction (2026-07-17, supersedes 2026-07-09 three-lane IA)

One site, one domain, **two buyer paths** (decision with Mike, 2026-07-17 — do not split into separate sites; that would split domain authority and double maintenance):

1. **Commercial & Industrial** (`/commercial-industrial.html`) — GCs, facilities, enterprise/commercial buyers. Full destination page: services, portfolio, credentials, process, FAQ, own tailored intake form.
2. **Residential Construction** (`/residential-construction.html`) — homeowners: larger builds, additions, remodels, structural work, **plus Home Repair & Improvements as an in-page section (`#home-repair`)**. Own tailored intake form.

The homepage (`index.html`) is a **lean chooser**: hero + company overview + two path cards + trust strip + contact info (phone/email + links to the two lane forms — no form of its own). The old `/home-repair.html` 301s to `/residential-construction.html#home-repair` (nginx + `_redirects`).

Shared brand, shared phone, shared analytics; each lane page carries its own Formspree form (same endpoint, lane-specific `_subject`/`source`/project-type radios).

Tech rule: stay static until the content volume forces a change. If Big7 grows past the homepage + lane pages, upgrade to Astro static pages with content collections. Do not build microservices unless Big7 needs auth, client portals, payments, scheduling, or lead-management workflows.

## Stack
Multi-page static HTML5 + per-page inline CSS + shared `big7.js` (plain static file, no framework, no build step) → nginx:alpine Docker on Railway (port 8080)

## Key Files
- `index.html` — homepage/chooser: HTML + its CSS in `<style>` block + decorative inline JS. Fonts: Fraunces + Barlow Condensed + Inter (Google Fonts, async pattern). Color palette: warm off-white, orange-red, electric blue
- `commercial-industrial.html` / `residential-construction.html` — lane destination pages, each with its own inline `<style>` and intake form
- `big7.js` — shared money-path JS: form submit (Formspree fetch), intent→radio prefill, URL-param prefill, dataLayer analytics adapter. One copy, loaded `<script defer>` on every page. Changes here are money code (LAW #6/7) — tests in `tests/` parse this file
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
- JS is allowed but minimal and dependency-free: shared money-path code lives in `big7.js` (one copy, test-locked); page-specific decorative JS stays inline on its page. No frameworks, no bundler.
- Styles stay per-page in each file's `<style>` block (shared-CSS extraction is a parked follow-up, see TODO.md)
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

Every shipped chunk (feature end-to-end, doc rolled out, deploy that survives smoke test) gets a Work Log entry in `../COCKPIT.html` — press `l`. No entry = the chunk didn't happen. Full protocol in `../CLAUDE.md § DEFINITION OF DONE — Cockpit Work Log`.


<!-- AI-HUB-SYNC:START -->
## Shared AI Hub

Read ../AI_HUB.md after root ../CLAUDE.md and before changing this project. Product lane, UI verdict, and combine/separate decisions are centralized there so Claude and Codex stay synced.

Current lane: large construction brand site

Current next action: Land the two-path restructure (home = chooser, two lane pages with own forms, home-repair 301 → residential#home-repair), then bind the canonical host and backfill the real Railway URL.
<!-- AI-HUB-SYNC:END -->
