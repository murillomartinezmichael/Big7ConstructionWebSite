# PREPROJECT — Big7Construction

> One-line: multi-page static marketing site (no framework, no build step) for Big 7 Construction,
> a Metro Atlanta commercial/industrial/residential GC — a live paying-client site whose leads are
> the product.
> Ground truth: 2026-08-19 — repo read end-to-end (README / STATUS / TODO / PENDING_MANUAL /
> DECISIONS / deploy.yaml), live probes re-run today, and
> `python scripts/preflight-deploy.py Big7Construction` from the fleet root = READY.

## 1. Where it stands today

**Deployed-but-NOT-released.** Session finding (verified today, treat as fact):

> Deployed and serving at big7construction.com (Cloudflare WORKER named big7, NOT Pages — an empty
> stray Pages project big7construction also exists in the account) but flagged blocked_on_user:
> only 3 images in repo, portfolio is a shell until client photos land. Open PR #12 verdict MERGE
> (canonical URL parity, verified no redirect loops). Live issue PR #12 surfaces but does not fix:
> www.big7construction.com serves a byte-identical 200 copy of the apex with no redirect, and
> plain http:// serves 200 — duplicate-content exposure, parked in PENDING_MANUAL.md.

- `RELEASES.yaml` (2026-08-19 entry) says the same: "do not count this as a shipped product or
  cite it as proof-of-work until the client's photo shoot lands."
- Fleet `projects.yaml:144-163` marks `blocked_on_user: true`, `blocked_since: 2026-08-19`.
- Blocked on: **the client** (job photos, real phone number, testimonial consent) and **Mike**
  (Cloudflare dashboard toggles, PR merges). Nothing is blocked on code.
- Working tree is on branch `design/a11y-2026-08-17` (3 a11y commits + docs rites, pushed to
  origin, not merged; `.gitignore` carries an uncommitted edit). Deploy branch is `main`
  (`deploy.yaml:60`; Workers Builds auto-deploys pushes to it).
- Money ladder: **rung 3** (`../MONEY_LADDER.md:13`). Its exact-next-action cell: Mike reviews
  and merges PR #12.

## 2. Known bugs & issues

1. **P0 — the repo root is the document root, live today.** `wrangler.jsonc` sets
   `assets.directory: "./"`. Re-probed 2026-08-19: `https://big7construction.com/TODO.md` → **200**
   and `/.git/config` → **200**. Every internal doc (TODO, PENDING_MANUAL, DECISIONS, tests,
   session notes) is publicly served on the client's domain. The fix exists in **PR #10**
   (`security(deploy): stop publishing the repo` — `.assetsignore` + source-note scrub) and is
   still open. Per `TODO.md:96-115` the config alone re-breaks unless Workers Builds is also
   restricted to `main` in the Cloudflare dashboard (whether branch pushes actually trigger
   deploys is UNVERIFIED — recorded in TODO, not re-tested here).
2. **www + http duplicate host** — session finding above, verbatim; parked as the "2026-08-07 www
   drift" decision in `PENDING_MANUAL.md` (three options laid out; recommended: 301 www → apex +
   Always Use HTTPS toggle). Re-confirmed today: www → 200, plain http → 200.
3. **Placeholder phone is live on a client site.** `site.config.json` →
   `"digits": "5557000007", "placeholder": true`; ~48 occurrences locked by `tests/test_phone.py`;
   also hardcoded in the failure-path copy at `big7.js:77`. Every click-to-call dials a dead
   number until the swap procedure in `PENDING_MANUAL.md` runs.
4. **Portfolio is a shell.** `images/` holds 3 files, and `jobsite-01.jpg` / `jobsite-02.jpg` are
   byte-identical (12,218 B each) — effectively 2 real photos + the generated OG card.
5. **Content-integrity warts** (parked list, `TODO.md:105-124`, no client input needed): the
   fake-looking `Bid № 2026-0187` on index; `geo`/`hasMap` downtown-Atlanta centroid; hidden
   `.sr-only` Message label on both lane forms; orphaned testimonial CSS incl. the star-rating
   rule; "8 trades" vs "11 trades" contradiction; a warranty contradiction; radio inputs render
   13×13px (WCAG 2.2 § 2.5.8 target size).
6. **Doc drift:** `RELEASES.yaml`'s 2026-07-17 entry still says "www was intentionally
   decommissioned" — contradicted by observed truth and by its own 2026-08-19 entry.
   `STATUS.md`'s header still says "Last verified 2026-07-17."
7. **Stale open PRs:** #4 / #5 (July Cloudflare autoconfig; `wrangler.jsonc` already has
   `name: big7`, so both are obsolete — close), #7 (draft CI-cap), #11 (dependabot setup-python
   bump, unmerged).
