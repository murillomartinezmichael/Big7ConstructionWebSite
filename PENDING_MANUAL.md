# Big7Construction — pending manual gates

Tick-level items only Mike can complete. Sweep at will; each ends in a
checkbox so it clears with a stroke.

## 2026-07-17 two-path restructure

- [ ] **Log this session to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** Two-path restructure merged to main (CI green,
    `f69c0b6`). Homepage → lean chooser (path cards + trust strip, no form);
    commercial + residential became full destination pages each with its own
    tailored Formspree form; home-repair.html folded into
    residential#home-repair with a 301; money JS extracted to shared big7.js
    with a legacy-URL shim; every lead now mirrors to the n8n big7-lead
    webhook (verified live) with lane derived from the new source slugs. All
    21 suites migrated to the 2-lane contracts and green + container smoke +
    strict preflight.
  - **Next up:** live form spot-check after Railway deploy, then bind the
    canonical host (see NEXT ACTION in TODO.md).
  - **Why blocked on him:** Cockpit Work Log is a browser localStorage write.
  - **Resumes:** Nothing blocked — logging only.

- [ ] **Delete the two TEST rows from the n8n `leads` data table**
  - **What to do:** In n8n (michaelmurillo.app.n8n.cloud) open the `leads`
    data table and delete the rows named "TEST ROW — safe to delete" and
    "TEST webhook e2e — safe to delete" (created 2026-07-17 while verifying
    the two-path field mapping + production webhook).
  - **Why blocked on him:** No delete-row surface via MCP; and if left, the
    Follow-up Nudger will draft follow-up emails for them in 2 days.
  - **Resumes:** Nothing blocked — cleanup only.
- [ ] **Verify the two-path test intakes reached the Formspree inbox**
  - **What to do:** After the site deploys, submit each lane form once with
    a marker message and confirm both arrive with the right `_subject`
    ("New commercial bid…" / "New residential bid…") and `source`
    (commercial-industrial-page / residential-page). The n8n mirror copy
    should appear in the `leads` table + notify email at the same time.
  - **Why blocked on him:** Formspree inbox is Mike-only.
  - **Resumes:** Confirms LAW #6/7 verification of the moved money surface.

