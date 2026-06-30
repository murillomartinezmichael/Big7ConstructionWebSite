> **STATUS: DRAFT** — this doc is a structured outline of what needs to be answered. Sections without content are TODO for the owner. Fill in over time; do not delete until replaced with real content.

---

<!--
  WHY THIS DOC EXISTS
  -------------------
  ONBOARDING.md takes a person who knows NOTHING about this project and
  walks them to "I can confidently make a meaningful contribution."

  README.md  = "what is this and how do I run it"
  RUNBOOK.md = "how do I operate this in every environment"
  ONBOARDING.md = "teach me to actually work in this codebase"

  Audience: a competent engineer who has never seen this codebase, this
  domain, or possibly this stack. They have the basics of programming.
  They do NOT have your context.

  Rule of thumb: if the reader has to leave this doc and ask you a question,
  the doc has a gap. Add the answer to the doc.

  Structure: linear days, each with goals + concrete tasks + a "you have
  succeeded when" gate. Not a reference manual.
-->

# Big7Construction — Onboarding

**Audience:** new contributor on day 1.
**Goal:** shipping a real change to main by day 5.
**Time:** ~4 hours per day, ~20 hours total.

If you finish a day early, jump ahead. If you get stuck, the troubleshooting section at the bottom is the first place to look — then ask in {{HELP_CHANNEL}}.

---

## Before day 1 — install these

| Tool | Why | Install |
|---|---|---|
| {{LANG_RUNTIME}} | Project language | {{link}} |
| Docker Desktop | Local DB + integration tests | https://docker.com/products/docker-desktop |
| Git | Source control | {{link}} |
| {{IDE, e.g. VS Code or Rider}} | What we standardize on | {{link}} |
| {{IDE_EXTENSIONS}} | Lint + format on save | {{install steps}} |

Set up:
- [ ] Git identity: `git config --global user.name "..."` / `git config --global user.email "..."`
- [ ] SSH key uploaded to {{GIT_HOST}}
- [ ] Access granted to repo, {{SECRET_STORE}}, {{DEPLOY_PLATFORM}}, {{LOG_PLATFORM}}, {{CHAT}}
- [ ] Joined channels: {{LIST}}

---

## Day 1 — Understand the system, run it locally

### Goals
- Know what the project does and why it exists
- Run it on your machine end-to-end
- Find your way around the folder structure

### Steps

1. **Read these in order**, no skipping:
   - `README.md` — what it is, what stack
   - `BRD.md` — the business problem and who it's for
   - `TRD.md` — the technical shape, architecture diagram, stack-choice rationale
   - `ENGINEERING_STANDARDS.md` (in repo root) — how we write code here

2. **Clone and build:**
   ```bash
   git clone {{REPO_URL}}
   cd {{PROJECT_DIR}}
   ./build.sh        # or build.bat on Windows
   ```
   If `build.sh` fails, do NOT work around it. The script is the contract — fix it (or open an issue and pair with someone). RUNBOOK § 6.3 lists common failure modes.

3. **Run the service:**
   ```bash
   ./scripts/run.sh
   ```
   Open `{{LOCAL_URL}}`. Verify the health check returns 200.

4. **Click through every screen / hit every endpoint** at least once. Make notes of anything confusing.

### You have succeeded today when
- [ ] You can describe the project's purpose in two sentences without looking
- [ ] The service runs locally and the health check returns 200
- [ ] You've used the main features end-to-end

---

## Day 2 — Read the code

### Goals
- Internalize the folder structure
- Trace one request from HTTP entry to DB and back
- Understand the testing approach

### Steps

1. **Skim the folder tree.** For each top-level folder, write yourself one sentence about what lives there. Compare against the structure section in `TRD.md`.

2. **Pick one endpoint.** Trace it top-to-bottom:
   - Route handler — where is it registered?
   - Request DTO — how is input validated?
   - Service method — what business logic runs?
   - Repository method — what query runs against the DB?
   - Response DTO — what gets returned, and shaped how?

   Draw this on paper. Box and arrow. Show it to your mentor.

3. **Read the unit tests for that service method.** Run them:
   ```bash
   ./scripts/test.sh unit
   ```

4. **Read the integration test for the same endpoint.** Run it:
   ```bash
   ./scripts/test.sh integration
   ```

5. **Read the E2E test (if any) that exercises that endpoint.** Run it. Watch the browser open. Look at the screenshots in `tests/e2e/screenshots/`.

