# Big7Construction — TODO

**Last updated:** 2026-07-07 (tick 11 — JSON-LD image/logo upgrade + test lock)
**Stack (locked by ADR-0001):** single-file `index.html` + embedded CSS + nginx:alpine on Railway. Now with a real `/404.html`, `/robots.txt`, and `/sitemap.xml`. No JS framework, no build step.
**Ladder position:** RUNG 2 PROVE — three automated smoke tests chain into `make test` (JSON-LD block w/ image+logo lock + selftest + sitemap/robots + canonical-agreement + conversion IIFE contract). RUNG 3 CLEAN — closed. RUNG 5 INSCRIBE — closed. RUNG 6 UPGRADE — half-shipped (analytics adapter waits on Michael's one-tag activation), JSON-LD imagery now uses the branded 1200×630 card. RUNG 4 QUICKEN — tick 5 added three safe no-visual-change micro-wins. Root-cause 206px placeholder images still client-blocked. Michael-side Lighthouse re-measure still pending.

## SHIPPED (2026-07-07 tick 11 — JSON-LD image/logo upgrade + selftest lock)

- **JSON-LD `image` + `logo` swapped off the 206×206 placeholder onto the 1200×630 branded OG card.** `image` is now `["https://big7construction.com/images/og-card.png", "https://big7construction.com/images/jobsite-01.jpg"]` (Google prefers the first entry, jobsite photo kept as fallback signal). `logo` is now a `schema.org/ImageObject` with `@type`, `url`, `contentUrl`, `width: 1200`, `height: 630`. Rationale: the branded OG card shipped in tick 4 for social previews was never propagated into structured data, so Google's local-pack + Knowledge-Panel candidates were still using the 206×206 placeholder — below Google's 112px organization-logo floor and a weak rich-result surface. LAW 6 clean — both files exist in `images/` (verified in tick 4 with `PIL.Image.open`), no fabrication.
- **`tests/test_jsonld.py` extended + `--selftest` mode + Makefile chain.** Added `image` and `logo` to `REQUIRED_TOP`. New assertions: `image` must be non-empty https URL string or list (every list entry `str` starting with `https://`); `logo` accepts raw https URL OR an `ImageObject` dict with `@type == "ImageObject"`, `url`/`contentUrl` https, `width` int ≥ 112, positive int `height`. `--selftest` mode constructs a minimal-but-valid baseline via `_valid_block()`, then mutates it 10 known-broken ways (image missing / empty / non-https / non-string; logo missing / string-not-https / dict-missing-@type / width-below-min / missing-height / wrong-type) and requires the assertion function to reject each. Baseline PASS + 10/10 mutations caught. `Makefile` `test-jsonld` target now runs both the golden check AND the selftest (matches tick-10 `test-conversion` pattern) so every `make test` proves the assertions still bite. Full stdlib chain (`test-jsonld` → `test-seo-files` → `test-conversion` incl. selftests) all PASS.

## SHIPPED (2026-07-07 tick 10 — Rung II PROVE third bite)

- **`tests/test_conversion.py` + `make test-conversion` — stdlib static test locking the CTA→radio contract on the conversion IIFE.** Same doctrine as ticks 6 + 7 (money-signal path, stdlib only, no `pip install`). Extracts the `const INTENT_TO_TYPE = { ... }` mapping from `index.html:~2876` with a regex, all `<input name="projectType" value="...">` radios, and every `data-intent="service:*"`/`data-intent="portfolio:*"` `<a>` in the HTML. Asserts a four-way cross-check: (1) every mapping value is a real projectType radio value; (2) every CTA intent has a mapping entry (else the click won't prefill the radio); (3) every mapping key is used by ≥1 CTA (dead mapping = CTA removed silently or slug drifted); (4) every radio value is a mapping target (orphan radio = dead code or a service the site quietly stopped selling). Plus substring presence for `track('cta_click'`, `track('intake_submit'`, `dataLayer`, `PREFILL_MARK`, `window.gtag`, `window.plausible` — the attribution loop end-to-end. Passes today: 13 mapping entries ↔ 13 CTA intents ↔ 6 projectType radios all cross-verified; adapter substrings present. Self-tested against 8 broken variants — renamed radio value, removed mapping entry, dead mapping (missing CTA), orphan radio, missing `track('cta_click'` call site, missing `INTENT_TO_TYPE` block, ghost mapping target, baseline — 8/8 caught, baseline PASS. First draft of check 5 initially missed a mutation because `cta_click` also appears in inline comments; tightened to require the specific call-site expression `track('cta_click'` so a comment reference alone can't mask a nuked call. `Makefile` gains `.PHONY` entry + `test: test-jsonld test-seo-files test-conversion` chain. `tests/README.md` rewritten with a three-row Automated table + a "Not covered by automation today" section flagging Playwright/nginx-container as the next lanes if the money path grows beyond stdlib's reach. Rationale: STANDARDS §3 requires tests on money paths — the CTA loop drives every intake, so a silent break is a silent revenue leak. STATUS.md line 15 as of tick 7 explicitly named this test as the next Rung 2 candidate; this closes that flag.

## SHIPPED (2026-07-07 tick 7 — Rung II PROVE second bite)

- **`tests/test_seo_files.py` + `make test-seo-files` — stdlib smoke test on `sitemap.xml` + `robots.txt` + canonical-agreement across all three surfaces.** Same doctrine as tick 6's JSON-LD test: money-signal path (Google crawl discovery + canonical URL correctness), stdlib only (`re`, `xml.etree.ElementTree`, `pathlib`, `urllib.parse`), no pip install. Asserts (a) `sitemap.xml` parses in the sitemap.org 0.9 namespace with ≥1 absolute-`https` `<url><loc>`, (b) `robots.txt` has both `User-agent:` and `Sitemap:` lines, (c) the robots `Sitemap:` URL equals origin-of-sitemap-`<loc>` + `/sitemap.xml`, AND both origins match `<link rel="canonical">` in `index.html`. The cross-file agreement check is the real value — it guards against the silent-drift failure mode where someone updates canonical on one surface (say the domain moves to `www.` or a subpath) but forgets the other two. Self-tested against 8 broken inputs (empty urlset, wrong XML namespace, relative `<loc>`, malformed XML, robots missing `Sitemap:`, robots missing `User-agent:`, cross-file canonical drift, missing canonical) — all 8 caught. Passes today: `python tests/test_seo_files.py` → `OK: sitemap.xml valid (https://big7construction.com/); robots.txt Sitemap: line points at https://big7construction.com/sitemap.xml; matches index.html canonical.` `Makefile` gains `.PHONY` entry + `test: test-jsonld test-seo-files` chain. `tests/README.md` rewritten with an "Automated (stdlib)" section that names both tests and explains why they exist (silent-money-signal regressions). Rationale: tick 6 covered structured data; sitemap/robots was already flagged as the next money-path test in STATUS.md L15 as of tick 6 — this closes that flag.

## SHIPPED (2026-07-07 tick 6 — Rung II PROVE first bite)

- **`tests/test_jsonld.py` + `make test-jsonld` — stdlib smoke test on the LocalBusiness JSON-LD block.** Extracts every `application/ld+json` script from `index.html`, JSON-parses, then asserts required fields for Google local-pack candidacy: `@context == "https://schema.org"`, `@type` includes a `LocalBusiness` subtype, `name`/`description`/`url`/`telephone`/`priceRange`/`openingHoursSpecification`, `address` with `PostalAddress` shape (`addressLocality`/`addressRegion`/`addressCountry`), `geo` with in-range `GeoCoordinates`, non-empty `areaServed`, `hasOfferCatalog` with children. Python 3.11+ stdlib only (`json`, `re`, `pathlib`) — no `pip install`, no network. Passes today (1 block, LocalBusiness schema valid). Self-tested against broken inputs: missing top-level fields → 12 caught, wrong `@context`/`@type` → 14 caught (rubber-stamp test = worse than no test). Wired into `Makefile` as `.PHONY test-jsonld`; `make test` now delegates to it. Rationale: STANDARDS §3 requires tests on money paths, and structured data is the money signal driving Google's local-pack surface for this business. Tick 6 brief offered "JSON-LD LocalBusiness schema block if missing" — the block was already complete after tick 2 (`geo`/`hasMap`), so this tick locks it against silent future regression instead of expanding a well-covered surface.

## SHIPPED (2026-07-07 tick 5 — Rung IV QUICKEN micro-wins, e22f148)

- **Three safe no-visual-change perf hints on `index.html`.** All root-cause-independent, all shippable without waiting on client photos:
  - `decoding="async"` on all 7 `<img>` tags (1 hero portrait at line 1806 + 6 portfolio at lines 2061/2081/2101/2121/2141/2161). Signals off-main-thread decode; compounds with the existing `loading="lazy"` on the six below-fold cards (they're orthogonal — lazy defers the fetch, async defers the decode).
  - `fetchpriority="high"` on the hero-photo `<img>` (index.html:1806). The preload at line 43 already declares high priority for the same URL; matching it on the actual `<img>` gives Chrome an unambiguous LCP-element hint and prevents priority downgrade at layout time.
  - `<link rel="preconnect">` + `<link rel="dns-prefetch">` for `https://formspree.io` (the quote-form action target, index.html:2498). Trims TLS + DNS from the primary money-lever's submit critical path. Preconnect is dropped after ~10s if unused, so no cost when the form isn't submitted.
- **Verified:** stdlib `html.parser` sweep confirms 7 imgs carry `decoding=async` and 2 formspree link hints are present. No image bytes changed, no CSS changed, no layout changed.
- **Predicted delta:** Perf category likely +2 to +5 in Lighthouse mobile emulator (largest single driver is still the 206px placeholder issue — PARKED §1); real-world LCP shave will be observable on the client's phone but hard to prove in emulator throttling noise. Michael-side re-measure step in NEXT ACTION below.

## SHIPPED (2026-07-07, fleet all-day ignition — Rungs III + V + VI triple strike, zero client blockers)

- **Analytics adapter: `dataLayer` → `gtag`/`plausible` bridge (Rung VI UPGRADE — half-shipping the client-blocked NEXT ACTION).** The conversion IIFE from tick 3 has been pushing `cta_click` + `intake_submit` to `window.dataLayer` since 2026-07-06 — but with no consumer, the events were a passive log. Rather than wait on a client-side GA4 ID or a Mike-registered Plausible domain, this session shipped a consumer-agnostic adapter (22 lines vanilla JS, no dep, monkey-patches `dataLayer.push`) that forwards every future push to whichever tag is loaded — none, GA4, Plausible, or both together. Michael's zero-code activation is now a single `<script>` tag drop-in (both snippet variants documented inline right above the adapter). Adapter no-ops on gtag's own `arguments`-shaped pushes so there's no forwarding loop when both are live. Runs after the conversion IIFE; `try/catch` around the forward so a broken consumer script never breaks a CTA click. **Client-blocked half remaining** = Michael pastes the one tag line when he has a domain-registered Plausible property or a client-supplied GA4 Measurement ID.

- **`/robots.txt` + `/sitemap.xml` shipped end-to-end** — closes the two crawler-file PARKED items with a single deploy.
  - `robots.txt`: `User-agent: *` + `Allow: /` + `Sitemap: https://big7construction.com/sitemap.xml` (matches the site's existing canonical + `og:url`).
  - `sitemap.xml`: single `<url>` at `https://big7construction.com/` — `404.html` deliberately excluded (it's `noindex` and served via nginx `error_page ... internal;`, not crawlable per sitemap.org guidance). Comment inline points at TODO PARKED "Service pages per offering (7) + per area (12)" as the moment to add more `<url>` entries — never hypothetical URLs.
  - Parses as valid XML: `xml.etree.ElementTree.parse` reports the sitemap.org 0.9 namespace + 1 url element.
  - `Dockerfile`: two new `COPY` lines land the files into `/usr/share/nginx/html/`.
  - `nginx.conf`: explicit `location = /robots.txt` + `location = /sitemap.xml` blocks with `Cache-Control: public, max-age=3600` (server default of 1-year immutable is wrong for crawler-facing files; downstream CDNs must not pin them for a year) + the 5 defense-in-depth headers re-added inline (SECURITY_AUDIT.md § M3-M6, same reset pattern already used for `/index.html`).
  - Smoke: `python -m http.server 8765` on the repo folder — both files return 200 with correct bytes.

- **Dark-divider `.section-marker span.tabular` contrast fix — closes the last-known AA fail (Rung III CLEAN).**
  Inherited color of `--ink-500` (#4C5258) on `--ink-950` (#08090B) sits at ~3.15 — fails WCAG AA for small text (4.5:1). New rule
  `.divider.dark .section-marker span.tabular { color: var(--ink-200); }`
  puts `#CBCFD3` on `#08090B` at ~11.5 — comfortably passes AA even for the "of 08" counter spans that still carry inline `opacity:0.8` (effective L still >7 with the brighter base). Rule is scoped to `.divider.dark` so the light-divider spans (§03–§07, on `--paper`) are intentionally untouched — they already pass. Predicted a11y ceiling: 96 → 98 (this was the last "known and named" contrast fail on the a11y audit).

- **Deploy delta vs. tick 4 (Michael-side re-measure):**
  a11y predicted 93 → 96 or 98 (dark-divider tabular was the last-known AA fail).
  SEO predicted 100 → 100 in the emulator (Lighthouse doesn't grade robots/sitemap presence directly), but real-crawler impact = Google now knows what to fetch + what schedule.
  Perf unchanged — still root-caused on the 206 px placeholder images (PARKED, client-blocked).

## SHIPPED (2026-07-06 tick 4)

- **Branded 1200×630 OG card + preview-clean meta on both top-level pages.** `images/og-card.png` (36KB) generated by `scripts/gen-og-card.py` — deterministic Pillow render, no client photo needed, byte-identical rerun on the same font stack. `index.html` `og:image` + `twitter:image` swapped from the 206×206 `jobsite-01.jpg` placeholder to the new card; `og:image:width` (1200), `og:image:height` (630), `og:image:type` (`image/png`) declared. `404.html` gained the full OG + Twitter card block (same image, page-specific title/description, `og:url` deliberately set to homepage so a shared stale link previews as the brand and routes visitors to a live page; `noindex` kept). Verified: `PIL.Image.open` reports PNG 1200×630, tag count 11 og-properties on each page. Fixes the practical "previews look bad" problem the prior tags couldn't solve on a 206px source.

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

**Mike-side, one tag line to activate the analytics funnel.** The conversion loop emits `cta_click` + `intake_submit` to `window.dataLayer`, and the 2026-07-07 adapter now mirrors every push to `window.gtag` or `window.plausible` if either is defined. Nothing else in the code needs to change. Drop-in either or both:

- **Plausible (paste inside `<head>`, after the meta block):**
  `<script defer data-domain="big7construction.com" src="https://plausible.io/js/script.js"></script>`
  Requires a Plausible account with `big7construction.com` (or the eventual client domain) registered. Cost: $9/mo or free 30-day trial.

- **GA4 (paste inside `<head>`, after the meta block):**
  ```
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXX"></script>
  <script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-XXXXXXX');</script>
  ```
  Requires GA4 Measurement ID (`G-XXXXXXX`) — client-side or spin one up under M³. Free.

Smoke-test after deploy: click any service row, then either open GA4 DebugView (looks for `cta_click` with `intent=service:<slug>`) or the Plausible dashboard's real-time view. Submit the form with fake info to also trigger `intake_submit` — Formspree still receives it, adapter mirrors it, and the funnel is complete.

**Deferred (Michael-side, unchanged from tick 2):** re-run Lighthouse against a real deploy to verify block-2 a11y bump landed + 2026-07-07 dark-divider tabular fix pushed a11y to 96/98. Micro-steps unchanged — see git history at commit `7ef08e4` for the full script if resurrected.

**Deferred (Michael-side, unchanged from tick 2):** re-run Lighthouse against a real deploy to verify block-2 a11y bump landed. Micro-steps unchanged — see git history at commit `7ef08e4` for the full script if resurrected.

---

## Cloudflare Pages deploy — OPTIONAL migration paste-block (2026-07-06)

Big7 currently ships on Railway (nginx:alpine, works fine). Cloudflare Pages is a viable static-first alternative if you want free-tier hosting + built-in edge cache. **Not urgent** — money ladder rung 3 says "reheat when client sends new shoots." Kept here so a future migration is a paste, not a hunt.

Because Big7 is pure static (no build step, no functions), the deploy is one command:

```powershell
cd C:/Users/Michael/Documents/GitHub/Big7Construction
npx wrangler login                                                # once
npx wrangler pages project create m3-big7construction --production-branch main   # once
npx wrangler pages deploy . --project-name=m3-big7construction --branch=main
```

Wrangler auto-ignores `.git/`, `node_modules/`, `Dockerfile`, and any file listed in `.gitignore`. It'll upload `index.html` + `404.html` + `images/` + `nginx.conf` (harmless on CF Pages — ignored). Add a `.wrangler-ignore` if you want to strip the Docker/nginx files explicitly.

**Custom domain:** dashboard → project → Custom domains → attach the client's domain → follow the CNAME instructions.

**Smoke after deploy:** `curl -sI https://<preview>.pages.dev/` returns 200; `curl -sI https://<preview>.pages.dev/does-not-exist` returns 404 (proves `404.html` is wired).

**When migration WOULD make sense:**
- Railway costs start showing up (Big7 as a static site pays nothing on CF Pages)
- Client asks for a specific CF-only feature (edge redirects, per-request access rules)
- You're already there for CompanySite and want the whole M³ portfolio under one dashboard

**When to stay on Railway:**
- Client has never complained
- Docker/nginx config is dialed in
- Boring-tech law says don't churn what works

## PARKED (do NOT start without a session goal)

- **Real photos** — `images/jobsite-01.jpg` + `jobsite-02.jpg` are 206×206 px, upscaled 3-5× in CSS. Deepest quality issue. Blocked on client sending 6+ real jobsite photos ≥1600 px long edge. Perf 95 won't clear without this. **Note (tick 4): the OG/Twitter card no longer relies on these — social previews are now a proper 1200×630 branded PNG (`images/og-card.png`). The in-page hero + gallery + JSON-LD `image`/`logo` still do.**
<!-- SHIPPED 2026-07-07: dark-divider tabular contrast fix landed as `.divider.dark .section-marker span.tabular { color: var(--ink-200); }` — ratio ~11.5 on the dark bg, well above AA. See SHIPPED block above. -->
- **Unminified / unused CSS** (both Lighthouse audits at 50). Truly fixing means a build step, ADR-1 rejects it. Hand-audit for definitely-dead rules is possible (5-10 min).
- **Service pages per offering (7) + per area (12)** for local SEO. Highest local-search lever remaining. 4-6 hrs shaped as separate `.html` files. Only justified once Google Business Profile is claimed. Note: `try_files ... =404` now correctly 404s non-existent service paths.
- **Trust section with real content** (line 2134 credentials §). Blocked on client input.
- **Quote form lead storage.** Formspree emails leads now. Cloudflare Workers KV row-store only when volume > 3/week.
- **Placeholder phone `(555) 700-0007`** — nav (1688), CTA closer (2405), contact (2572, 2612, 2648), JSON-LD (44).
- **Placeholder email `info@big7construction.com`** — verify domain + inbox.
- **HTTP 200 verification of the live Railway URL.** URL not on file. `PENDING_MIKE.md § J` covers the dashboard lookup.
<!-- SHIPPED 2026-07-07: robots.txt + sitemap.xml shipped end-to-end with Dockerfile + nginx cache/header overrides. When service or per-city pages ship (PARKED §4), extend sitemap.xml with real `<url>` entries. -->
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
