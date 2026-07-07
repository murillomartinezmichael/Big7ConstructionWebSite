# Big7Construction — STATUS

**Last verified:** 2026-07-06 (auto-improve tick 2/8)

## Runtime

- **Live URL:** unknown (Railway public URL not backfilled; TODO PARKED §9). Fleet norm probe `https://big7construction-production.up.railway.app/` returned 404 in an earlier block — service is under a non-standard slug.
- **Local dev:** `python -m http.server 8080` at `/` (no build step). Preview at http://localhost:8080. **This does NOT exercise nginx.conf** — cache headers, 404 rewriting, and Vary all only apply when the container runs.
- **Container:** `docker build -t big7 . && docker run -p 8080:8080 -e PORT=8080 big7` to preview the real prod behaviour end-to-end.
- **Stack:** single-file `index.html` + `404.html` + `<style>` block + `nginx:alpine` (non-root) on Railway. Fonts: Anton + Barlow Condensed + Fraunces via Google Fonts (async-loaded).

## Evolution ladder

- Rung 1 HARDEN ✅ — non-root nginx user, security headers (`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`), no dynamic input surface (static site).
- Rung 2 TEST ⚠ — no automated tests (n/a for a single-file static site; STANDARDS §3 says "manual verification is fine" for glue/UI).
- Rung 3 CLEAN 🔄 — a11y contrast + `<dl>` semantic + real 404 landed this block. Remaining: dead-CSS sweep (low-value, ADR-locked away from a build step), dark-divider `.section-marker span.tabular` color fix.
- Rung 4 QUICKEN 🔄 — block-1 async-fonts + preload-hero landed the `render-blocking-insight` audit PASS. Emulated Perf score stuck ~70 under Lighthouse's simulated slow-4G throttling. Real bottleneck = 206×206 px placeholder images upscaled 3-5× in CSS (see PARKED §1). Not a code fix.
- Rung 5 INSCRIBE ✅ — README/CLAUDE/BRD/TRD/RUNBOOK/ONBOARDING/CHANGELOG/CONTRIBUTING/SECURITY doc-tier full.
- Rung 6 UPGRADE 🔜 — 12 service-area pages + 7 offering pages (PARKED §4) would land the largest local-SEO lift. Waits on Google Business Profile claim.
- Rung 7 ENVISION 🔜 — see PROPOSAL below.
- Rung 8 RENEWAL — not yet.

## Lighthouse timeline

Prior scores (from 2026-07-05 block 1, TODO SHIPPED):
- Perf category: 74 → 70 after async-font + hero-preload work. Movement inside emulator throttling noise (~±5); the audit-level `render-blocking-insight` genuinely PASSed.
- FCP/LCP raw values unchanged — Lighthouse's slow-4G throttling also throttles the async font fetch, so the emulator doesn't see the real-world win.
- a11y: 93.

Predicted after block 2 (this session; NOT re-measured — Michael-side verify):
- a11y: 93 → 95 or 96 (`<dl>` flatten + `.brand-sub` + `.btn-accent`; dark-divider tabular ratio still 2.14, so 96 is the ceiling).
- Perf: unchanged from block 1. Root cause (206 px placeholders) is not a code fix.
- SEO: 100 → 100 (404 page helps real crawls, not the audit).
- best-practices: unchanged.

Next measurement:
1. Deploy this block's changes to Railway
2. `npx lighthouse <prod-url> --preset=desktop --output=json --output-path=./lighthouse-post-block2.json --headless=new`
3. Append the deltas here as a new dated entry.

## Rung 7 ENVISION — proposal, not built

**Wire Big7 into the fleet-wide `Hub` panel.** `Hub.lock` is claimed today (fleet inventory 2026-07-05). Once the Hub agent's session lands a `/services/:project` route or a static-dump pattern, Big7 should export a small daily JSON with: last commit sha, Lighthouse-Perf, Lighthouse-a11y, whether the placeholder phone `(555) 700-0007` still exists (grep), whether the real Railway URL is on file. That JSON becomes a single row on Michael's Hub dashboard — one glance to know "is Big7 launch-ready today or not." Cheap: ~10 lines of Python at the docker-build step or a nightly GitHub Action; ~40 lines on the Hub side. Compounds every day. Ship after Hub's own state stabilizes.

## Recent commits (heads)

Most recent through 2026-07-06 tick 2:
- `b9450ce` feat(seo): add geo + hasMap to GeneralContractor JSON-LD (this tick)
- `1f971b2` docs(claude): append Cockpit Work Log DoD reminder to project CLAUDE.md
- `7ef08e4` docs(TODO): rewrite for block-2 SHIPPED + Lighthouse-re-measure NEXT ACTION
- `712edae` docs(state): TODO/STATUS/DECISIONS rewritten + CONTENT + CHANGELOG for block-2 ships
- `d921703` feat(404): real 404 page + nginx no longer rewrites broken links to /
- `ec70763` fix(a11y+cdn): color-contrast pass + Vary: Accept-Encoding
- `b06b4ba` fix(a11y): flatten hero-stats <dl> — dt/dd are direct children now
- `feb029e` perf: async-load Google Fonts + preload hero image (RUNG 4) (block 1)
- `d213c8c` feat(seo): expand areaServed to 12 cities + fill Commercial/Residential OfferCatalog services (block 1)
