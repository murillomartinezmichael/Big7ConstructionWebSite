# Big7Construction — Onboarding

**For:** a contributor (or future-Michael) getting productive in a day.
**Time to first shipped edit:** ~20 minutes.

---

## Day 1 — get it running and understand the shape

**Checklist:**

- [ ] Clone the repo. `cd Big7Construction`.
- [ ] `python -m http.server 8080` → open `http://localhost:8080`.
- [ ] Read `index.html` in a text editor. **One file, no JavaScript.** HTML + a `<style>` block. That's it.
- [ ] Skim `RUNBOOK.md` for deploy shape (Railway + nginx:alpine + `sed` port injection).
- [ ] Look at `images/` — every photo referenced from HTML lives here.

**By end of day 1 you can:** change copy, swap an image, run locally, ship to prod (`git push origin main` → Railway ~90s).

---

## Day 2 — nav + brand + palette

- [ ] Nav links (`<nav class="top">`) each anchor a section by id. Brand anchor points at `#hero`.
- [ ] Palette: warm off-white, orange-red, electric blue — defined near top of `<style>`.
- [ ] Fonts: Anton (display) + Barlow (body) via Google Fonts `<link>` at top of `<head>`.
- [ ] Try changing a section headline; refresh the browser.

**By end of day 2 you can:** add a new section, wire it into the nav, ship it.

---

## Day 3 — deploy safely

- [ ] Read `RUNBOOK.md § 4 Deploy` end-to-end.
- [ ] After any push, run the smoke test from RUNBOOK § 4.
- [ ] If a deploy 502s: check the `sed` line in the Dockerfile substituted `NGINX_PORT` — that's the failure mode 90% of the time.

---

## Anti-patterns for a new contributor

1. Adding JavaScript. This is HTML + CSS. If a feature needs JS, that's a scope call, not an edit.
2. Externalizing CSS. Styles live inside the `<style>` block in `index.html`.
3. Referencing images by absolute path. `images/<file>` is the convention — the folder is copied into the Docker image.
4. Using `href="#"` for dead anchors. Every clickable anchor points somewhere real.

---

## Where to look next

- `RUNBOOK.md` — run, deploy, debug, rollback.
- `../docs/CONVERSION_STANDARDS.md` — CTA + intake rules.
- `../docs/HOSTING_STANDARDS.md` — why Railway free-tier fits this shape.
