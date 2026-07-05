# Changelog

All notable changes to this project.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Real `/404.html` + no-more-SPA-shim.** Editorial 404 page in brand type + palette + one CTA + `noindex` meta + fonts preloaded via Filament pattern (no render-block regression). `nginx.conf` `try_files` falls through to `=404`; `error_page 404 /404.html;` with `internal;` location prevents direct access. `Dockerfile` copies the file. Was silently rewriting typos + broken inbound links to `/` with HTTP 200 — bad for SEO, user trust, and analytics honesty. Closes STANDARDS §6 deploy-checklist "404 page exists." Commit `d921703`.
- **Project state scaffolding.** `TODO.md`, `STATUS.md`, `DECISIONS.md` per canon Book I §2 (CONTENT.md and CHANGELOG.md already existed). TODO carries the exact Lighthouse re-measurement micro-steps for a 60-second cold start.

### Changed
- **A11y contrast pass** (predicted Lighthouse a11y 93 → 95/96, needs live re-measure). `.brand-sub` color `--ink-400` (#6E757C) → `--ink-500` (#4C5258) — contrast on paper 4.14 → 5.53. `.btn-accent` background `--accent-500` (#E85D2C) → `--accent-600` (#B34419) — white text contrast 3.48 → 5.05. Hover swapped from a bg swap to `filter: brightness(0.88)` to preserve interaction affordance without a new palette token. All 8 `.section-marker span.tabular` inline `opacity: 0.6` → `0.8` (marginal on light dividers; dark-divider case still fails AA — deferred). Commit `ec70763`.
- **`.hero-stats <dl>` flattened.** Dropped 4 wrapper `<div class="hero-stat">`. `<dt>` and `<dd>` are now direct children per WCAG. CSS `grid-auto-flow: row` places 4 dts across row 1 and 4 dds across row 2 — visual layout preserved. Renamed `.hero-stat *` → `.hero-stats *`; grep-verified zero orphans. Commit `b06b4ba`.
- **CDN correctness.** `nginx.conf` gained `Vary: Accept-Encoding` header — gzip is on, without Vary a shared cache can serve a gzipped response to a client that didn't advertise gzip support. Same commit `ec70763`.

### Not-a-change
- **`Cache-Control` headers on `nginx.conf` were not "broken."** Prior TODO PARKED §3 flagged cache-insight=50 in Lighthouse, but the audit was run against `python -m http.server`, not nginx. The nginx.conf already sets `public, max-age=31536000, immutable` at server scope + `max-age=0, must-revalidate` on `/index.html`. Book I §3: repo beats word; correcting the record.

### Requires Railway redeploy to observe
- `404.html` won't serve until nginx rebuilds. `curl -I https://<prod>/does-not-exist` should return `404` + the 404 body after redeploy.
- `try_files =404` change: same rebuild.
- A11y contrast + `Vary` header: `curl -I https://<prod>/` shows `Vary: Accept-Encoding` after redeploy.

- feat(seo): flesh out social + structured-data metadata on `index.html` — `<link rel="canonical">`, `og:site_name`/`og:url`/`og:image`/`og:image:alt`/`og:locale`, `twitter:title`/`twitter:description`/`twitter:image`/`twitter:image:alt`. Extended the existing `GeneralContractor` JSON-LD block with `image`, `logo`, `openingHoursSpecification` (Mon-Fri 07:00-18:00), and a two-division `hasOfferCatalog` (Commercial & Enterprise / Residential & Repair). Existing name/description/areaServed/telephone/email/priceRange/address kept intact.
- feat(security): 5 defense-in-depth response headers on every response — `Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`. Closes SECURITY_AUDIT.md § M3-M6 for Big7Construction (out of original audit scope, surfaced by `verify-security-headers.py` live sweep). Headers duplicated in `location = /index.html` because nginx `add_header` inheritance resets when a nested location declares its own directives. Docker build + curl smoke pending next Railway redeploy.

## [0.1.0] - 2026-07-03

Initial documented release. Prior work committed since 2026-06-15 is being
captured retroactively; see `git log` for the full history.

### Added
- README: replace hardcoded 'C:\Users\Michael\Documents\GitHub\' path with relative reference
- feat: add § 07 The Straight Answers FAQ section
- Wire form to Formspree + add SVG favicon
- Palette shift: copper → orange, muted steel → punchy blue
- Redesign to editorial-tier: single-file HTML, editorial typography, corporate GC positioning
- docs: point CLAUDE.md at repo-wide standards + add tests scaffold
- chore: roll out engineering standards + cross-platform scripts
- Add project governance, docs, and CI/CD infrastructure
- chore: apply project standard — add CLAUDE.md, README, .gitignore
- Add light/dark mode toggle to nav
