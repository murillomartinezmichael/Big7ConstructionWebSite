# Big 7 implementation handoff — October 11, 2026

## Result
A real six-page static candidate is implemented and runnable locally. See README
for the preview and the evidence report for the actual test boundaries. This is
not another design-only handoff.

## Source observations and ownership
Repository: `murillomartinezmichael/Big7ConstructionWebSite`.
Observed upstream main: `c5a26edf4de61eae360e625af25ab6085edacb90`.
Existing design branch: `design/big7-premium-revamp-2026-10` at
`04e4248987dba6165850f7ea713cf8a693624a14`.
A separate `revamp/big7-2026-10-11` branch was found at
`7c3442e486cfd657c0e0926afdff38e48f8cb1d7`. Its visible head adds a publication
workflow; its corresponding inspected run `38166041142` failed and returned no
artifacts. That branch was not edited or represented as a completed redesign.

Direct Git clone was unavailable in this container (DNS failure). Source inspection
used the live GitHub connector for the branch list, instructions, tree, shared JS,
form contract, asset-exclusion rules and workflow. The attached delivery repository
is NOT a clone of upstream. Do not treat its local commit as upstream history.

The connected Desktop Commander device was offline. GitHub discovery in this
session exposed read actions but no create/update/commit/ref actions. No GitHub
write, remote push, merge, CI trigger or intentional deployment occurred.

## Safe staging patch
The patch adds only new files below `scripts/big7-framing-preview/`. The inspected
`.assetsignore` already excludes `scripts/`; the candidate is not intended to be
served from the client domain. Recheck that rule and hosting configuration before
any push—branch naming alone does not prove deployment isolation.

Use an isolated worktree. Inspect current instructions, owner claims and working
state first. Apply with normal Git tooling and hooks, not `--no-verify`:

```sh
git apply --check /path/to/Big7-Framing-First-Implementation.patch
git am /path/to/Big7-Framing-First-Implementation.patch
python scripts/big7-framing-preview/preview.py --open
```

The patch is additive. It should fail rather than overwrite an existing candidate
at those paths. No root page is promoted by applying it. Do not reset, clean or
stash another agent's working tree. Verify a scoped remote destination before
pushing, and distinguish a commit, push, CI result and deployment receipt.

## Before root-page integration
1. Run the existing repository baseline suites and retain failures before changing
   expectations. Review this candidate's actual diffs rather than treating it as
   a byte-identical port of `big7.js` or `theme.js`.
2. Compare root pages/JS/assets against this candidate. Preserve newer useful
   work, established ownership, source tracking and the working form route.
3. Introduce explicit verified-contact/no-phone test modes. The inspected upstream
   phone is a placeholder; this candidate deliberately omits `tel:` and schema
   telephone. Do not restore a fake number just to satisfy old tests.
4. Update tests deliberately for the approved wording, field labels, no-phone
   state, retained clean paths, metadata, illustrative assets and theme tokens.
   Preserve the protections; do not remove tests to make a release pass.
5. Review existing theme preference storage and external assistant-widget behavior
   during integration. The preview uses a `big7-theme` preference and intentionally
   does not load the external widget or tracking tags. Do not silently disable a
   useful production integration when promoting root files.
6. Verify the existing primary lead recipient and optional automation mirror with
   owner-authorized synthetic delivery. Offline receipt tests do not prove a real
   inbox or webhook. Do not send visitor data or test leads without approval.
7. Only after these gates: remove `data-preview`, replace preview form actions with
   the verified existing `data-live-action`, remove preview-only UI/attributes,
   restore the production robots policy, and remove page-level noindex for approved
   indexable pages. The legacy project page must stay noindex until real project
   facts are verified. Reconcile sitemap/structured data accordingly.
8. Run all repository golden/mutation tests, preflight, real browser navigation,
   both retained theme modes, external font loading and before/after performance.
   Run the actual nginx-container route/security smoke and verify Cloudflare route
   behavior. These gates were not completed by the in-memory preview tests.
9. Content/asset approval and a known-safe release destination precede a live cutover.

## Files intended for eventual scoped integration
Six root HTML files; `big7.js`; `theme.js`; qualified image derivatives and social
card. Existing security headers, deployment configuration, exclusion rules,
phone configuration and production workflows were not replaced in this package.
The page generator is developer tooling, not a mandatory hosting build step.

## Remaining factual / release gates
- Approved public phone number (or an approved permanent email/form-only mode).
- Confirmed real lead-receiving path and external-widget disposition.
- Authentic, client-approved portfolio material; higher-resolution final art where
  appropriate. No illustration is proof of completed client work.
- Full original repository regression, real navigation/performance and deployment
  verification. No traffic or conversion lift has been claimed.

## Rollback
For the staging patch, review current history and revert only its commit. Do not
reset the repository or remove unrelated newer work. For a future live root-page
integration, retain its own pre-release baseline and perform a scoped revert or
verified host rollback after checking current HEAD. Nothing was deployed here,
so no production rollback was necessary.

## Next action
Open the implemented preview, then integrate the tested candidate in an owner-
claimed worktree and run the original repository gates before any live cutover.
