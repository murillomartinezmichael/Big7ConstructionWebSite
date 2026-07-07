# Tests — Big7Construction

Static site. Test surface is intentionally minimal.

## Automated (stdlib)

Runnable on any Python 3.11+ machine with zero setup — `make test` chains all four.

| Test | Purpose | Runs |
|------|---------|------|
| `tests/test_jsonld.py` | LocalBusiness JSON-LD block parses, `@context`/`@type` correct, all money-signal fields present (address, geo, opening hours, offer catalog); `image` + `logo` locked to the branded 1200×630 og-card (not the 206px placeholder). `--selftest` mutates the block 10 known-broken ways and requires each to reject. | `make test-jsonld` |
| `tests/test_seo_files.py` | `sitemap.xml` parses in the sitemap.org 0.9 namespace, `robots.txt` has `User-agent:` + `Sitemap:` lines, and the canonical origin agrees across `sitemap.xml <loc>` / `robots.txt Sitemap:` / `<link rel="canonical">` in `index.html` (guards the silent-drift failure mode where one gets updated but not the others) | `make test-seo-files` |
| `tests/test_conversion.py` | CTA `data-intent="service:*"`/`portfolio:*"` values ↔ `INTENT_TO_TYPE` mapping ↔ `<input name="projectType" value="...">` radios — a full four-way cross-check plus a substring check on the `dataLayer` push + gtag/plausible adapter (locks the conversion money-path against silent regression). `--selftest` mode mutates the golden HTML 8 known-broken ways and requires the *right* error substring for each — `make test-conversion` runs both the golden check AND the selftest so every run proves the assertions still bite. | `make test-conversion` |
| `tests/test_og_twitter.py` | OG + Twitter card meta tags valid on BOTH `index.html` and `404.html`: required tag set present (`og:type`/`title`/`description`/`url`/`image` + `twitter:card`/`title`/`description`/`image`), `og:image` + `twitter:image` locked to the branded `og-card.png` and NOT the 206px `jobsite-01.jpg` placeholder, `og:image:width == 1200` / `height == 630` / `type == image/png`, `twitter:card == summary_large_image`. `--selftest` mutates the baseline 12 known-broken ways (missing tags, http instead of https, placeholder image, wrong dimensions, small-card twitter). Guards the tick-4 branded-card fix against silent regression. | `make test-og` |

Why stdlib only? Two reasons: (a) any future agent on any machine can run the suite without a `pip install` step, and (b) the money paths under test — structured data, crawler discovery, conversion attribution — should not depend on a fragile test toolchain. Rule of thumb: if a test would require `pip install`, it's out of stdlib scope and belongs in an integration/E2E lane instead.

Each of the four tests is self-tested against ≥6 deliberately-broken inputs (missing fields, drifted origins, orphan mappings, placeholder-image regressions, etc.) — never rubber-stamps.

## Manual (pre-deploy)

- **HTML validation** — `npx html-validate **/*.html`
- **Link check** — `npx broken-link-checker http://localhost:8080`
- **Lighthouse** — Chrome DevTools → Lighthouse → Mobile + Desktop; aim ≥90 perf / ≥95 a11y / 100 SEO
- **Real phone preview** — open the live URL on a mobile device (not devtools emulation)

## Not covered by automation today

- Interactive JS: form submit against Formspree, prefill click loop end-to-end (would need Playwright / jsdom — out of stdlib scope).
- Nginx cache-header behavior: only observable against the actual container, not `python -m http.server`. Run `docker build && docker run -p 8080:8080 -e PORT=8080 big7` to smoke, then `curl -I http://localhost:8080/`.
