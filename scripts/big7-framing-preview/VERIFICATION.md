# Implementation verification

Final candidate source hashes and every browser case are in
`evidence/verification-summary.json`.

| Check | Observed result |
|---|---|
| Python candidate contracts + local preview HTTP | 28 passed, 0 failed; includes 10 deliberately broken mutations |
| Node attribution / URL-prefill tests | 12 passed, 0 failed |
| Browser layouts | 48 passed: 6 pages × 4 widths × 2 themes |
| Browser interactions and synthetic delivery | 25 passed, 0 failed |
| Selected rendered text/background comparisons | 24 passed; this is not a full accessibility certification |

Viewport widths: 320, 390, 768 and 1440 CSS pixels. Captured screenshots are actual
Chromium renders of the candidate source, not the AI-generated concept mockups.
Browser navigation was blocked by the execution environment, so the test adapter
loads HTML in memory, embeds the actual local image bytes, and runs the candidate
JS. Google Fonts did not load; screenshots use the declared fallback font stack.
The browser fixture eagerly decodes below-fold images for full-page screenshots;
separate source contracts verify the real lazy-loading attributes.

Synthetic delivery cases: confirmed receipt, optional mirror failure, 400, 500,
HTML response, JSON error, array/null/missing/invalid receipt, malformed JSON,
network failure, redirect rejection, timeout, duplicate/re-entrant submit, invalid
required fields, preview-disabled delivery and honeypot rejection. Errors retain
inputs and explain uncertain receipt. Confirmed-receipt analytics are distinct
from submit attempts; tested telemetry does not contain entered contact fields.

Menu open/close, Escape/focus return, theme toggle with storage unavailable,
keyboard FAQ, reduced motion, no-JavaScript content/navigation, service prefill
and preserving typed details were exercised. Effective 200% viewport reflow was
checked; that does not claim a real browser zoom action or screen-reader audit.

The local-only Python preview server independently passed clean-path, redirect,
query/anchor, 404, path-boundary, security-header and disabled native-POST tests.
These tests do not certify Cloudflare or nginx routing. No real inquiry was sent.

Original upstream Makefile/CI/pre-commit/container suites: NOT RUN here.
Lighthouse and real deployed behavior: NOT RUN. No traffic uplift is claimed.
Unbounded early harness runs exceeded the execution limit; they were rerun in
bounded partitions and deduplicated. Initial logs remain under `evidence/history`.

Commands and environment versions are recorded in the evidence files. All public
preview files remain noindex and delivery-disabled pending integration review.
