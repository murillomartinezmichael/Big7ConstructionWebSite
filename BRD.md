# Big7Construction — Business Requirements

**Author:** Michael Martinez (built for client)
**Last updated:** 2026-06-29
**Status:** Live on Railway with custom domain
**Stakeholders:** Big7 Construction client, Michael

---

## Site Architecture Direction (2026-07-09)

Do not split Big7 into three separate sites yet, and do not introduce microservices for a marketing site. Big7 should read like one large company with three clear buyer lanes:

1. **Commercial & Industrial** - GCs, facilities, enterprise/commercial buyers.
2. **Residential Construction** - homeowners planning larger builds, additions, remodels, structural work.
3. **Home Repair & Improvements** - smaller homeowner work that is still profitable: repair, replace, punch-list, exterior/interior fixes.

Recommended next shape: one parent homepage plus real static landing pages for each lane (`/commercial-industrial/`, `/residential-construction/`, `/home-repair/`). Shared brand, shared phone, shared quote form, shared analytics. Split into separate domains/sites only if the company has separate brands, teams, phone numbers, ad budgets, or SEO strategy for each lane.

Tech rule: stay static until the content volume forces a change. If Big7 grows past one page + a few lane pages, upgrade to Astro static pages with content collections. Do not build microservices unless Big7 needs auth, client portals, payments, scheduling, or lead-management workflows.

## 1. Problem

Big7 Construction is positioning to grow from six-figure operation toward multi-seven-figure revenue. Their existing online presence doesn't communicate scale. Prospective residential clients, GCs, and commercial/industrial partners need a site that:
- Looks like a multi-million dollar operation
- Surfaces BOTH home construction (ground-up) AND home repair (fix/replace) — not just commercial
- Reads as competent, present, reachable

## 2. Who has this problem

### Primary users
- **Residential homeowners** needing construction OR repair
- **General contractors** evaluating Big7 as sub/partner
- **Commercial / industrial / enterprise** prospects

### Anti-persona
- Not individual handyman one-off jobs that aren't profitable
- Not DIY traffic

## 3. Success criteria

| # | Metric | Target |
|---|---|---|
| 1 | Inbound leads | > 5/mo within 90 days |
| 2 | Home repair clearly represented | yes |
| 3 | p95 load | < 1.5s |
| 4 | Lighthouse | > 95 all categories |
| 5 | Hosting cost | minimum tier (≤ $5/mo) |

## 4. Scope

### In scope (v1)
- Marketing site with sections: home construction, home repair, commercial, industrial, enterprise framing, all trades (plumbing, electrical, roofing, HVAC, drywall, foundation/concrete)
- Clear CTAs to contact
- Imagery of real work
- Custom domain
- Deploy via Railway nginx:alpine on port 8080

### Out of scope (v1)
- Online booking / quoting
- Customer portal
- Blog
- Multi-language

### Maybe later (v2)
- Quote request form per service
- Project gallery filterable by service line
- Reviews integration (Google Reviews API)

## 5. User stories

1. As a homeowner, I see Big7 does BOTH construction AND repair — not just commercial.
2. As a GC, I find the partnership / subcontracting contact path in one click.
3. As any visitor, I read the site on my phone without zooming.

## 6. Constraints

- Static HTML (no build step preferred for cost + simplicity)
- Railway minimum tier
- MUST reflect both construction AND repair — explicit content rule

## 7. Risks

| Risk | Mitigation |
|---|---|
| Repair buried under commercial messaging | Content audit — equal billing in nav + hero |
| Hosting cost creep | Evaluate Cloudflare Pages migration (free) |
| Mobile UX neglected | Responsive + Lighthouse mobile audit |

## 8. Dependencies

- Custom domain
- Hosting (Railway min tier; CF Pages as $0 alternative)
- Real project photography


<!-- AI-HUB-SYNC:START -->
## AI Product Research Update - 2026-07-09

Source of product truth: ..\AI_HUB.md.

**Lane:** large construction brand site

**Design decision:** One parent brand is right. The design should feel sturdy, premium, and operational, with clear buyer lanes rather than three separate brands. Separate sites would split trust and SEO too early.

**Product direction:** Add three lane pages on the same domain: Commercial & Industrial, Residential Construction, Home Repair & Improvements. Use real proof, job photos, FAQ schema, service areas, shared quote form, and lane-specific CTA intents.

**Scope boundary:** Separate pages, not separate sites. No microservices unless auth, portal, payments, scheduling, or CRM workflows appear.

**Acceptance evidence:** make test; anchor/SEO/schema/form/CTA smoke; mobile Lighthouse when URL is known.
<!-- AI-HUB-SYNC:END -->