8. **Fallback-only duplicate shapes:** on nginx, `/index` and `/home-repair` serve 200 instead of
   redirecting (residual-risk notes in `../docs/PR_REVIEW_2026-08-19.md` § 1). Nothing links
   these; Cloudflare, the live host, behaves correctly.

## 3. Security hardening

Specific to this code — a static site with two outbound money paths and no backend:

- **Asset exposure (the real one):** merge PR #10, restrict the Workers Builds deploy branch,
  then re-probe `/TODO.md`, `/.git/config`, `/PENDING_MANUAL.md`, and `/docs/adr/` for 404.
  `docs/` is served too — the capability-statement PDF is intentional, the ADRs are not.
- **n8n lead-mirror webhook:** URL hardcoded at `big7.js:46`
  (`michaelmurillo.app.n8n.cloud/webhook/big7-lead`, fire-and-forget mirror; Formspree stays
  path-of-record per DECISIONS 2026-07-17). It ships in public page source by design, carries no
  shared-secret header, and the leaked TODO named it — `TODO.md:115` already calls for rotation.
  Rotate after the leak closes; better: add a static token header checked inside the n8n
  workflow, plus an n8n-side dedupe/rate guard so the `leads` data table cannot be spammed.
- **Forms:** Formspree contract is test-locked (`tests/test_form.py`: action, required
  name/email/phone, honeypot, tel ↔ JSON-LD agreement). No secrets involved. Cloudflare
  Turnstile is a later option if spam actually appears — don't pre-build it.
- **Headers:** `_headers` ships the 5 defense-in-depth headers (HSTS w/ includeSubDomains, XCTO,
  XFO DENY, Referrer-Policy, Permissions-Policy); `nginx.conf` mirrors them per-location, locked
  by `tests/test_nginx_headers.py`. **No CSP** — hard while all CSS/JS is inline per ADR-0001; a
  `Content-Security-Policy-Report-Only` header is the cheap first step. Note HSTS only protects
  repeat visitors while plain http:// still answers 200 (item 2.2).
- **Secrets:** none in the repo by design (`.env.example`: "no environment variables required").
  Gitleaks runs twice (the `secrets` job in `ci.yml` AND `secret-scan.yml`) with a
  `.gitleaks.toml` allowlist. Preflight confirms zero required env.
- **Dependency risk:** zero npm/pip runtime dependencies — the supply-chain surface is GitHub
  Actions versions + the `nginx:alpine` base image, both covered by `.github/dependabot.yml`.
- **PII path:** lead name/email/phone mirror to n8n cloud (leads table + notify email). The site
  has no privacy-policy page — worth one paragraph before real lead volume arrives.

## 4. Professionalism gaps

- **Docs:** unusually complete (README, RUNBOOK, BRD, TRD, ONBOARDING, CHANGELOG, SECURITY,
  CONTRIBUTING, ADRs, postmortems dir) and mostly current — except the drift in item 2.6, and the
  fact that all of it is currently public on the client's domain (item 2.1).
- **Tests:** 24 stdlib contract suites, each with golden + mutation selftest (`Makefile`), plus a
  container boot smoke. Genuinely untested: real-browser JS behavior (prefill / submit / focus
  paths — acknowledged out of stdlib scope in `STATUS.md`), live Cloudflare responses (whether
  `_headers` is actually applied, Worker extensionless handling), and Formspree inbox delivery —
  the "verify the two-path test intakes reached the Formspree inbox" checkbox in
  `PENDING_MANUAL.md` has never been ticked.
- **CI:** `ci.yml` (contract suite + strict preflight + container boot; lychee link check is
  `continue-on-error`), `verify.yml` (standards), `secret-scan.yml`. Gap: per `STATUS.md`, CI "can
  become a required PR check via branch protection; it does not block direct pushes" — branch
  protection is not on, and direct pushes to `main` auto-deploy the client's site unreviewed.
  No CODEOWNERS.
- **LICENSE:** present. UNVERIFIED whether an open-source license is intended for a paying
  client's brand copy and photos — confirm with Mike before the photo shoot lands in-repo.
- **Accessibility:** best-in-fleet — measured WCAG AA pass on `design/a11y-2026-08-17` (0 of 80
  text nodes failing contrast, 375px overflow fixed, `<legend>`s, `aria-live` form status, honest
  hero alt), plus `accessibility.html` and `test_a11y_baseline.py`. Gap: that branch is **not
  merged**, so none of it is live; the 13px radio target size is still parked.
- **Error messages:** the 404 page with lane-recovery nav is genuinely good; the form-failure
  message tells visitors to call the fake 555 number (`big7.js:77`).
