# Big7Construction — DECISIONS

Reversible + small choices only. Load-bearing choices live in `docs/adr/`.

---

## 2026-07-09 - One parent site with three buyer lanes, not three separate sites

**What:** Big7 is a large company, but the next cleanup should be one parent site with three lane pages: Commercial & Industrial, Residential Construction, and Home Repair & Improvements. Do not split into separate domains/sites yet. Do not introduce microservices for the marketing surface.

**Why:** the buyers differ, but the brand, trust signals, phone number, quote form, and proof all compound better on one domain. Three separate sites would multiply maintenance, SEO, analytics, and trust work before there is evidence that the lanes need separate brands. Microservices solve runtime complexity; Big7's current problem is positioning and page structure.

**How to escalate if wrong:** split later only if Big7 has separate brands, teams, phone numbers, ad budgets, or SEO campaigns per lane. Upgrade from single-file HTML to Astro static if the page count or repeated sections become painful. Add backend services only for auth, scheduling, client portals, payments, or CRM/lead workflows.

---

## 2026-07-05 · `<dl>` semantic flatten over `<ul>` rewrite

**What:** the hero stat block was `<dl>` → `<div class="hero-stat">` wrappers → `<dt>`/`<dd>` inside. Lighthouse's `definition-list` a11y audit + WCAG both want `<dt>` and `<dd>` as direct children of `<dl>`. Options were (a) drop the wrapper divs, keep semantics, use CSS `grid-auto-flow: row` to place all 4 dts on row 1 and all 4 dds on row 2; or (b) switch to `<ul>` of `<li>` and give up the "term/definition" semantic. Picked (a).

**Why:** the four stats ARE genuinely term/definition pairs ("Projects delivered" → "500+"). `<dl>` is the right element; browsers announce it correctly to screen readers; the semantic is a real accessibility win, not just an audit compliance move. `<ul>` would compile but lose the term/value relationship.

**How to escalate if wrong:** if a design brief later wants each stat as a big vertical block with the number on top of the label (reverse the current order), the CSS grid solution supports it — just change `grid-template-rows` and reorder the dt/dd emission. If both directions get tried and the CSS grows unwieldy, revisit (b).

---

## 2026-07-05 · `.btn-accent` bg from `--accent-500` to `--accent-600` for WCAG AA