### You have succeeded today when
- [ ] You can explain, on a whiteboard, what happens when {{REPRESENTATIVE_REQUEST}} hits the service
- [ ] You've run unit, integration, and E2E tests at least once each

---

## Day 3 — Make a trivial change

### Goals
- Get familiar with the dev loop
- Open your first PR
- Get one round of code review

### Steps

1. **Pick a "good first issue."** Talk to {{MENTOR}} — they'll point you to one already triaged. Examples: a typo in a response message, a missing log line, a small docs update.

2. **Create a branch:**
   ```bash
   git checkout -b fix/<short-name>
   ```

3. **Make the change. Write a test first** if the change is observable from outside the function.

4. **Run the full test suite:**
   ```bash
   ./scripts/test.sh
   ```

5. **Lint + format:**
   ```bash
   ./scripts/lint.sh --fix
   ```

6. **Open a PR:**
   ```bash
   git push -u origin fix/<short-name>
   ```
   Use the PR template (What / Why / How tested / Screenshots). Tag {{MENTOR}}.

7. **Address review comments.** Push more commits to the same branch — don't force-push during review.

### You have succeeded today when
- [ ] A PR is open with green CI
- [ ] You've responded to at least one round of review

---

## Day 4 — Ship something real

### Goals
- Pick up a real ticket
- Write production-quality code
- Get it merged

### Steps

1. **Pick a ticket from {{BACKLOG_LOCATION}}** marked "good for new joiners" or "starter." Confirm with {{MENTOR}}.

2. **Before writing code, write down:**
   - What problem this solves
   - What the user-visible behavior change is
   - Which layer the change goes in (route / service / repo / model)
   - What tests need to exist after

3. **Build it.** Follow `ENGINEERING_STANDARDS.md`:
   - CRUD layering intact
   - Names per the rules
   - Comments only where WHY is non-obvious
   - Tests at the right tier(s)

4. **Run the full test suite + lint.** Open a PR with the same template.

5. **After merge:** verify it works in staging within 30 minutes of CI completing.

### You have succeeded today when
- [ ] A real change is merged to main
- [ ] Staging shows the change working

---

## Day 5 — Understand operations

### Goals
- Know how to deploy
- Know how to debug a prod issue
- Know who to page

### Steps

1. **Read `RUNBOOK.md` end-to-end.** Pay extra attention to:
   - § 5 Deploy
   - § 6 Debug
   - § 7 On-call / incident response

2. **Shadow a deploy.** If one isn't happening, ask {{MENTOR}} to walk you through a dry run.

3. **Open the prod log viewer** and watch live traffic for 5 minutes. Get used to the shape of normal logs so you'll recognize abnormal ones.

4. **Open the prod dashboard / metrics view.** Identify the top 3 alerts and what they mean.

### You have succeeded today when
- [ ] You can perform a deploy unsupervised (with a senior on standby)
- [ ] You can explain what to do if {{COMMON_PROD_SYMPTOM}} happens
- [ ] You know which channel alerts go to and what severity means

---

## The mental model (read after day 2, re-read after day 5)

{{ONE_TO_TWO_PARAGRAPHS describing the system in plain English. What is the core abstraction? What is the data flow? Where does state live? Why was this stack chosen? Use a diagram if it helps. This is the most valuable section of the whole doc — write it carefully.}}

---

## Glossary

| Term | Meaning |
|---|---|
| {{DOMAIN_TERM_1}} | {{plain-English definition}} |
| {{DOMAIN_TERM_2}} | {{plain-English definition}} |
| {{ACRONYM}} | {{expanded + what it means here}} |

---

## Troubleshooting (you'll hit these)

| Symptom | What's actually wrong | Fix |
|---|---|---|
| `build.sh` hangs at "Installing requirements" | Slow network or PyPI mirror unreachable | Retry; check internet; see § 1.1 RUNBOOK |
| Tests fail with "connection refused" on DB | Local DB container not running | `docker compose up -d {{DB_SERVICE}}` |
| "Module not found" after `git pull` | New dependency added | Re-run `./build.sh` |
| Linter complains about formatting | You skipped format-on-save | `./scripts/lint.sh --fix` |
| {{ADD_THE_REAL_ONES_YOU_HIT}} | | |

---

## After onboarding — leveling up

- Read `docs/architecture/` for deeper design notes and ADRs
- Read recent postmortems in `docs/postmortems/` — that's how the codebase actually behaves under stress
- Pair with someone on a complex ticket
- Volunteer for on-call shadowing
- Pick one section of the codebase you don't understand and refactor a small piece of it (with a reviewer)
