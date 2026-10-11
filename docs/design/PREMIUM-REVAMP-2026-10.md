# Big 7 — Premium Revamp Direction (October 2026)

Status: design candidate, **not client-approved or production-deployed**.

## Objective
Upgrade the existing static six-page marketing website into a distinctive, high-trust general contractor presentation for Metro Atlanta. Preserve the commercial/industrial and residential conversion paths, Formspree intake, SEO metadata, accessibility, and performance.

## Design direction
- Editorial architectural photography, large typography, generous spacing, charcoal/limestone palette and restrained construction-orange accents.
- Hero: confident project imagery, concise value proposition, two clear division CTAs.
- Commercial: industrial and distribution construction, process, services, and project evidence.
- Residential: custom homes, structural repairs, renovation services, separate quote path.
- Case study: only verified project facts; no fictional outcomes.
- Mobile: prominent tap targets and sticky contact CTA; respect reduced motion.

## AI image rules
- Generated images may be used for **conceptual/illustrative** hero and service visuals, clearly identified as illustrations in alt text and adjacent context where confusion is likely.
- Do not depict generated projects as Big 7's completed work or imply project ownership.
- Prefer genuine, client-approved project photographs for portfolio, testimonials, and case studies.
- Avoid fake workers, logos, permits, safety certifications, client endorsements, or equipment ownership claims.
- Produce compressed WebP/AVIF with JPEG fallback where appropriate, descriptive filenames, source provenance, and mobile crops.
- Obtain client approval before replacing any live portfolio or case-study image.

## Acceptance gates
1. Preserve the current no-framework static architecture and existing URLs.
2. Keep `big7.js` intake behavior and `site.config.json` business facts unchanged without verified client input.
3. Run all Python golden and mutation self-tests, Node intake runtime tests, strict deployment preflight, and browser mobile/desktop accessibility checks.
4. Compare Lighthouse performance, LCP, CLS, image payload, keyboard navigation and form submission against baseline.
5. Record before/after screenshots and evidence with commit IDs.
6. No production release without client-content approval and successful tests; confirm whether branch pushes trigger deployment before any push.

## Proposed implementation sequence
1. Inventory existing imagery, content, responsive layouts and tests.
2. Build a full local visual prototype of homepage and both buyer lanes.
3. Generate illustrative imagery, optimize, and label appropriately.
4. Integrate pages and preserve metadata/structured data.
5. Test forms, routing, responsive behavior, accessibility, SEO, and performance.
6. Deliver screenshots, test evidence, rollback instructions and owner-review checklist.

## Known blockers
- Canonical phone number remains a 555 placeholder in `site.config.json`.
- Client-approved authentic project photos and testimonial permissions are pending.
- Repository records warn that branch pushes may deploy; staging must be isolated and deployment behavior verified.

## Handoff
Candidate branch: `design/big7-premium-revamp-2026-10`.
Next step: implement the isolated visual prototype and verify it locally before any release.
