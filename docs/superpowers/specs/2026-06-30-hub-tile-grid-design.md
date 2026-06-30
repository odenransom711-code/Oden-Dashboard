# Hub tile grid cleanup (index.html)

## Context

This is phase 3a of the dashboard redesign, which itself splits into two sub-projects:
- **This spec (3a)** — clean up the hub's tile grid: drop Water/Caffeine tiles, add a School tile, make all tiles uniform size.
- **3b** (separate spec, after this one) — add a Calendar block to the hub (month grid + agenda, manual event entry).

Earlier phases: [1] Hydration/Stimulation folded into Health.html, [2] School.html built. This spec assumes both are done — Water/Caffeine tracking already lives inside Health, and `school.html` already exists as a real page.

## Problem

`index.html`'s bento grid (index.html:62-138) currently has 7 tiles in mixed sizes (`big`/`wide`/default) on a 4-column desktop grid: Main, Fitness, Health, Water, Finance, Caffeine, Nova. Two of these (Water, Caffeine) are now redundant — that functionality moved into Health in phase 1 — and there's no tile yet for the new School page from phase 2. The mixed tile sizing was also never something the user asked for; they explicitly want uniform tiles.

## Design

Edit `index.html`'s `<div class="bento">` (index.html:222-322) and its supporting CSS (index.html:62-138):

**Tiles, in order:**
1. Main 🏠 `#6BE3A4` → `main.html` (unchanged)
2. Fitness 💪 `#7DD3FC` → `gym.html` (unchanged)
3. Health 💊 `#A7F3D0` → `health.html` (unchanged)
4. Finance 📊 `#F2C063` → `finance.html` (unchanged)
5. Nova 🧠 `#A78BFA` → `nova-lite.html` (unchanged)
6. School 🎓 `#F472B6` → `school.html` (new)

Water and Caffeine tiles are deleted outright (not just unlinked — their markup is removed from `index.html`).

**Sizing:** every tile becomes a plain `.tile` — remove the `big`/`wide` class from all `<a class="tile ...">` elements. In the CSS, delete the `.tile.big`/`.tile.wide` rules (index.html:99-100), the `.tile.big .tile-title` font-size override (index.html:117), and the size-variant overrides inside both responsive breakpoints (index.html:131-132, 137).

**Grid columns:** change `.bento`'s desktop `grid-template-columns` from `repeat(4, 1fr)` to `repeat(3, 1fr)` (index.html:65) — 6 uniform tiles exactly fill a 3×2 grid with no leftover cells, instead of the awkward 4-wide layout leaving a half-empty row. The existing tablet (`repeat(2, 1fr)`, index.html:130) and mobile (`1fr`, index.html:136) breakpoints are unchanged — they already collapse correctly for any tile count since `grid-auto-flow: dense` (index.html:67) just wraps uniform tiles in order.

**`tile-num` labels** (the "·01" through "·07" eyebrow text on each tile, e.g. index.html:227) get renumbered ·01 through ·06 to match the new 6-tile order.

## Data flow / error handling / testing

No data model changes — this is pure markup/CSS restructuring of a static page, no JS logic touched. No automated test framework exists in this repo (confirmed in phase 1). Verification is manual: open `index.html` in a browser, confirm exactly 6 tiles render (Main, Fitness, Health, Finance, Nova, School), all the same size, arranged 3 per row on desktop width, confirm each tile links to the correct page, confirm the responsive breakpoints (2-column tablet, 1-column mobile) still look correct, and confirm Water/Caffeine no longer appear anywhere on the hub.
