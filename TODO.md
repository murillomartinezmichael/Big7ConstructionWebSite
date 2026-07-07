# Big7Construction — TODO

**Last updated:** 2026-07-06 (auto-improve tick 3/8)
**Stack (locked by ADR-0001):** single-file `index.html` + embedded CSS + nginx:alpine on Railway. Now with a real `/404.html`. No JS framework, no build step.
**Ladder position:** RUNG 3 CLEAN (a11y) + RUNG 5 INSCRIBE (JSON-LD completeness) advancing. RUNG 6 UPGRADE now taking a bite (conversion loop closed). RUNG 4 QUICKEN Lighthouse re-measurement still pending (Michael-side).

## SHIPPED (2026-07-06 tick 3)

- **`c6edb41`** — **Conversion audit — CTA `data-intent` + form prefill + `cta_click`/`intake_submit` attribution.** CONVERSION_STANDARDS.md §§2/3/4 gap-fill. 7 service-list rows + 6 portfolio cards now carry `service:<slug>` / `portfolio:<slug>` intents. One IIFE below the existing form-submit handler: on any `[data-intent]` click it pushes `cta_click` to `window.dataLayer` (GA4-compatible, no analytics dep required today), selects the matching `projectType` radio if not already checked, and seeds the textarea with `— Interested in: <label>`. Form-submit fires `intake_submit` with `has_prefill` bool. Verified: 13 CTAs, 13 unique intents, every mapped `projectType` value exists as a real radio. Kills anti-pattern §8 "CTA scrolls to a form that's blank" — the top gap called out in this tick's brief.

## SHIPPED (2026-07-06 tick 2)

- **`b9450ce`** — **JSON-LD `geo` + `hasMap`.** Added `GeoCoordinates` (Atlanta 33.7490, -84.3880) and `hasMap` (Google Maps URL) to the existing `GeneralContractor` block. Enables Google local-pack candidacy signal that was missing. Validated by extracting the block and running `python -c "json.loads(...)"` — parses, `@context` + `@type` + `geo` + address + 2-division `hasOfferCatalog` all intact. Deliberately NOT added: `sameAs` (no real social handles on file — LAW 6) and `aggregateRating` (no real reviews — same). Both parked below.

## SHIPPED (2026-07-05, block 2)

- **Checkpoint 1** (`b06b4ba`) — **`.hero-stats <dl>` flattened.** Dropped 4 wrapper `<div class="hero-stat">`. All 4 `<dt>` are now direct children of `<dl>`, followed by all 4 `<dd>`. CSS grid `grid-auto-flow: row` preserves the 4-column visual layout. Renamed `.hero-stat *` CSS selectors to `.hero-stats *` — grep-verified zero orphans. Predicted a11y 93 → ~95 on next Lighthouse pass.
- **Checkpoint 2** (`ec70763`) — **Color-contrast sweep + `Vary: Accept-Encoding`.** `.brand-sub` `--ink-400` → `--ink-500` (4.14 → 5.53 on paper). `.btn-accent` bg `--accent-500` → `--accent-600` (3.48 → ~5.05 on white text); hover moved from a bg swap to `filter: brightness(0.88)`. All 8 `.section-marker span.tabular` `opacity: 0.6` → `0.8` (marginal on light dividers; dark-divider case still fails AA — deferred). nginx gets `Vary: Accept-Encoding` for gzip correctness. **TODO PARKED §3 (cache headers) was a false positive** — nginx.conf already sets `public, max-age=31536000, immutable` at server scope + `max-age=0, must-revalidate` on `/index.html`. Prior Lighthouse cache-insight=50 was measured against `python -m http.server`, not nginx. Book I §3: repo beats word.
- **Checkpoint 3** (`d921703`) — **Real `/404.html` + nginx no longer rewrites broken links.** STANDARDS §6 required a 404 page — never had one. `nginx.conf` `try_files` falls through to `=404` (was silently rewriting typos + broken inbound links to `/` with HTTP 200 — bad for SEO). `error_page 404 /404.html;` + `internal;` location. `Dockerfile` copies the file.
- **Exit-rite state files** (`712edae` + this commit) — `STATUS.md` created with runtime + evolution ladder + Lighthouse timeline + Rung-7 ENVISION proposal. `DECISIONS.md` created with 4 reversible calls. `CONTENT.md` gained 3 filmable moments. `CHANGELOG.md` [Unreleased] catches all three block-2 commits.

## NEXT ACTION (60-second cold start)

**Wire real analytics onto the `window.dataLayer` events fired by tick 3.** The conversion loop is now emitting `cta_click` and `intake_submit`, but no downstream consumer exists — the events go into `dataLayer` and stop there. Cheapest right move: paste a GA4 gtag.js snippet in `<head>` with a real Measurement ID; every dataLayer push then reports automatically. Alternative: Plausible + a custom-event bridge (10 lines). Do NOT ship a third tag manager. LAW 5.

Micro-steps:
1. Get GA4 Measurement ID from client (`G-XXXXXXX`) — or spin up a free property on Mike's account for now.
2. Paste standard gtag.js snippet after `<head>` opens, before the `<title>` line.
3. Smoke-test locally with `python -m http.server 8080`: click a service row, open GA4 DebugView, confirm the `cta_click` event lands with correct `intent` param.
4. Submit the form with a fake email + name, confirm `intake_submit` fires + Formspree still receives it.
5. Deploy. Verify one live click before closing the tick.

