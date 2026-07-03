# Big7Construction — Runbook

**Last updated:** 2026-07-03
**Owner:** Michael Martinez (murillomartinezmichael@gmail.com)
**Client:** Big 7 Construction — multi-7 contractor, home construction + home repair, Metro Atlanta.
**Project shape:** static single-file HTML5 marketing site. No JS framework, no build step, no server-side logic.

---

## Quick reference

| Task | Command |
|---|---|
| Run locally | `python -m http.server 8080` (from repo root) |
| Build Docker image | `docker build -t big7:local .` |
| Run container | `docker run --rm -p 8080:8080 -e PORT=8080 big7:local` |
| Deploy | `git push origin main` — Railway auto-deploys from the Dockerfile |
| Tail prod logs | `railway logs` |
| Smoke test prod | `curl -I <PROD_URL>` → expect `HTTP/2 200` |
| Open live site | `<PROD_URL>` — set in `STATUS.md` |

`<PROD_URL>` is tracked in `STATUS.md § 🟢 LIVE right now` (currently `null` — fill in when Railway assigns the public domain).

---

## 1. Local development

The whole site is `index.html` plus `images/` plus a `Dockerfile` and `nginx.conf`. Any HTTP server works locally.

```bash
cd Big7Construction
python -m http.server 8080
# open http://localhost:8080
```

There is **no build step, no JavaScript**. Edit `index.html`, refresh, done.

---

## 2. Environment variables

**None from the site itself.** Railway injects `PORT` at container start; the Dockerfile substitutes it into `nginx.conf` via `sed`:

```dockerfile
CMD sed -i "s/NGINX_PORT/${PORT:-8080}/g" /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'
```

If you're testing the container locally without a `PORT` env var, `nginx.conf` will fall back to `8080`.

---

## 3. Docker

```bash
docker build -t big7:local .
docker run --rm -p 8080:8080 big7:local
# open http://localhost:8080
```

Base image: `nginx:alpine`. Total image size is small — a few hundred KB of HTML + images.

---

## 4. Deploy

Push to `main` triggers Railway auto-deploy. Typically ~90 seconds to live.

```bash
git add index.html images/
git commit -m "content: <what changed>"
git push origin main
```

**Post-deploy smoke test (mandatory per `docs/DEPLOY_STANDARDS.md § 5`):**

```bash
curl -sS -o /dev/null -w "%{http_code}\n" <PROD_URL>
# expect 200
curl -sS <PROD_URL> | grep -c 'Big 7'
# expect ≥ 1 — confirms brand text made it into the served HTML
```

---

## 5. Rollback

Static site, no state — rollback is always safe. Per `docs/DEPLOY_STANDARDS.md § 6`:

```bash
git revert <bad-sha>
git push origin main
# Railway redeploys in ~90s
```

---

## 6. Debug

### 6.1 Locally

- Open browser DevTools. There is no JS to break, so most bugs are CSS or HTML structure.
- Missing image? Check the `images/` folder is intact and paths in `index.html` match.

### 6.2 Prod logs

```bash
railway logs
```

nginx access lines print to stdout. `502` from Railway means the container isn't binding to `$PORT` — check the `sed` step in the Dockerfile ran.

### 6.3 Common failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| 502 on prod URL | nginx not binding to `$PORT` | Rebuild + check the `sed` line in Dockerfile substituted `NGINX_PORT` correctly |
| Images missing on prod but present locally | New image not added to git | `git status`, `git add images/<file>`, commit, push |
| Fonts fail to load | Google Fonts blocked / typo in URL | Verify `<link>` tags at top of `<head>` |
| Layout breaks on mobile | Broken CSS media query | Bisect back to the last working commit |

---

## 7. Content editing rules

- **No JavaScript.** Pure HTML + CSS. If a feature needs JS, that's a scope conversation, not a quick edit.
- **All styles in the `<style>` block inside `index.html`.** No external CSS.
- **Images go in `images/`** and are copied into the Docker image.
- **Fonts:** Anton (display headings) + Barlow (body), both from Google Fonts.
- **Palette:** warm off-white, orange-red, electric blue.
- **Nav brand link** (`.brand`) points at `#hero` — matches the "01 Home" nav entry. If you rename the hero section id, update both.

---

## 8. Secrets

**None.** Fully static site.

Global rotation cadence per `docs/SECURITY_STANDARDS.md` doesn't apply — no secrets to rotate.

---

## 9. Useful one-liners

```bash
# Sanity check the Dockerfile port substitution before pushing
grep -E "NGINX_PORT|sed.*PORT" Dockerfile nginx.conf

# Count images referenced vs images on disk (should match)
grep -oE 'images/[^"'"'"']+' index.html | sort -u | wc -l
ls images/ | wc -l
```

---

## Cross-refs

- **Where Big7 fits in the tree:** `../PROJECT_GLOSSARY.md`
- **Live URL manifest:** `../STATUS.md § 🟢 LIVE right now`
- **CTA + intake standard:** `../docs/CONVERSION_STANDARDS.md`
- **Deploy standard:** `../docs/DEPLOY_STANDARDS.md`
- **Hosting choice rationale:** `../docs/HOSTING_STANDARDS.md` + `../docs/DECISIONS.md § D-001` (Railway default)
