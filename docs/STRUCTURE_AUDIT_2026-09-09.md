# Structure Audit — Big7Construction — 2026-09-09

MONEY_LADDER rung 3. Audience the surface must convince: a commercial construction
client evaluating Big7, plus the lane-form lead.

## Method (LAW #6 — what was actually measured)

Every number below was counted from the shipped HTML at commit `87a42c2`, not
remembered. `make test` was run before and after the one change made (green both
times, 8 design mutations caught). Nothing was pushed — `DECISIONS.md` 2026-08-25
records that Cloudflare Workers Builds deploys **every branch** on this repo, so an
agent push here is a production deploy to a paying client's domain.

## The headline number was wrong, and the real one is smaller

A generated handoff earlier today reported "215 hardcoded hex literals" for this
repo. That figure is technically true and practically useless. Split properly:

| Category | Count | What it actually is |
|---|---:|---|
| Token **definitions** inside `:root` | 132 | 22 tokens × 6 pages — duplication, not hardcoding |
| Plain white outside `:root` | 77 | `#fff` ×73, `#ffffff` ×4 — one colour, two spellings, no token |
| Hex that duplicates an existing token | 6 | of which **4 are false positives** (below) |
| **Genuinely wrong and fixed** | **2** | `body { background; color }` on index.html |

**The lesson for the next automated pass:** a regex that counts `#rrggbb` cannot
tell a CSS declaration from an HTML attribute or a code comment. Four of the six
"replaceable" hits were not replaceable at all:

- `index.html:8` — `<meta name="theme-color" content="#08090B">`. This is an HTML
  attribute. `var()` does not resolve there; substituting it would have silently
  broken the mobile browser chrome colour.
- `index.html:382–383` — inside a comment that documents measured WCAG contrast
  ratios (`--ink-500 (#4C5258) on --ink-950 (#08090B) sits at ~3.15`). Rewriting
  those to `var()` would have destroyed the documentation and left a comment that
  says nothing.

Blind find-and-replace on this repo would have shipped both defects to a live
client site.

## Findings

### 1. FIXED — the body ignored its own tokens
`index.html` set `background: #F5F1EA; color: #151719` literally, while `:root`
defined `--paper: #F5F1EA` and `--ink-800: #151719` a few lines above. The single
most important colour pair on the page was not governed by the token system that
exists to govern it. Now `var(--paper)` / `var(--ink-800)`. Suite green.

### 2. OPEN — white is the most-used colour on the site and is not a token
77 uses, spelled two ways. There is no `--white` or `--paper-pure`. This matters
more than it looks: the brand already has a deliberate warm paper (`#F5F1EA`,
commented "warm concrete"), and pure `#FFF` sitting next to it 77 times is either
an intentional contrast or unnoticed drift. **That is a brand call, not a cleanup,
so it was not made autonomously.** Decide, then tokenize whichever way you decide.

### 3. OPEN — the token block is duplicated once per page, documented once
All six pages carry an identical 22-token `:root`. The values agree exactly
(verified by hash: five pages are byte-identical, and `index.html` differs **only
in comments** — no value drift). But the explanatory comments — what "ink" means,
why Division 01 is orange and Division 02 blue — exist only in `index.html`. Anyone
editing `404.html` sees 22 undocumented hex values.

This is the strongest argument for a shared stylesheet, and it is also why the site
does not have one: there is no build step, and extracting CSS adds a request on a
Workers-served static site. `tests/test_design_tokens.py` already pins the six
copies together, so the duplication is *guarded* even though it is not *removed*.
Not changed — the guard makes it safe, and changing CSS delivery on a live client
site is a separate, deliberate decision.

### 4. OPEN — page weight is concentrated and unreviewed
`index.html` is 1,752 lines, more than the other five pages combined
(1,145 / 1,123 / 501 / 215 / 153). Everything is inline: fonts, reset, tokens,
components, page sections. Nothing here is broken, but no one can review a diff in
that file with confidence, which is how the body-colour defect survived a commit
literally titled *"require complete design tokens across every page."*

### 5. NOTED — `.pyc` files are tracked
`tests/__pycache__/*.pyc` show as modified in every session. They should be
gitignored. Trivial, unrelated to design, and left alone to keep this diff honest.

## Prioritized next actions

1. **Decide the white question** (finding 2). One sentence from Michael unblocks it.
2. **Copy the token comments into the other five pages**, or add a one-line pointer
   to `index.html` as the documented source. Cheap, removes the worst trap.
3. **Only then** consider a shared stylesheet (finding 3) — and treat it as a
   delivery change with its own verification, not a refactor.

Nothing on this list blocks revenue. Rung 3's actual money gate is still a single
n8n dashboard click: retire the old `big7-lead` trigger in workflow
`NOiAPRC4nYcOdMge`. No amount of CSS moves that.
