# Big7Construction — STATUS

**Last verified:** 2026-07-07 (tick 12 — OG/Twitter card contract test + selftest lock)

## Runtime

- **Live URL:** unknown (Railway public URL not backfilled; TODO PARKED §9). Fleet norm probe `https://big7construction-production.up.railway.app/` returned 404 in an earlier block — service is under a non-standard slug.
- **Local dev:** `python -m http.server 8080` at `/` (no build step). Preview at http://localhost:8080. **This does NOT exercise nginx.conf** — cache headers, 404 rewriting, and Vary all only apply when the container runs.
- **Container:** `docker build -t big7 . && docker run -p 8080:8080 -e PORT=8080 big7` to preview the real prod behaviour end-to-end.
- **Stack:** single-file `index.html` + `404.html` + `<style>` block + `nginx:alpine` (non-root) on Railway. Fonts: Anton + Barlow Condensed + Fraunces via Google Fonts (async-loaded).

## Evolution ladder

- Rung 1 HARDEN ✅ — non-root nginx user, security headers (`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`), no dynamic input surface (static site).
- Rung 2 TEST 🔄 (five bites landed, 2026-07-07 ticks 6+7+10+11+12) — `tests/test_jsonld.py` (ticks 6+11) parses the `application/ld+json` block in `index.html` and asserts LocalBusiness shape for Google local-pack candidacy; tick 11 added `image` + `logo` to `REQUIRED_TOP` and a `--selftest` mode (10 broken-mutation cases, all caught). `tests/test_seo_files.py` (tick 7) parses `sitemap.xml` + `robots.txt` and cross-checks canonical origin agrees across `sitemap.xml <loc>`, `robots.txt Sitemap:`, and `index.html <link rel="canonical">` — guards silent-drift. `tests/test_conversion.py` (tick 10) parses the conversion IIFE's `INTENT_TO_TYPE` mapping, all `data-intent="service:*"`/`portfolio:*"` CTAs, and all `<input name="projectType" value="...">` radios — asserts a four-way contract (every mapping value is a real radio, every CTA has a mapping, no dead mapping entries, no orphan radios) plus substring presence of `track('cta_click'` / `track('intake_submit'` / `dataLayer` / `window.gtag` / `window.plausible` to lock the attribution loop end-to-end. `tests/test_og_twitter.py` (tick 12) parses `<meta>` tags on BOTH `index.html` and `404.html`, asserts the required OG + Twitter tag set is present, locks `og:image` + `twitter:image` to the branded `og-card.png` (rejects reversion to the 206px `jobsite-01.jpg` placeholder that tick 4 moved OFF of), asserts `og:image:width == 1200` / `height == 630` / `type == image/png`, asserts `twitter:card == summary_large_image`. All four stdlib-only. `make test` chains via `make test-jsonld test-seo-files test-conversion test-og` and every target runs its selftest alongside the golden check. Each self-tested against ≥8 deliberately-broken variants (tick 12: 12 mutations) — all caught, baselines PASS. Next test-worthy money paths (deferred): live form-submit + click-loop behavior (would need jsdom/Playwright — out of stdlib scope), on-disk existence of the file the `og:image` URL points at (currently the meta-tag contract asserts the URL string, not the byte at that path — a `git rm images/og-card.png` regression would still pass) — see PARKED below.
- Rung 3 CLEAN ✅ (as of 2026-07-07) — a11y contrast + `<dl>` semantic + real 404 landed prior block; dark-divider `.section-marker span.tabular` contrast fixed 2026-07-07 by scoped `--ink-200` override (11.5 contrast, comfortably passes AA). Only outstanding item is dead-CSS sweep, which ADR-0001 rejects at build-tool level and hand-audit ROI is low. Rung CLEAN closed pending Michael-side Lighthouse verification.
- Rung 4 QUICKEN 🔄 — block-1 async-fonts + preload-hero landed the `render-blocking-insight` audit PASS. Tick 5 (2026-07-07, `e22f148`) added three safe no-visual-change hints: `decoding="async"` on all 7 `<img>` tags, `fetchpriority="high"` on hero `<img>` matching the existing preload, and `preconnect`+`dns-prefetch` for `formspree.io` (form action target). Emulated Perf still bounded by 206×206 px placeholder images upscaled 3-5× in CSS (see PARKED §1) — not a code fix; real-world win from tick 5 comes from unambiguous LCP-element hint + form-submit TLS/DNS shave, both invisible in slow-4G emulator throttling.
- Rung 5 INSCRIBE ✅ — README/CLAUDE/BRD/TRD/RUNBOOK/ONBOARDING/CHANGELOG/CONTRIBUTING/SECURITY doc-tier full. Crawler files (`robots.txt` + `sitemap.xml`) shipped 2026-07-07 with correct nginx cache/header overrides; site is now fully addressable to Googlebot on the canonical `big7construction.com/` origin the moment the domain resolves.
- Rung 6 UPGRADE 🔄 — tick 3 landed the conversion loop: `data-intent` on 13 CTAs, project-type radio prefill from click, `cta_click` + `intake_submit` pushed to `window.dataLayer` (GA4-compatible). Tick 4 landed a real 1200×630 branded OG card (`images/og-card.png` via `scripts/gen-og-card.py`) — social previews now render cleanly on both top-level pages instead of a 206px placeholder crop. Remaining under this rung: (a) wire an actual analytics consumer to `dataLayer` (see TODO NEXT), (b) 12 service-area + 7 offering pages waits on Google Business Profile claim.
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

Most recent through 2026-07-07 tick 10 (LOCAL ONLY — brief locked "commit locally, do not push"):
- `<tick-10 pending>` test(rung2): stdlib conversion IIFE contract test — CTA↔radio↔mapping cross-check + attribution-loop substring guard
- `c176e24` test(rung2): stdlib sitemap/robots + canonical-agreement smoke (tick 7)
- `824d25c` docs(status): mark Rung 2 TEST as in-flight (JSON-LD smoke first) (tick 6)
- `063391f` test(rung2): stdlib JSON-LD smoke test on LocalBusiness block (tick 6)
- `5344367` fix(perf): drop decoding=async on hero LCP <img> (tick 5 follow-up)
- `6cdee5b` docs(state): tick-5 Rung IV micro-wins SHIPPED in TODO/STATUS/CHANGELOG
- `e22f148` perf(rung4): decoding=async + formspree preconnect + hero fetchpriority (tick 5)
- `c6edb41` feat(conv): data-intent + form prefill + cta_click on service/portfolio CTAs
- `a2708c9` docs(state): record JSON-LD geo/hasMap ship + park sameAs/aggregateRating
- `b9450ce` feat(seo): add geo + hasMap to GeneralContractor JSON-LD (tick 2)
- `1f971b2` docs(claude): append Cockpit Work Log DoD reminder to project CLAUDE.md
- `7ef08e4` docs(TODO): rewrite for block-2 SHIPPED + Lighthouse-re-measure NEXT ACTION
- `712edae` docs(state): TODO/STATUS/DECISIONS rewritten + CONTENT + CHANGELOG for block-2 ships
- `d921703` feat(404): real 404 page + nginx no longer rewrites broken links to /
- `ec70763` fix(a11y+cdn): color-contrast pass + Vary: Accept-Encoding
- `b06b4ba` fix(a11y): flatten hero-stats <dl> — dt/dd are direct children now
- `feb029e` perf: async-load Google Fonts + preload hero image (RUNG 4) (block 1)
- `d213c8c` feat(seo): expand areaServed to 12 cities + fill Commercial/Residential OfferCatalog services (block 1)
