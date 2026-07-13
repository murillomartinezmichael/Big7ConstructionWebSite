PROJECT: Big7Construction
GOAL:    Extend tests/test_og_twitter.py to lock the four social-preview tags every page already carries but nothing tests: og:site_name, og:locale, og:image:alt, twitter:image:alt. All 6 top-level pages must (a) carry them, (b) agree on brand-level values (site_name/locale identical across pages, image:alt identical across pages), (c) og:image:alt must equal twitter:image:alt on the same page (LAW #11 — screen readers on social previews). Add selftest mutations for missing tag, per-page mismatch, and cross-page brand drift. `make test-og` PASS + full `make test` PASS. Commit locally, no push. Log to Cockpit.
BUDGET:  25 min (auto-improve tick 20/9999)
STARTED: 2026-07-12
