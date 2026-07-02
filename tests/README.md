# Tests — Big7Construction

Static site. Test surface is intentionally minimal:

- **HTML validation** — run `npx html-validate **/*.html` before deploy
- **Link check** — `npx broken-link-checker http://localhost:8080`
- **Lighthouse** — Chrome DevTools → Lighthouse → Mobile + Desktop run; aim ≥90 perf / ≥95 a11y

No automated CI tests yet — add Playwright smoke if interactive forms are added.
