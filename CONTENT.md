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

## Waiting-for
- Real jobsite photos (2000+ px) — the site actually reads like a portfolio not a template only after these arrive.
- Client testimonial + head-shot — the trust section is currently editorial framing with no faces.
