# Big7Construction
Marketing website for Big 7 Construction — full-service commercial, industrial, and residential contractor. Static HTML site on Railway.

## Stack
- HTML5 + embedded CSS (no build step, no JS framework)
- Google Fonts: Anton + Barlow
- nginx:alpine → Railway (port 8080)

## Setup
```bash
cd Big7Construction

# Serve locally
python -m http.server 8080
# Open http://localhost:8080
```

## Environment Variables
None — fully static site. Railway injects `PORT` for nginx config.

## Deploy
Railway — push to main triggers Docker build. nginx:alpine serves on `${PORT:-8080}`.

## Status
Live. Single-page site covering commercial, industrial, and residential construction services.
