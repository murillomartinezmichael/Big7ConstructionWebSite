PROJECT: Big7Construction
GOAL:    nginx (Railway fallback) 301s every shipped page's `.html` form to the same clean path Cloudflare does, proven by a real container probe (`.html` -> 301, clean path -> 200, `/` -> 200 with no redirect loop) and locked by a rewritten test_url_shape contract 6 that derives ONE expected redirect map and asserts BOTH stacks satisfy it.
BUDGET:  90 min
STARTED: 2026-08-12
