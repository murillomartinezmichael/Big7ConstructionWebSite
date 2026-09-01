# Shipped-source hygiene

**Rule:** nothing in a file the browser can fetch may reference our internal
governance. No LAW numbers, no `PENDING_MANUAL.md` / `DECISIONS.md` / `TODO.md`
pointers, no test or script paths, no agent/session/tick names, no operator
names, no internal tool names, no admissions about client content quality.

This is a client's live commercial site. "View source" is one keystroke, and a
competitor or the client themselves is exactly the audience for anything we
leave in there.

The reasoning is not lost — it moves here, or into the commit message. This
file is excluded from the deploy by `.assetsignore`, so it is safe to be candid.

---

## 1. The deploy served the entire repository (2026-08-08)

`wrangler.jsonc` sets `assets.directory: "./"`. The repo root **is** the
document root on Cloudflare Workers, which is the host of record. With no
`.assetsignore`, every tracked file was published.

Verified live on `https://big7construction.com` on 2026-08-08, all HTTP 200
with real content:

| Path | Size | What it exposed |
| --- | --- | --- |
| `/PENDING_MANUAL.md` | 36,735 B | The verbatim unattributable testimonials, the open decision about them, the placeholder-phone gate, client-gated photo notes |
| `/TODO.md` | ~114 KB | The full internal backlog |
| `/DECISIONS.md`, `/STATUS.md`, `/CHANGELOG.md` | — | Internal decision log, session status, full changelog |
| `/CLAUDE.md`, `/AGENTS.md` | — | Agent operating instructions, LAW numbering |
| `/tests/*.py`, `/tests/README.md` | — | The whole test suite and its rationale |
| `/scripts/preflight-deploy.py` | 10,282 B | Deploy tooling |
| `/.env.example`, `/.gitleaks.toml`, `/.pre-commit-config.yaml` | — | Config surface and secret-scanning rules |
| `/Dockerfile`, `/nginx.conf`, `/wrangler.jsonc`, `/Makefile`, `/deploy-cf.bat` | — | Infrastructure |
| `/.github/workflows/ci.yml` | — | CI pipeline |
| `/.git/config` | 263 B | The private GitHub remote URL |
| `/.git/index` | 14,097 B | Full file inventory with blob SHAs |
| `/.git/HEAD`, `/.git/logs/HEAD` | — | Build-clone commit SHA |

Git *history* was not retrievable by guessing — the clone is packed, loose
objects returned 404, and `/.git/objects/info/packs` returned 404 with no
directory listing. The metadata above was fully retrievable.

Meanwhile `robots.txt` said, and still says:

```
# Public marketing site. Nothing sensitive on any path.
User-agent: *
Allow: /
```

— actively inviting every crawler to index all of it.

**Fix:** `.assetsignore` at the repo root, deny-list only. The public surface is
already defined precisely by the `Dockerfile`'s explicit `COPY` list (the
Railway/nginx fallback ships those files and nothing else, so that fallback was
never affected). `.assetsignore` makes Cloudflare match it.

`_headers` and `_redirects` are consumed by Cloudflare rather than served —
both verified 404 — so their internal comments do not ship. They are excluded
anyway for consistency.

---

## 2. Comments removed from shipped files (2026-08-08)

Verbatim, so nothing is lost.

### 2.1 The testimonial-removal notes

Four pages carried a comment explaining *why* a testimonial had been pulled.
Each one published our LAW numbering, our internal filenames, and a written
admission that a client testimonial had no documented source.

`index.html` (trust strip):

```html
<!-- Trust-strip quote removed 2026-08-05: no documented source for
     the "Marcus H." attribution (LAW 6). Verbatim quote + restore
     instructions: PENDING_MANUAL.md § "2026-08-05 unattributable
     testimonials". Credential badges above are the published claims. -->
```

`commercial-industrial.html`:

```html
<!-- ─── TESTIMONIALS ── removed 2026-08-05 ───────────────────
     Three quotes shipped here with no documented source (LAW 6 —
     reputational exposure on a client site). Removed pending client
     sign-off; the verbatim quotes + restore instructions live in
     PENDING_MANUAL.md § "2026-08-05 unattributable testimonials". -->
```