**What:** primary CTA background was `#E85D2C` on white text (contrast 3.48 — fails AA at 4.5 for regular text). Bumped to `--accent-600` (#B34419), contrast ~5.05, clears AA. Hover was previously a bg swap from 500 → 600; now that 600 is the base, hover uses `filter: brightness(0.88)` to preserve the "darken on hover" affordance without inventing a new token.

**Why:** the alternative was inventing an `--accent-700` or a specific `--btn-accent-hover` variable, which meant expanding the palette on aesthetic guesswork. `filter: brightness()` is a boring, well-understood CSS pattern that keeps the token count flat.

**How to escalate if wrong:** if the deeper orange reads as "burnt" or muddies the M³-style brand energy, either (a) revert to `--accent-500` and accept the a11y miss with a documented waiver in this file, or (b) tune the accent hue slightly to a color that clears 4.5:1 while feeling brighter — a `#C24618` or so. Both are one-line changes.

---

## 2026-07-05 · `try_files ... =404` over `... /index.html`

**What:** nginx.conf `try_files $uri $uri/ /index.html;` changed to `try_files $uri $uri/ =404;`. Missing paths now return HTTP 404 with a real `/404.html` body instead of silently rewriting to `/`.

**Why:** the site is a static single-page marketing site, not a client-side-router SPA. SPA `try_files` fallback is meaningful when JavaScript owns routing (React Router, etc.); Big7 has no client-side router. Silent rewrites to `/` produce three real harms: (1) Google sees duplicate content at every fake path, hurting SEO; (2) users following a stale/broken link think the destination page is broken, not the link; (3) analytics can't distinguish "typo" traffic from "home page visit." A real 404 with a helpful "back to Big7" CTA is strictly better on all three axes.

**How to escalate if wrong:** if service pages ship (PARKED §4) at deep paths like `/services/framing/` and the docker copy misses them, those paths will 404 hard instead of falling back. That's actually the correct behaviour — every service page must exist as a real file, or it should 404. If a specific redirect is ever wanted (e.g., `/quote` → `/#contact`), add an explicit `location = /quote { return 301 /#contact; }` block rather than reintroducing the SPA-shim fallback.

---

## 2026-07-06 · CONVERSION_STANDARDS.md fix — data-intent taxonomy uses `service:` + `portfolio:` namespaces

**What:** the shared standards doc (`../docs/CONVERSION_STANDARDS.md`) lists six reserved namespaces — `tier:`, `product:`, `feature:`, `plan:`, `book:`, `checkout:`. Big7 sells neither tiers nor SaaS products, and its CTAs feed a shared intake form scoped to project types and portfolio case studies. Rather than force-map to `product:` (misleading — Big 7's "products" are constructed buildings, not the case studies themselves), added two intents: `service:<slug>` for the 7 service-list rows and `portfolio:<slug>` for the 6 case-study cards.

**Why:** the standard's own §2 says "if a CTA's intent doesn't map to one of these, extend the namespace list in this doc." That doc lives at the shared repo root (`../docs/CONVERSION_STANDARDS.md`), and this session's hard constraints forbid touching cross-project shared files. So the extension is applied inline here + noted for a future cross-repo pass. The alternative (invent `service:` silently) is what §2 explicitly forbids — this is the audit trail so a future reviewer doesn't wonder.

**How to escalate if wrong:** if a cross-repo standards pass promotes a different taxonomy (e.g., merges `service:` into `product:`), the `INTENT_TO_TYPE` map in `index.html` is the only place to update — 13 keys, one map, one commit. Portfolio + service HTML anchors would need `data-intent` values updated in a second pass. Total blast radius: ~15 lines.

---

## 2026-07-06 · Textarea prefill uses `— Interested in: <label>` marker, not a horizontal rule

**What:** the shared standards' canonical prefill pattern (§3) uses a horizontal-rule separator to detect prior prefills without overwriting user-typed text. Big7's textarea prefill uses `— Interested in: <label>\n\n` as the marker instead of an HR line.

**Why:** the textarea in Big7's form has no rendered HR (it's a plain `<textarea>`), so a Unicode em-dash + a fixed prefix does the same "identifiable marker" job with fewer characters and a friendlier reading experience for the visitor who *sees* the prefilled text before typing. The `indexOf(PREFILL_MARK) === 0` check preserves the "never overwrite user typing" invariant — if the visitor starts with anything else, we leave it alone.

**How to escalate if wrong:** if analytics later wants to standardize prefill markers across projects, replace the constant `PREFILL_MARK` in one place (line ~2865 of index.html) — one-line change. No structural refactor needed.

---

## 2026-07-05 · 404.html inlines its palette rather than importing from index.html

**What:** the 404 page defines `--paper`, `--ink-500`, `--ink-900`, `--ink-950`, `--accent-600` directly in a small `:root` block instead of loading a shared CSS file.

**Why:** ADR-0001 rejects a build step. Without a build step, there's no way to share CSS variables across files without duplicating a `<link rel="stylesheet">` or hitting a network round-trip on every 404 (which is served to bots more than humans). Duplicating the ~5 tokens is cheap; the 404 page is small (~2 KB gzipped); the maintenance cost of keeping the tokens in sync is a single grep every time the palette changes.

**How to escalate if wrong:** if the palette gets a real revamp (new primary token, restructured ramp), the STANDARDS §5 "5-minute stranger clone" test still passes — but the 404 page will visually drift until it's touched. Grep both files (`grep -E "\\-\\-paper|\\-\\-ink|\\-\\-accent" index.html 404.html`) before any palette change to catch this.

---

## 2026-07-17 — Two-path IA: fold Home Repair into Residential; forms move to lane pages; homepage becomes a chooser

**Decision (with Mike):** collapse the 3-lane IA to 2 buyer paths on one domain (SEO consensus: separate pages, never separate sites). Home Repair became `#home-repair` inside the residential page (old URL 301s, offers merged into the residential OfferCatalog). Each lane page owns a tailored intake form; the homepage keeps NO form — `#contact` routes to the two lane forms. Money JS extracted to shared `big7.js` (no build step) so two forms can't drift as inline copies; legacy `/?intent=` URLs redirect via an inline index shim. Leads mirror to the n8n `big7-lead` webhook fire-and-forget; Formspree remains path-of-record (LAW #7 — don't silently switch a verified money path).

**Why:** the homepage tried to serve both audiences in every section and separated nothing; audience-specific pages rank and convert better; one form per audience kills the irrelevant-radio problem; 3 surfaces of money code needed one shared implementation.

**How to escalate if wrong:** the 301 + shim keep every legacy URL alive, so reverting is additive (rebuild a lane as its own page again). If home-repair volume justifies its own page later, restore `home-repair.html`, re-add the sitemap entry, and drop the nginx 301 — tests will walk the change.

---
