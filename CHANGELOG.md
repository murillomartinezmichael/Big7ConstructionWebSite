# Changelog

All notable changes to this project.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
