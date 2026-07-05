# Big7Construction — TODO

**Last updated:** 2026-07-05 (Ignition Prompt session)
**Stack (locked by ADR-0001):** single-file `index.html` + embedded CSS + nginx:alpine on Railway. No JS framework, no build step.
**Ladder position:** RUNG 4 (SPEED) partially climbed this session — see SHIPPED below.

## SHIPPED (recent, chronological)

**2026-07-05 (chunk 1) — SEO / schema.org deepening** (committed as `d213c8c`)
- JSON-LD `GeneralContractor.areaServed` expanded 2 → 13 nodes (12 metro Atlanta cities + GA state).
- `hasOfferCatalog.itemListElement` populated from empty stubs to 7 real `Service` offers (4 Commercial + 3 Residential).
- Portfolio grid: copy-paste comment marker at line 1997 documenting the 4 fields a client edits per new project (no JS, no build tool).
- Page weight verified: 125 KB raw / **24 KB gzipped** (8× under the 200 KB gate).

**2026-07-05 (chunk 2, this session) — RUNG 4 SPEED, one-shot fix**
- Async-loaded Google Fonts stylesheet using the Filament Group pattern (preload + `media=print` + `onload='this.media=all'` + `<noscript>` fallback). Same-origin `preconnect` was already in place.
- Added `<link rel="preload" as="image" href="images/jobsite-01.jpg" fetchpriority="high" />` for the hero LCP candidate.
- Lighthouse mobile before/after (`npx lighthouse` v13.4.0, `--headless=new`, mobile emulation):
  - `render-blocking-insight` audit: **0 → 1 (PASS)**. wastedMs was 786.
  - Category score: 74 → 70 — within throttling noise (~±5). The Speed Index metric moved 63 → 76.
  - FCP/LCP raw values unchanged — Lighthouse's simulated slow-4G throttling also throttles the async font fetch, so the emulator doesn't see the real-world win.
- **Honest read: audit-level PASS is a real improvement (~800 ms off render on real slow devices); score gate 95 still not cleared in the emulator.** Root causes remain (below).

## NEXT ACTION (60-second cold start)

**Fix the CLS on `.hero-stats <dl>` structure (a11y 93 → ~95).** Lighthouse `definition-list` audit calls out `section#hero > div.wrap > div > dl.hero-stats` — each `<div class="hero-stat">` wraps a `<dt>`/`<dd>` pair, but the a11y checker requires `<dt>` and `<dd>` as direct children of `<dl>` in properly-ordered runs. Either drop the wrapper `<div>` (and use CSS grid on the `<dl>` directly) or switch the semantic to `<ul>` of `<li>` with visual styling. ~30 min including a re-run.

## PARKED (do NOT start without a session goal)

- **Real photos** — `images/jobsite-01.jpg` and `jobsite-02.jpg` are **206×206 pixels** (verified via PIL 2026-07-05). All 6 portfolio cards + the hero all reuse those two 206px thumbnails, upscaled 3-5× in CSS. This is the deepest quality issue on the site. Real fix: client sends 6+ real jobsite photos at ≥1600 px long edge. Blocked on client.
- **Color-contrast a11y** (5+ violations). Lighthouse concretely names: `.brand-sub` #6e757c on paper (4.14, needs 4.5); `.btn` white on some fill (3.48); `.section-marker span.tabular` (2.51, opacity 0.6 amplifies the miss); `.section-marker span.tabular` inside dividers (1.61). Fix path: bump ink-400 → ink-500 (#4C5258) in these spots; drop opacity 0.6 to 0.8 on section-marker span.tabular. ~20 min.
- **Cache headers in `nginx.conf`.** Lighthouse `cache-insight` = 50. Add per-asset `Cache-Control: public, max-age=31536000, immutable` for `/images/*` and `/*.woff2`, plus `Cache-Control: public, max-age=3600` for HTML. ~5 min. Needs a Railway redeploy to observe.
- **Unminified / unused CSS** (both audits at 50). Truly fixing would mean a build step, which ADR-0001 explicitly rejects. Alternative: hand-audit the `<style>` block for definitely-dead rules only.
- **Service pages per offering (7) + per area (12)** for local SEO. Highest local-search lever remaining. Requires ~4–6 hrs to shape as separate `.html` files served by same nginx. Only justified if Google Business Profile is claimed.
- **Trust section with real content** (line 2134 credentials §). Currently editorial framing only. Blocked on client input.
- **Quote form lead storage.** Formspree emails leads (line 2418). If searchable log is wanted → Cloudflare Workers KV row-store. Not needed until lead volume > 3/week.
- **Placeholder phone `(555) 700-0007`** — needs real number before public launch. Locations: nav (1688), CTA closer (2405), contact (2572, 2612, 2648), JSON-LD (44).
- **Placeholder email `info@big7construction.com`** — verify domain owned + inbox routing.
- **HTTP 200 verification of the live Railway URL.** URL isn't on file. `PENDING_MIKE.md § J` covers the dashboard lookup.

## QUESTIONS FOR MIKE (session end)

None. Session ran fully on independent authority.

## References

- `docs/adr/0001-nginx-alpine-static-html.md` — why we're not on Astro
- `index.html:34` — JSON-LD block
- `index.html:1997` — portfolio copy-paste marker
- `index.html:30-38` — head render-block fix (this session)