`residential-construction.html` carried the same comment, singular ("Quote
shipped here with no documented source").

`south-fulton-distribution.html` (case-study result section):

```html
<!-- Client quote removed 2026-08-05: the "Marcus H." attribution has
     no documented source (LAW 6; PENDING_MANUAL already flagged it as
     inferential). Verbatim quote + restore instructions:
     PENDING_MANUAL.md § "2026-08-05 unattributable testimonials". -->
```

and, inside its Article JSON-LD header comment:

```html
Every fact here mirrors commercial-industrial.html's own pf-card verbatim
(LAW #6 — no invented specifics). The page's testimonial was removed
2026-08-05 pending a documented source (PENDING_MANUAL § "2026-08-05
unattributable testimonials").
```

**Reasoning, preserved:** the testimonials were removed on 2026-08-05 because
no source was documented for the attributions. The verbatim quotes and the
restore procedure remain in `PENDING_MANUAL.md`, section
*"2026-08-05 unattributable testimonials"*, where the decision is still open
pending Mike. The credential badges are the published proof in the meantime.
None of that belongs in shipped HTML.

### 2.2 The portfolio-photo notes

`commercial-industrial.html`, twice:

```html
<!-- No photo: only 2 real jobsite shots exist and both are used
     above — a repeated photo reads as "no real portfolio"
     (competitor research 2026-07-19). Real shots are client-gated
     in PENDING_MANUAL. -->
<!-- No photo — same reason as № 04 above. -->
```

**Reasoning, preserved:** only two real jobsite photographs exist, both already
used higher on the page. Repeating one reads to a prequalifying buyer as "no
real portfolio" (competitor research, 2026-07-19), so the later portfolio cards
run without a photo instead. Real shots are blocked on the client sending the
jobsite photo folder — tracked in `PENDING_MANUAL.md` and enforced at WARN
level by `tests/test_images.py`. Telling a visitor in the page source that the
contractor has only two photographs is precisely the impression the cards were
built to avoid.

### 2.3 The SiteGuide widget block (`index.html`)

```html
<!-- ═══════════════════════════════════════════════════════════════
     SiteGuide widget — Big 7 tenant. Loaded from separately-deployed
     SiteGuide (siteguide-production.up.railway.app). If unreachable
     the rest of the page is unaffected. If the visitor is on an
     origin not listed in SiteGuide/sites/big7.json → allowed_origins,
     /v1/chat returns 403 and the widget stays silent (by design).
     LOCAL DEV: swap both URLs below to http://localhost:8000
                after `cd ../SiteGuide && ./run.sh`.
     ═══════════════════════════════════════════════════════════════ -->
```

The worst of the comment leaks after the testimonials. It published another
product's repo layout (`SiteGuide/sites/big7.json`), its authorization model
(origin allow-list, `/v1/chat` → 403), and local-dev instructions. The two
lane pages carried a shorter version naming the tenant and config.

**Reasoning, preserved:** the widget is loaded from the separately-deployed
SiteGuide service; if it is unreachable the page is unaffected. Access is
gated by an origin allow-list in SiteGuide's own `sites/big7.json` — an
unlisted origin gets a 403 from `/v1/chat` and the widget stays silent, by
design. For local development, point both the `src` and `data-api` URLs at
`http://localhost:8000` after starting SiteGuide locally.

### 2.4 Internal file paths, tool names, and TODO references

Removed across `index.html`, `accessibility.html`, both lane pages,
`south-fulton-distribution.html`, `big7.js` and `sitemap.xml`:

- `Locked by tests/test_og_twitter.py` (×4), `tests/test_breadcrumbs.py` (×3,
  including south-fulton's "Not wired into…"), `tests/test_service_schema.py`
  (×2), `tests/test_url_prefill.py`, `tests/test_lane_nav.py`,
  `tests/test_seo_files.py`, `test_conversion.py`, `test_intake_analytics.py`.
  **The test contracts still hold** — they are simply no longer advertised to
  the browser. `tests/README.md` is the index of what each suite locks.
- `scripts/gen-og-card.py` — regenerate the OG card with
  `python scripts/gen-og-card.py` when the brand or tagline changes.
- `CONVERSION_STANDARDS.md § 2/3/4` (×4 in `big7.js`) — that document remains
  the spec for the intent, prefill, and event contracts.
- `LAW #6/7 — money code` in the `big7.js` file header.
- `Closes TODO PARKED §2 (dark-divider tabular contrast)` in `index.html`'s CSS.
  The contrast override itself and its WCAG arithmetic are unchanged and still
  documented in place.
- `SiteAudit tap_target_size` / `SiteAudit click_to_call` /
  `SiteAudit sticky_mobile_cta` (×5) — the internal audit tool's finding IDs.
  The rules and their WCAG 2.5.8 justification stay; only the tool's private
  identifiers went.
- `tick-27 lane-attribution loop` in `big7.js` — internal session/tick naming.
- `Michael's zero-code activation` in `big7.js` — named the operator on the
  client's own site.
- `n8n automation webhook (leads data table + follow-up nudger + morning
  briefing)` in `big7.js` — described our automation architecture.

Purely technical comments were deliberately **kept**: the font-swap CLS guard,
the WCAG contrast arithmetic, the Filament Group async-font pattern, the
legacy money-URL shim, the JSON-LD rationale, and the pricing-range notes
(whose figures — `$480K`, `$650K`, `$740K`, `$1.9M` — are already visible on
the portfolio cards, so they leak nothing). They explain the code to the next
maintainer and name nothing internal.

---

## 3. Still open

- **`big7.js` posts every lead to `https://michaelmurillo.app.n8n.cloud/webhook/big7-lead`.**
  Not a comment — live code, so it was left alone. It puts the operator's
  personal automation hostname in the client's page source and mirrors client
  lead data to an unauthenticated webhook on a personal tenant. Needs Mike's
  decision: keep, proxy behind a big7-owned hostname, or drop.
- **`robots.txt` claims "Nothing sensitive on any path."** True again once this
  branch deploys; it was not true before.