- **Versioning:** CHANGELOG + RELEASES.yaml ledger — right-sized for a site; keep RELEASES.yaml
  self-consistent (item 2.6).

## 5. Future features

**Now (serves the current blocker):**
- Merge PR #10 + branch-restrict Workers Builds — unpublishes the repo from the client's domain.
- Merge PR #12 — one canonical URL per page on both stacks; verdict already **MERGE** in
  `../docs/PR_REVIEW_2026-08-19.md` § 1.
- Merge `design/a11y-2026-08-17` once the P0 closes — 7 measured a11y wins are sitting unshipped.
- Keep the photo-intake pipeline warm (PhotoPicker `big7` profile, documented in
  `PENDING_MANUAL.md`) so the client shoot can land same-day.

**Next (after release):**
- Clone the case-study template to the 3 remaining pf-cards — gated on Mike confirming each
  project's facts and naming rights (`PENDING_MANUAL.md` 2026-07-20).
- Google Business Profile claim → restore `aggregateRating` JSON-LD with real reviews (the
  fabricated rating was correctly cut 2026-07-19; never re-add without live reviews).
- Wire a real analytics consumer to the already-locked `dataLayer` events (STATUS Rung 6) — the
  funnel is fully instrumented and payload-key-locked, but nothing reads it.
- Restore sourced testimonials once written client consent exists (PR #9 drafts the outreach).

**Later (only if the project earns it):**
- 12 service-area + 7 offering pages — waits on the GBP claim; SEO expansion only after photos
  prove the portfolio.
- Fleet Hub status row (STATUS Rung 7 proposal) — cheap and compounding, but only once Hub's own
  state stabilizes.
- Astro migration only if page count makes the per-page inline CSS painful (DECISIONS 2026-07-09
  names this exact escalation path).

## 6. GitHub & environment files

- **Workflows:** `ci.yml` (static suite + strict preflight + container boot, lychee links,
  gitleaks), `secret-scan.yml` (gitleaks again — intentional belt-and-suspenders; could be
  consolidated), `verify.yml` (scaffold / Makefile 5-target / Dockerfile / tests / .env-not-
  tracked standards). Dependabot covers docker + github-actions only — correct, the repo has no
  other manifests. Issue templates (bug/feature/chore) + PR template present.
- **Missing:** CODEOWNERS; branch protection making CI a required check (today a direct push to
  `main` deploys unreviewed); a post-deploy smoke that fails if `/TODO.md` ever answers 200 again
  (cheap permanent regression lock for the P0).
- **Env files:** `.env.example` present and truthful ("fully static — no environment variables
  required"). Cross-checked 2026-08-19 from the fleet root:
  `python scripts/preflight-deploy.py Big7Construction` → `[READY] 0 required, 0 optional;
  .env.example matches code — no drift.`
- **Deploy contract:** `deploy.yaml` is documentation-grade and explicitly fenced — deploykit
  only speaks the Pages API; `provision --apply` would create a second site and repoint apex DNS
  at `big7.pages.dev`, moving a paying client off the live Worker. Do not run apply. The stray
  empty Pages project `big7construction` in the account (session finding) is exactly the
  confusion this fence predicts — delete the stray project in the dashboard.
- **Name trap:** GitHub repo `Big7ConstructionWebSite`, local folder `Big7Construction`, worker
  `big7` (`deploy.yaml:43-56`). Scripts must never guess between them.

## 7. Priority order

This project is money-ladder **rung 3** and the ladder's gate is "photo intake done" — so the
order below serves getting the site releasable without adding new exposure, explicitly:

1. **Close the P0 leak:** merge PR #10, restrict Workers Builds to `main` (Cloudflare dashboard —
   Mike), then re-probe `/TODO.md` + `/.git/config` for 404. Nothing else ships first.
2. **Rotate the n8n `big7-lead` webhook** (`big7.js:46`) once 1 lands; add a shared-secret header
   check in the n8n workflow.
3. **Merge PR #12** (verdict already MERGE), then flip the two dashboard toggles — 301 www→apex
   and Always Use HTTPS — killing the whole-host duplicate-content exposure PR #12 surfaces but
   cannot fix.
4. **Merge `design/a11y-2026-08-17`** and sweep the parked no-client-input warts (Bid №, geo
   centroid, sr-only label, trades count, the `big7.js:77` phone string).
5. **Land the client gates that make it a release:** photos (PhotoPicker `big7` profile) + real
   phone number (`site.config.json` swap, `PENDING_MANUAL.md` procedure) + Formspree inbox
   spot-check — then flip RELEASES.yaml from `blocked` to `shipped`.
