# Big7Construction — Technical Requirements

**Author:** Michael Martinez
**Last updated:** 2026-06-29
**Status:** Live (static site)
**Links:** [BRD](./BRD.md) · [RUNBOOK](./RUNBOOK.md) · [ONBOARDING](./ONBOARDING.md)

---

## 1. Summary

Static HTML marketing site for Big7 Construction. Served via `nginx:alpine` on Railway, port 8080. No build step (intentional — minimizes dependency surface and ops cost). Single `index.html` with embedded CSS; images in `images/`. Custom Dockerfile uses inline `CMD` to substitute `$PORT` so the same image runs on Railway (which sets `$PORT` at runtime) without CRLF parsing issues from Windows-edited files.

## 2. Non-functional requirements

| Category | Requirement |
|---|---|
| First contentful paint | < 1.5s p95 globally |
| Lighthouse | > 95 Perf / A11y / BP / SEO |
| Cost | minimum tier (~$5/mo Railway or $0 on CF Pages) |
| Availability | 99.5% (single instance is fine for marketing) |

## 2.1 Architecture Direction (2026-07-09)

Current static nginx site remains the right runtime. The cleanup needed is information architecture, not distributed systems.

Recommended path:

1. Keep one domain and one deploy.
2. Add three static lane pages: `/commercial-industrial/`, `/residential-construction/`, `/home-repair/`.
3. Keep one quote form and one analytics adapter. Add hidden `projectType`/`data-intent` values per lane.
4. Extend sitemap only with real pages.
5. If maintaining duplicated HTML becomes painful, migrate to Astro static components.
6. Only add backend/microservices for auth, payments, scheduling, client portal, or lead-management workflows.

## 3. Architecture

```
Static HTML/CSS  →  nginx:alpine  →  Railway (port 8080)
                       │
                       └── images/ folder served as-is
```

## 4. Stack choices

| Concern | Choice | Why |
|---|---|---|
| Markup | Plain HTML5 | No build step, no JS framework |
| Styling | Embedded CSS in `<style>` | Single-file deploy; minimal |
| Server | `nginx:alpine` via Dockerfile | Lightweight, cacheable, portable |
| Hosting | Railway (today) | Evaluate Cloudflare Pages for $0 + global edge |
| Dockerfile | Inline `CMD` substituting `$PORT` | Avoids CRLF issues from Windows-edited shell scripts |

## 5. Content rules

**MANDATORY:** Both Home Construction AND Home Repair must have equal prominence. The site cannot read as "we only do commercial" — residential repair is a significant revenue driver.

Service lines to represent:
- Home Construction (ground-up, structural alteration)
- Home Repair (maintain, fix, replace)
- Commercial
- Industrial
- Enterprise framing
- Trades: plumbing, electrical, roofing, HVAC, drywall, foundation/concrete

## 6. Deploy

- Push to `main` → Railway rebuild + redeploy
- Custom domain configured at Railway DNS
- If migrating to Cloudflare Pages: push to `main` triggers CF Pages build

## 7. Cross-cutting

- No analytics yet → add Plausible ($9/mo) or Cloudflare Web Analytics (free) in v2
- No CMS — content edits are repo edits (acceptable at cadence)
- Security headers added at nginx — verify HSTS, CSP, X-Content-Type-Options

## 8. Open decisions

- **Migrate to Cloudflare Pages?** Saves ~$5/mo, faster edge, free. Risk: minor. Worth doing.
- **Add a contact form?** Currently relies on phone/email. Add Netlify Forms (free) or Resend webhook.

## 9. Future work

- Cloudflare Pages migration (zero-effort win)
- Analytics
- Project gallery filterable by service
- Quote request form
