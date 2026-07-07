# Big7Construction — TODO

**Last updated:** 2026-07-06 (auto-improve tick 2/8)
**Stack (locked by ADR-0001):** single-file `index.html` + embedded CSS + nginx:alpine on Railway. Now with a real `/404.html`. No JS framework, no build step.
**Ladder position:** RUNG 3 CLEAN (a11y) + RUNG 5 INSCRIBE (JSON-LD completeness) advancing. RUNG 4 QUICKEN Lighthouse re-measurement still pending (Michael-side).

## SHIPPED (2026-07-06 tick 2)

- **`b9450ce`** — **JSON-LD `geo` + `hasMap`.** Added `GeoCoordinates` (Atlanta 33.7490, -84.3880) and `hasMap` (Google Maps URL) to the existing `GeneralContractor` block. Enables Google local-pack candidacy signal that was missing. Validated by extracting the block and running `python -c "json.loads(...)"` — parses, `@context` + `@type` + `geo` + address + 2-division `hasOfferCatalog` all intact. Deliberately NOT added: `sameAs` (no real social handles on file — LAW 6) and `aggregateRating` (no real reviews — same). Both parked below.

## SHIPPED (2026-07-05, block 2)

- **Checkpoint 1** (`b06b4ba`) — **`.hero-stats <dl>` flattened.** Dropped 4 wrapper `<div class="hero-stat">`. All 4 `<dt>` are now direct children of `<dl>`, followed by all 4 `<dd>`. CSS grid `grid-auto-flow: row` preserves the 4-column visual layout. Renamed `.hero-stat *` CSS selectors to `.hero-stats *` — grep-verified zero orphans. Predicted a11y 93 → ~95 on next Lighthouse pass.
- **Checkpoint 2** (`ec70763`) — **Color-contrast sweep + `Vary: Accept-Encoding`.** `.brand-sub` `--ink-400` → `--ink-500` (4.14 → 5.53 on paper). `.btn-accent` bg `--accent-500` → `--accent-600` (3.48 → ~5.05 on white text); hover moved from a bg swap to `filter: brightness(0.88)`. All 8 `.section-marker span.tabular` `opacity: 0.6` → `0.8` (marginal on light dividers; dark-divider case still fails AA — deferred). nginx gets `Vary: Accept-Encoding` for gzip correctness. **TODO PARKED §3 (cache headers) was a false positive** — nginx.conf already sets `public, max-age=31536000, immutable` at server scope + `max-age=0, must-revalidate` on `/index.html`. Prior Lighthouse cache-insight=50 was measured against `python -m http.server`, not nginx. Book I §3: repo beats word.
- **Checkpoint 3** (`d921703`) — **Real `/404.html` + nginx no longer rewrites broken links.** STANDARDS §6 required a 404 page — never had one. `nginx.conf` `try_files` falls through to `=404` (was silently rewriting typos + broken inbound links to `/` with HTTP 200 — bad for SEO). `error_page 404 /404.html;` + `internal;` location. `Dockerfile` copies the file.
- **Exit-rite state files** (`712edae` + this commit) — `STATUS.md` created with runtime + evolution ladder + Lighthouse timeline + Rung-7 ENVISION proposal. `DECISIONS.md` created with 4 reversible calls. `CONTENT.md` gained 3 filmable moments. `CHANGELOG.md` [Unreleased] catches all three block-2 commits.

## NEXT ACTION (60-second cold start)

**Re-run Lighthouse against a real deploy** (or a locally-hosted `nginx.conf` container) to verify block-2 landed the a11y bump and to see whether Perf category cleared 95 with async-fonts + color-contrast + `<dl>` fixes together.

Micro-steps:
1. Push commits (this session's `push` at exit rite handles that; or `git push origin main` if resumed).
2. Redeploy Big7 to Railway — the a11y + nginx + Dockerfile changes need a rebuild.
3. Get the live URL from Railway dashboard (still not on file — see PARKED §9).
4. `npx lighthouse https://<prod-url> --preset=desktop --output=json --output-path=./lighthouse-post-block2.json --headless=new`
5. Append the deltas to `STATUS.md § Lighthouse timeline` — a11y target 95-96, Perf still 70-ish (real fix is real photos per PARKED §1).

If any score REGRESSES, git-blame this session's commits + revert the specific change. `b06b4ba` (`<dl>` flatten) is the highest risk of visual regression — verify the 4-column hero stat block still renders correctly on mobile (375px width).

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

## QUESTIONS FOR MIKE (session end)

1. Redeploy Big7 to Railway to pick up 404.html + a11y fixes? (yes / no)
2. `.btn-accent` background switched from `--accent-500` (#E85D2C) to `--accent-600` (#B34419) for WCAG AA. Is the deeper orange still on-brand, or revert? (keep / revert)

## References

- `docs/adr/0001-nginx-alpine-static-html.md` — stack lock
- `index.html:1766-1775` — flattened `<dl>` hero-stats
- `index.html:264-266` — `.btn-accent` new colors + filter-based hover
- `nginx.conf:35-45` — new try_files + error_page
- `404.html` — new
- `STATUS.md § Lighthouse timeline` — score history + next entry pending