## 2026-07-13 tick 20e (SHIPPED — locally)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** `tests/test_url_prefill.py` gained a `landing_prefill`
    payload-key contract lock. Before this tick the test only asserted the
    substring `track('landing_prefill'` was present — a refactor that shipped
    `track('landing_prefill', { intent })` (dropping page / src / type /
    did_radio / did_text / did_source) would still pass and silently gut the
    lane-attribution funnel at the dataLayer surface. Now: (a) exactly-one
    call-site check (duplicates double-fire and inflate landing-rate metrics);
    (b) required key set `{intent, type, src, page, did_radio, did_text,
    did_source}` extracted from the payload literal via the same regex
    pattern `test_intake_analytics.py` uses on `intake_submit`. Selftest
    grew from 9 → 15 mutations (drop page / drop src / drop did_source /
    drop type / duplicate call / delete call, all caught). Full 21-suite
    chain still PASS end-to-end.
  - **Files touched:** `tests/test_url_prefill.py`, `Makefile`,
    `SESSION_GOAL.md`, `PENDING_MANUAL.md`
  - **Next up:** Same Rung II PROVE lane. Follow-ups still open from prior
    ticks: (a) `sameAs` social links on homepage LocalBusiness when Mike
    stands up the socials; (b) `?type=<projectType>` CTA param on lane
    pages (blocked on residential-custom / residential-remodel naming
    decision); (c) `aggregateRating` JSON-LD block once real reviews exist.
    All three key events (`cta_click`, `intake_start`, `intake_submit`,
    `landing_prefill`) now have payload-key locks — the CONVERSION_STANDARDS
    § 4 funnel contract is closed at the dataLayer surface.
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-13 tick 20d (SHIPPED — commit `851a187`)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** `tests/test_conversion.py` extended with (a) `LANE_SRC_MAP`
    per-page attribution-slug lock — every lane deep-link's `src=` value must
    equal the canonical slug for the page it's on (home-repair-lane on
    home-repair.html, etc.), catching the cross-lane copy-paste class where a
    service row lifted from commercial-industrial.html into home-repair.html
    with `src=commercial-industrial-lane` left in place would silently
    mislabel every home-repair intake as commercial in dataLayer + Formspree;
    (b) `MIN_LANE_CTAS = 3` floor per lane page — the tick-19 "≥ 1 deep-link"
    floor was too permissive to catch a slow gutting from shipped 4-6 CTAs
    down toward 1. `check_lane_deep_links()` signature grew `expected_src` +
    `min_ctas` kwargs. Selftest 13/13 (8 mapping/attribution + 5 lane
    deep-link; up from 11). Full 19-suite `make test` chain green.
  - **Files touched:** `tests/test_conversion.py`, `Makefile`, `SESSION_GOAL.md`
  - **Next up:** Same Rung II PROVE lane. Follow-ups still open from prior
    ticks: (a) `sameAs` social links on homepage LocalBusiness when Mike
    stands up the socials; (b) `?type=<projectType>` CTA param on lane pages
    (blocked on residential-custom vs residential-remodel naming decision);
    (c) an `aggregateRating` JSON-LD block once real reviews exist; (d)
    mirror the same `page`/`src` lock into `landing_prefill` payload
    contract in `test_url_prefill.py`.
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-12 tick 20c (SHIPPED — locally)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** Lane-attribution loop closed at the dataLayer surface.
    `intake_submit` payload in `index.html` now carries `page: 'home'` and
    `src: <hidden source input value>` alongside the existing intent /
    has_prefill / message_length. Before this tick, a visitor landing via
    a lane link (`?src=commercial-industrial-lane`) whose submit reached
    Formspree with the correct `source` attribution was still dark to
    GA4/Plausible — the funnel view of "which lane page produced the most
    intake submits" could not be answered without leaving analytics.
    Extended `tests/test_intake_analytics.py` `INTAKE_SUBMIT_REQUIRED` to
    include `page` + `src` and added 2 selftest mutations (drop `page`,
    drop `src`) scoped to the intake_submit block so the shared
    `page: 'home'` in cta_click is not stripped by mistake. Selftest now
    15/15 (was 13/13). Full 20-suite chain green end-to-end.
  - **Files touched:** `index.html`, `tests/test_intake_analytics.py`,
    `PENDING_MANUAL.md`
  - **Next up:** Rung VI UPGRADE — natural next bites are (a) mirror the
    same `src`/`page` lock into `landing_prefill` payload contract (extend
    `test_url_prefill.py` from substring checks to full payload-key
    validation), (b) `sameAs` on the homepage LocalBusiness once socials
    exist, (c) `aggregateRating` JSON-LD once real reviews exist.
  - **Move card to:** In Progress (Big7 is a rolling site).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser localStorage; only Mike's browser can write it.

