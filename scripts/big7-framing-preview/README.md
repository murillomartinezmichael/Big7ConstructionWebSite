# Big 7 Construction — implemented framing-first candidate

A working six-page static redesign, not a design document or a deployed website.
Commercial wood framing and drywall lead. Home repairs stay visible. The brand
name is retained and the headline is **Built right. From the frame up.**

## Open the website

Windows: double-click `START-WINDOWS.bat` with Python 3 installed.

Windows, Linux or macOS:

```sh
python preview.py --open
```

The server binds only to `127.0.0.1:8767`; stop it with Ctrl+C. No package installation
is required to view the preview. The actual static pages are in `site/`.
Use this server rather than double-clicking an HTML file: the site intentionally
preserves clean, root-relative production URLs.

**Preview submissions are disabled**, with and without JavaScript. Preview files
are marked noindex. No real lead, mailbox test, advertising or publication was
performed. Existing production pages and workflows were not modified.

## Implemented

- Homepage, commercial framing/drywall page, residential/home repair page,
  accessibility page, genuine-404 design, and a conservative legacy-project page.
- Consistent inline CSS; responsive layouts; two themes; keyboard mobile menu;
  reduced motion; service selection; labelled, optimized illustrative imagery.
- Adapted existing intake interface and receipt validation: retained endpoint
  identity, field names, duplicate-send protection, optional automation mirror,
  timeout, ambiguous-receipt wording and attribution contracts. Added a distinct
  confirmed-receipt event and removed invented response deadlines and the fake
  phone from the candidate.
- First-pass copy using Michael's latest requirements. “30+ years” describes
  industry experience, not the company's age. No fabricated project statistics,
  customer quotes, trade credentials or completion guarantees.

## What is deliberately not claimed

The candidate is not integrated into the root of the GitHub repository, pushed,
CI-certified, deployed, or proven against real Formspree/n8n delivery. The existing
repository's entire Makefile/pre-commit/container suite was not available locally
and was not run. New candidate tests are identified separately.

Browser tests use **in-memory Chromium rendering**, because this execution
container blocks browser HTTP and file navigation. Markup, inline CSS and actual
candidate JS run in Chromium; local image bytes are embedded by the test fixture
and fetch responses are synthetic. Screenshots use fallback fonts, not downloaded
Google Fonts. Layout results are not a live routing or Lighthouse test.

## Source layout

`site/`: usable six-page preview and JS/assets.
`src/design.css`: authoring source; emitted inline in each HTML page.
`src/build_preview.py`: deterministic developer-only generator; not a runtime
framework, server dependency or mandatory hosting build step.
`tests/`: contract, browser, contrast and attribution checks.
`evidence/`: exact commands/results, screenshots, provenance and size observations.
`HANDOFF.md`: integration and release boundaries.

Rebuild: `python src/build_preview.py`. The generator only emits previews and
cannot enable delivery or publish. JavaScript and images are maintained in `site/`.

## Verify

Test-tool versions are pinned in `requirements-test.txt`. Viewing the preview
needs only Python's standard library; test tools are separate optional developer
dependencies. Use a virtual environment for test dependencies, never system pip.

```sh
python tests/test_contracts.py
node --test tests/attribution.test.cjs
python tests/test_browser.py --mode layout
python tests/test_browser.py --mode functions
python tests/test_contrast.py
```

Browser scripts currently default to `/usr/bin/chromium`, the actual tested
container executable. For a different machine, change that test-only executable
path to its installed Chromium/Chrome path. No browser download is initiated.
The browser test supports `--start` / `--stop` for bounded partitions; the delivered
result summary deduplicates those partitions rather than counting retries twice.

## Imagery

Three WebP crops were extracted from an AI-generated concept image. They are
labelled as illustrations, never represented as completed Big 7 jobs or employees.
Exact crop coordinates, pixel dimensions and hashes are in the asset manifest.
These are review assets, not high-resolution client portfolio photography. Replace
or upgrade them only with equally well-labelled generated art or approved real
photos. The social card is a rendered typography asset, not a project image.

## Source control / release

The accompanying patch stages this implementation under
`scripts/big7-framing-preview/`, an already excluded tooling directory in the
inspected upstream configuration. It does not replace root pages, change hosting
rules, or create a workflow. A local delivery commit is not an upstream commit.
See `HANDOFF.md` before applying or promoting any files.
