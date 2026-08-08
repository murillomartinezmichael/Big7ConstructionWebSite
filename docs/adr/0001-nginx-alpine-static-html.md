# ADR-0001: Single-file HTML on nginx:alpine, no framework

**Status:** Accepted
**Date:** 2026-07-03
**Author:** Michael Martinez
**Deciders:** Michael Martinez

## Context

Big 7 Construction needed a real marketing site — commercial + industrial + residential lines under one brand, a portfolio, credentials, testimonials, a contact form, a FAQ. What it did NOT need was a CMS, a login, a database, or any dynamic behavior. The site is content that changes maybe twice a year.

Simultaneously, it needed to be *live* immediately (client wanted it up in under two weeks), *cheap* (Big 7 isn't paying for a Vercel Pro tier just to host a landing page), and *fast to redeploy* if they wanted a copy tweak on a Saturday.

Three shapes were on the table. The wrong pick locks the site into a maintenance model that doesn't match Big 7's actual editing cadence.

## Decision

We will ship Big 7 as a **single-file `index.html` with embedded CSS**, served by **`nginx:alpine` on Railway**. No framework, no build step, no JavaScript.

## Alternatives considered

### Astro or Next.js static site
- **Pro:** Cleaner component reuse across sections. Type-safe content.
- **Con:** Build step, node_modules, framework knowledge to make any edit. Client can't change a phone number without either asking us or learning the toolchain.
- **Why not:** Overkill for a site whose entire "content model" is one file. The friction to edit outweighs the code-reuse benefit at this scale.

### Squarespace / Webflow
- **Pro:** Client-editable, no code needed at all.
- **Con:** Monthly SaaS bill forever. Design constraints. Vendor lockout — if Webflow raises prices we're stuck migrating.
- **Why not:** Big 7 doesn't need in-browser WYSIWYG editing. Michael edits the site during the rare content refresh; a text editor is faster than Webflow.

### GitHub Pages
- **Pro:** Free hosting.
- **Con:** Custom domain + SSL is fiddly. No control over headers. Not the same infra shape as the other Railway-hosted projects, which increases mental context-switching cost.
- **Why not:** Railway is already the deploy target for the rest of the fleet (SiteGuide, CompanySite). Consistency wins.

## Consequences

### Positive
- **Entire site is one file.** Any change is a git-diffable edit; PR reviews are trivial.
- **Cold-start deploy in 30 seconds** — nginx:alpine is ~10 MB, Railway build is copy-file + start-nginx.
- **No build step means no build breakage.** The site is exactly what's committed.
- **Consistent deploy shape with the rest of the fleet** (SiteGuide, CompanySite, Aries V1 all use nginx-static on Railway).
- **Portable escape hatch:** the file works from any static host (Cloudflare Pages, GitHub Pages, S3+CloudFront) if Railway ever prices us out.

### Negative / trade-offs accepted
- **No component reuse.** Copy-pasted patterns across sections. When we redesign the § headers, we edit every occurrence. Acceptable at ~2500 lines; not acceptable at 10000.
- **No CMS.** Adding a new testimonial requires editing HTML. Fine at Big 7's editing cadence (~2 times/year); we'd revisit if it became weekly.
- **CSS is embedded.** No separate stylesheet to cache — first-load hits the whole file. At Big 7's traffic scale, this is a wash.

### Neutral
- Migration path exists: if the site grows past its single-file ceiling (~5000 lines), the natural next step is Astro with the same design system ported into components. Big 7's design language would survive the migration intact.

## References

- [`CLAUDE.md`](../../CLAUDE.md) — "No JavaScript — pure HTML + CSS" rule
- [`../../index.html`](../../index.html) — the entire site (2600+ lines, § 01 through § 08)
- [`../../nginx.conf`](../../nginx.conf) — port-injection config for Railway
- [`../../Dockerfile`](../../Dockerfile) — `FROM nginx:alpine`
- Related standard: [`../../../docs/HOSTING_STANDARDS.md`](../../../docs/HOSTING_STANDARDS.md) — Railway static-nginx pattern
- Sibling adopter: [`../../../CompanySite/CLAUDE.md`](../../../CompanySite/CLAUDE.md) — same shape for the Offload Labs marketing site