## 2026-07-12 tick 20b (SHIPPED — locally)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** Brand-identity social-preview lock in
    `tests/test_og_twitter.py` — extends the OG contract with (a) per-page
    presence of `og:site_name` / `og:locale` / `og:image:alt` /
    `twitter:image:alt` across all 6 top-level pages, (b) per-page agreement
    that `og:image:alt == twitter:image:alt` (LAW #11 — screen readers on
    social previews must not read different text for the same PNG on FB vs
    Twitter), (c) cross-page brand agreement — those four tags must be
    identical across all 6 pages (they describe the *brand* + the shared
    branded card, not the page). Every tag was already shipped on-page; the
    tick locks them so a future silent edit that drops one now fails CI.
    Selftest 30/30 (12 OG + 5 canonical + 3 uniqueness + 6 brand + 4
    brand-agreement). Full 19-suite chain green.
  - **Files touched:** `tests/test_og_twitter.py`, `Makefile`,
    `SESSION_GOAL.md`, `PENDING_MANUAL.md`
  - **Next up:** Rung VI UPGRADE — natural next bites are (a) `sameAs`
    on the homepage LocalBusiness once socials exist, (b) `aggregateRating`
    JSON-LD once real reviews exist, or (c) locking the on-page `<img alt>`
    text against the shared brand alt-string so a future logo/card swap
    can't drift the two apart.
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-12 tick 20 (SHIPPED — commit `7aef7c1`)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** Per-indexable-page OG uniqueness lock on `og:url` /
    `og:title` / `og:description` across the 5 indexable pages, wired into
    the existing `test-og` recipe. Catches the copy-paste class of drift
    where a new lane page ships with an older page's OG boilerplate — every
    per-page presence + canonical check still passes in that state; only
    cross-page comparison surfaces the mistake. `--selftest` now 20/20
    (12 OG + 5 canonical + 3 uniqueness). Full 19-suite golden chain green.
  - **Files touched:** `tests/test_og_twitter.py`, `Makefile`, `TODO.md`
  - **Next up:** Same rung — natural follow-ups are (a) social-links
    `sameAs` on the homepage LocalBusiness when Mike stands up handles, or
    (b) an `aggregateRating` JSON-LD block once real reviews exist.
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-11 tick 26 (SHIPPED — commit `b288398`)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** Dockerfile-vs-repo drift lock (`tests/test_dockerfile_html.py`)
    that would have caught the tick-17 `accessibility.html`-missing-from-container
    regression; also wired the orphaned `test-service-schema` (tick 25) into
    `make test`. Full 15-suite smoke chain green.
  - **Files touched:** `Makefile`, `tests/test_dockerfile_html.py`
  - **Next up:** Rung VI UPGRADE — Big7 IA cleanup finished on the three lane
    pages; next natural bite is either (a) social-links `sameAs` on the
    homepage LocalBusiness JSON-LD if/when Mike stands up the socials, or
    (b) adding `accessibility.html` to `sitemap.xml` (currently
    Dockerfile-copied but sitemap-excluded).
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-11 tick 28 (SHIPPED — commit `034e093`)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** Conversion-audit fix — the URL-param prefill IIFE was
    reading `?src=` / `?utm_source=` on landing but only pushing the value to
    `window.dataLayer`; Formspree never saw it. Every intake from the three
    lane pages (which route as `/?src=<lane>-lane#contact`) landed with blank
    attribution and the estimator had no clue which lane / bio link drove the
    click. Added a hidden `<input name="source">` to the form and wired the
    IIFE to write the whitelisted `src` value into it on load. `did_source`
    added to the `landing_prefill` event so future analytics measure
    attribution rate for free. Drift-locked in `test_url_prefill.py`
    (6→9 mutations covered, all caught; full 17-suite smoke chain green).
  - **Files touched:** `index.html`, `tests/test_url_prefill.py`
  - **Next up:** Same rung — natural follow-ups are (a) social-links `sameAs`
    on the homepage LocalBusiness JSON-LD when Mike stands up the socials, or
    (b) adding a `?type=<projectType>` param onto each lane page CTA so the
    correct radio pre-selects for lane visitors (residential lane covers both
    `residential-custom` + `residential-remodel`, so this needs a naming
    decision first — not just mechanical).
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-12 tick 19-b (SHIPPED — commit `09f7170`)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** Refactored `hasOfferCatalog` on the homepage
    GeneralContractor JSON-LD from a two-division taxonomy into three
    lane-aligned `OfferCatalog`s whose `url`s point at the three lane
    pages (`commercial-industrial.html`, `residential-construction.html`,
    `home-repair.html`). Schema.org graph now mirrors the on-page
    three-lane IA; all seven existing service Offers preserved and
    regrouped along lane lines — no fabricated service copy. Drift lock
    added: `tests/test_offer_catalog.py` (stdlib-only golden + 15-mutation
    selftest) asserts the parent's three nested-catalog `url`s exactly
    equal each lane page's `Service.url` and each `url` resolves to a
    real on-disk lane file. Wired into `make test`; full 16-suite smoke
    chain green.
  - **Files touched:** `index.html`, `Makefile`,
    `tests/test_offer_catalog.py`
  - **Next up:** Same rung. Follow-ups from prior ticks still open:
    (a) `sameAs` social links on homepage LocalBusiness when socials
    exist, (b) `?type=<projectType>` CTA param on lane pages (blocked on
    residential-custom vs residential-remodel naming decision).
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-12 tick 19-c (SHIPPED — commits `0c72f6a` + `ca8fe1a`)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** `Service.hasOfferCatalog` on all three lane pages
    (`home-repair.html` / `commercial-industrial.html` /
    `residential-construction.html`). Each catalog `itemListElement` has
    an `Offer` whose `itemOffered.@type='Service'`, `name` exactly matches
    the on-page `<span class="service-title">` row (verbatim,
    HTML-unescaped), and `url` points at the intake deep-link. Counts:
    3 + 5 + 3 = 11 offers. Google can now surface each sub-service on
    lane-specific queries instead of only linking the umbrella lane page.
    Drift-lock: extended `tests/test_service_schema.py` (+219 lines)
    with 11 schema-shape mutations + 3 visible↔schema sync mutations, all
    caught by selftest (29/29 mutations). Golden report now prints
    `N offer(s) sync'd to page` per lane.
  - **Files touched:** `home-repair.html`, `commercial-industrial.html`,
    `residential-construction.html`, `tests/test_service_schema.py`
  - **Next up:** Same rung. Open follow-ups still standing:
    (a) `sameAs` social links on homepage LocalBusiness when Mike stands
    up the socials, (b) `?type=<projectType>` CTA param on lane pages
    (blocked on residential-custom / residential-remodel naming
    decision).
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-12 tick 19-d (SHIPPED — meta-descriptions contract lock)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** New stdlib test `tests/test_meta_descriptions.py` +
    `make test-meta-descriptions` recipe. Locks the `<meta name="description">`
    contract on every top-level page: presence, exactly-one, length ∈
    `[40, 220]` (bounds set to accept shipped copy so this is a drift lock,
    not a rewrite mandate), all 6 descriptions unique across pages
    (Google demotes near-duplicates on local-service queries), and no
    description byte-identical to `<title>` (wasted SERP line). Handles
    both attribute orders and HTML-entity decoding via `html.unescape` so
    `&amp;` counts as 1 char in the length check. Selftest catches 6
    mutations + uniqueness lock + false-positive guard, all first run.
    Wired into `make test` — full 17-suite smoke chain still PASS.
  - **Files touched:** `tests/test_meta_descriptions.py` (new),
    `Makefile`, `TODO.md`
  - **Next up:** Same Rung II PROVE lane. Follow-ups still open from prior
    ticks: (a) copy-tightening pass to pull the four over-160-char
    descriptions (index, home-repair, commercial-industrial,
    residential-construction) down toward Google's SERP cap — separate
    tick because it's a marketing-copy decision, not a mechanical one;
    (b) `sameAs` social links on homepage LocalBusiness when Mike stands
    up the socials; (c) `?type=<projectType>` CTA param on lane pages
    (blocked on residential-custom / residential-remodel naming
    decision).
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.

