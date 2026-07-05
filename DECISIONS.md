# Big7Construction — DECISIONS

Reversible + small choices only. Load-bearing choices live in `docs/adr/`.

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

## 2026-07-05 · 404.html inlines its palette rather than importing from index.html

**What:** the 404 page defines `--paper`, `--ink-500`, `--ink-900`, `--ink-950`, `--accent-600` directly in a small `:root` block instead of loading a shared CSS file.

**Why:** ADR-0001 rejects a build step. Without a build step, there's no way to share CSS variables across files without duplicating a `<link rel="stylesheet">` or hitting a network round-trip on every 404 (which is served to bots more than humans). Duplicating the ~5 tokens is cheap; the 404 page is small (~2 KB gzipped); the maintenance cost of keeping the tokens in sync is a single grep every time the palette changes.

**How to escalate if wrong:** if the palette gets a real revamp (new primary token, restructured ramp), the STANDARDS §5 "5-minute stranger clone" test still passes — but the 404 page will visually drift until it's touched. Grep both files (`grep -E "\\-\\-paper|\\-\\-ink|\\-\\-accent" index.html 404.html`) before any palette change to catch this.

---
