PROJECT: Big7Construction
GOAL:    Extend tests/test_og_twitter.py so it locks each real top-level page's <link rel="canonical" href="..."> against its og:url. The 404 gets a documented exception (og:url points at homepage per Google's "404s should not carry a canonical to themselves" guidance; test asserts 404.html has NO canonical link at all). Add selftest mutations covering canonical missing, canonical/og:url mismatch, and 404 accidentally sprouting a canonical. `make test-og` PASS + full 15-target `make test` PASS. Commit locally, no push. Log to Cockpit.
BUDGET:  25 min (auto-improve tick 19/9999)
STARTED: 2026-07-12 (dynamic)