## 2026-07-12 tick 19 (SHIPPED — commit `5eb8b84`)

- [ ] **Log this tick to Cockpit Work Log** (COCKPIT.html — press `l`)
  - **Card:** Big7Construction
  - **What shipped:** `<link rel="canonical">` ↔ `og:url` per-page lock added
    to `tests/test_og_twitter.py`. Silent SEO leak vector closed: if a lane
    page's canonical ever disagrees with its og:url, Google indexes one URL
    while social clicks preview under another. Also enforces exactly-one
    canonical (some CMS bugs leave two on the page) and asserts 404.html
    carries ZERO canonicals (Google's soft-404 guidance) while its og:url
    still routes social clicks to the homepage. 5 new selftest mutations,
    all caught (17 mutations total for `test-og`). Full 15/15 smoke chain
    still PASS. Makefile help text updated.
  - **Files touched:** `tests/test_og_twitter.py`, `Makefile`,
    `SESSION_GOAL.md`
  - **Next up:** Same rung. Natural follow-ups from tick 28's list still
    apply: (a) social-links `sameAs` on homepage LocalBusiness when socials
    exist, or (b) `?type=<projectType>` CTA param on the lane pages (needs
    residential-custom / residential-remodel naming decision from Mike
    before mechanical work starts).
  - **Move card to:** In Progress (Big7 is a rolling site; no "Done" state).
  - **Why blocked on Mike:** COCKPIT.html work log lives in browser
    `localStorage` — cannot be written from CLI. 30 seconds in the browser.
  - **Resumes:** Cockpit shows the entry; next Big7 tick can proceed with a
    clean log timeline.
