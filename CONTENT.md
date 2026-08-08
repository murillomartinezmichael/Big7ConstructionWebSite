# Big7Construction — Content moments worth filming

Rolling list of before/after moments and process shots that would land on TikTok. Per root CLAUDE.md LAW #8, no auto-publishing, no TTS — this is a draft queue only.

## 2026-07-05 chunk 1 (schema.org)

### Filmable
- **Schema.org before/after in a SERP simulator.** Show the old JSON-LD block (empty `itemListElement: []`) side-by-side with the new one (7 populated services + 12 cities). Paste both into Google's Rich Results Test — the new block gets a "Local Business" rich card, the old one gets nothing. **Frame:** "30 lines of JSON = one Google rich card = free local search traffic."
- **Portfolio grid client-editable marker.** Screen record: open `index.html`, scroll to line 1997, show the copy-paste comment block, then paste-and-edit a fake new project card in 40 seconds. **Frame:** "no CMS. no build step. non-technical client edits 4 fields, refreshes, ships."
- **8× gzip headroom.** Terminal shot: `wc -c` shows 125 KB, `gzip -c | wc -c` shows 24 KB, cut to the 200 KB Lighthouse gate. **Frame:** "the whole website is smaller than one Instagram thumbnail."

## 2026-07-05 chunk 2 (Lighthouse RUNG 4)

### Filmable
- **Google Fonts render-block, isolated.** Terminal shot of the `render-blocking-insight` audit — before line shows `wastedMs: 786` and score 0, after line shows score 1 (PASS). Cut to the ~5-line HTML diff (Filament Group async-load pattern) that removed it. **Frame:** "one HTML edit, 800 ms shaved off first paint. Font loading is the single most-mis-configured thing on the web."
- **The 206×206 hero image reveal.** Split-screen: the hero on the live site (looks fine at hero size) next to opening the actual file in an image viewer at 100% — pixel-tiny 206×206 speck. **Frame:** "your fancy hero image is a thumbnail wearing makeup. This is why real photos matter." (Client-photo-blocked note: don't publish until real photos land.)

## 2026-07-05 chunk 3 (a11y + 404)

### Filmable
- **The DL semantic reveal, screen-reader edition.** Screen record with macOS VoiceOver (or NVDA) walking the hero stats: before the fix, VoiceOver says "empty definition list, empty definition list…" because the DTs and DDs were nested in divs; after, "Projects delivered, 500 plus. Trades in-house, 8. Coverage, 100 percent…" — perfect. **Frame:** "a blind visitor. Before: silence. After: your whole pitch. And it took deleting four divs."
- **404 that isn't the home page.** Split-screen: paste a fake URL like `/services/framing/does-not-exist` into two browsers. Left: an old build silently reloads the home page and pretends everything's fine. Right: the new build shows a real 404 with a big "back to Big 7" button. **Frame:** "if your broken links secretly serve your home page, Google is duplicate-content-penalizing you and you don't know it. This is a two-line nginx fix."
- **`.btn-accent` accessibility fix in the browser dev tools.** Open Chrome dev-tools contrast checker, hover the CTA — old build shows 3.48 (fail), new build shows 5.05 (pass). Voice-over: "This was making my CTA invisible to about 8 percent of visitors. One hex code change. My conversion just got better and I didn't touch the layout." **Frame:** "the a11y fix that pays for itself in extra clicks."

## Waiting-for
- Real jobsite photos (2000+ px) — the site actually reads like a portfolio not a template only after these arrive.
- Client testimonial + head-shot — the trust section is currently editorial framing with no faces.
- Real live URL — Perf Lighthouse against Railway prod, not local emulator, is the honest re-measurement.

## 2026-07-17 font-swap CLS fix

### Filmable
- **"Watch the page jump — now watch it not."** Side-by-side slow-mo screen recording: hero headline rewrapping when the fancy font loads (CLS 0.235, fails Google's bar) vs. the fixed version staying rock-still. Overlay the CLS numbers dropping 0.235 → 0.06. **Frame:** "Your website jumps when the font loads. Google penalizes that. Here's the 40-line CSS fix nobody does — no font files, no build step, just math." Nerd-bait hook: the fix required knowing Fraunces is an optical-size variable font whose display cut is 19% narrower than its text cut.
