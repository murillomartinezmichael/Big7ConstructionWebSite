# Big7Construction

Marketing website for Big 7 Construction — full-service commercial, industrial,
and residential general contractor, Metro Atlanta. **Live client site** at
https://big7construction.com/ — treat every content change as client-visible.

## What this actually is

Multi-page static site. No framework, no bundler, no build step.

| Page | Purpose |
|---|---|
| `index.html` | Homepage — lean chooser: hero, two buyer-path cards, trust strip, contact |
| `commercial-industrial.html` | Commercial & Industrial lane — services, portfolio, credentials, FAQ, own intake form |
| `residential-construction.html` | Residential lane (incl. `#home-repair` section) — own intake form |
| `south-fulton-distribution.html` | Flagship case-study page |
| `accessibility.html` | Accessibility statement (WCAG 2.1 AA baseline, LAW #11) |
| `404.html` | Not-found page with lane-recovery nav |

- **CSS** is per-page, inline in each file's `<style>` block (deliberate — see ADRs).
- **JS**: shared money-path code lives in `big7.js` (Formspree submit, intent→radio
  prefill, URL-param prefill, analytics events). It is test-locked money code —
  changes require the suite green. Page-specific decorative JS stays inline.
- **Fonts**: Fraunces + Barlow Condensed + Inter (Google Fonts, async pattern
  with metric-tuned local fallbacks to keep CLS < 0.1).
- **Business facts are single-sourced**: the phone number canonical value lives
  in `site.config.json`; `tests/test_phone.py` fails if any page, JSON-LD block,
  or `big7.js` drifts from it. NOTE: the shipped number is still the reserved
  `(555)` placeholder — real number is client-gated, see `PENDING_MANUAL.md`.
- Old `/home-repair.html` URLs 301 to `/residential-construction#home-repair`
  (`_redirects` on Cloudflare, `nginx.conf` on the fallback).

## Hosting

**Primary — Cloudflare Workers static assets.** Worker `big7` auto-deploys from
GitHub `main` via Workers Builds (`wrangler.jsonc`). Bound to the apex
`big7construction.com` only — `www` was intentionally decommissioned (2026-07-17),
do not re-add it. Security headers ship via `_headers`; redirects via
`_redirects`; pages are served extensionless (`/commercial-industrial`).

**Fallback — Railway (nginx).** `Dockerfile` (`nginx:alpine`) + `nginx.conf`;
`PORT` is injected at container start via `sed`. Kept build- and test-able but
it is not the live host.

## Run locally

```bash
cd Big7Construction
python -m http.server 8080
# open http://localhost:8080
```

Any static file server works — there is nothing to build.

## Test

```bash
make test          # 24 stdlib-only contract suites, each golden + selftest
```

No `make` on Windows? Run any suite directly, exactly as the Makefile does:

```bash
python tests/test_phone.py            # golden check
python tests/test_phone.py --selftest # mutation self-check
```

Container smoke (requires Docker running):

```bash
python scripts/test-container-boot.py   # builds image, boots nginx, probes routes
```

Deploy preflight: `python scripts/preflight-deploy.py --strict`.
CI (`.github/workflows/ci.yml`) runs all three on every push/PR to `main`.

## Deploy

```bash
git push origin main
# Cloudflare Workers Builds auto-deploys (~1–2 min)
curl -sI https://big7construction.com/   # expect HTTP 200
```

Rollback: `git revert <bad-sha> && git push origin main` — static site, no state,
always safe.

## Status

Live on Cloudflare at the apex domain with six public pages. All 24 suites pass
locally; CI re-verifies the branch before merge.
Known placeholders awaiting client input (photos, real phone number) are tracked
in `PENDING_MANUAL.md`.

<!-- standards-block-v1 -->
## Standards & docs

This project follows the cross-repo engineering standards. See the repo-root docs (one level up from this project):

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