If GA4 is a blocker (client hasn't handed over anything), instead ship a Plausible embed and add a 4-line adapter that mirrors `dataLayer` pushes to `plausible('cta_click', {props: {...}})`. Same event names, same funnels.

**Deferred (Michael-side, unchanged from tick 2):** re-run Lighthouse against a real deploy to verify block-2 a11y bump landed. Micro-steps unchanged — see git history at commit `7ef08e4` for the full script if resurrected.

## PARKED (do NOT start without a session goal)

- **Real photos** — `images/jobsite-01.jpg` + `jobsite-02.jpg` are 206×206 px, upscaled 3-5× in CSS. Deepest quality issue. Blocked on client sending 6+ real jobsite photos ≥1600 px long edge. Perf 95 won't clear without this.
- **Section-marker tabular contrast on DARK dividers** (was 1.61; now ~2.14 after opacity bump — still fails AA). Root: `--ink-400` (#6E757C) on `--ink-950` (#08090B) is a color-pick problem, not opacity. Fix: use `--ink-300` (#9CA3AA) or lighter for tabular specifically on `.divider.dark .section-marker span.tabular`. ~10 min. Named separately so it doesn't slip.
- **Unminified / unused CSS** (both Lighthouse audits at 50). Truly fixing means a build step, ADR-1 rejects it. Hand-audit for definitely-dead rules is possible (5-10 min).
- **Service pages per offering (7) + per area (12)** for local SEO. Highest local-search lever remaining. 4-6 hrs shaped as separate `.html` files. Only justified once Google Business Profile is claimed. Note: `try_files ... =404` now correctly 404s non-existent service paths.
- **Trust section with real content** (line 2134 credentials §). Blocked on client input.
- **Quote form lead storage.** Formspree emails leads now. Cloudflare Workers KV row-store only when volume > 3/week.
- **Placeholder phone `(555) 700-0007`** — nav (1688), CTA closer (2405), contact (2572, 2612, 2648), JSON-LD (44).
- **Placeholder email `info@big7construction.com`** — verify domain + inbox.
- **HTTP 200 verification of the live Railway URL.** URL not on file. `PENDING_MIKE.md § J` covers the dashboard lookup.
- **`/robots.txt` + `/sitemap.xml`.** Neither exists at repo root. Both are SEO wins. `nginx try_files =404` now correctly 404s these — Google will re-crawl once wired. ~15 min. Bundle with service-pages work.
- **JSON-LD `sameAs` social links.** Skipped in 2026-07-06 tick — no confirmed handles. Once client hands over Facebook / Instagram / LinkedIn / Google Business Profile URLs, add them as a `"sameAs": [...]` array right after `hasMap` in the `<script type="application/ld+json">` block (~44–95 in index.html). ~2 min.
- **JSON-LD `aggregateRating`.** Skipped — no real Google/BBB reviews yet. Once ≥3 real reviews exist, add `"aggregateRating": {"@type": "AggregateRating", "ratingValue": <n>, "reviewCount": <n>}`. Sourced from Google Business Profile once claimed. LAW 6 blocks fabricating this.
- **Generic-CTA attribution** — hero "Request a bid →", nav CTA, footer CTAs, "Start a scoping call", "Start at Station 01" etc. all still route to `#contact` without `data-intent`. Adding requires extending the shared standards namespace list (`cta:hero-primary`, `cta:nav-primary`, `cta:footer`, `cta:scoping`) — cannot do without touching `../docs/CONVERSION_STANDARDS.md`, which is out-of-scope for this project's tick. Batch this into the next cross-repo standards pass. ~10 min at that point.
- **Cross-repo standards extension** — propose adding `service:` and `portfolio:` to the reserved-namespaces table in `../docs/CONVERSION_STANDARDS.md § 2`. See `DECISIONS.md` "2026-07-06 · CONVERSION_STANDARDS.md fix" entry for the rationale. Needs a shared-docs session, not a Big7 session.

## QUESTIONS FOR MIKE (session end)

1. Redeploy Big7 to Railway to pick up 404.html + a11y fixes + conversion attribution? (yes / no)
2. `.btn-accent` background switched from `--accent-500` (#E85D2C) to `--accent-600` (#B34419) for WCAG AA. Is the deeper orange still on-brand, or revert? (keep / revert)
3. GA4 Measurement ID for Big7 — do you have one from the client, want me to create one under M³ for now, or ship Plausible instead? (client / m3 / plausible)

## References

- `docs/adr/0001-nginx-alpine-static-html.md` — stack lock
- `index.html:1923-1997` — 7 service-list rows w/ `data-intent="service:<slug>"`
- `index.html:2041-2160` — 6 portfolio cards w/ `data-intent="portfolio:<slug>"`
- `index.html:2850-2914` — conversion IIFE: intent→prefill + dataLayer push (`cta_click`, `intake_submit`)
- `index.html:1766-1775` — flattened `<dl>` hero-stats
- `index.html:264-266` — `.btn-accent` new colors + filter-based hover
- `nginx.conf:35-45` — try_files + error_page
- `404.html` — real 404
- `../docs/CONVERSION_STANDARDS.md` — the standard this tick audited against
- `STATUS.md § Lighthouse timeline` — score history + next entry pending
