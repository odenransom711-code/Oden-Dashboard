# Health page: Hydration + Stimulation sections

## Context

This is phase 1 of a 3-phase dashboard redesign:
1. **This spec** — fold Water and Caffeine into Health.html as "Hydration" and "Stimulation" sections
2. Build a new School.html page (assignments/deadlines, classes/schedule, grades/GPA, exam countdown)
3. Redesign the hub (index.html): uniform-size nav tiles, a built-in Calendar block (month grid + agenda) featured prominently up top, snapshot/graph cards filling remaining grid space, and removal of the standalone Water/Caffeine hub tiles (superseded by phase 1)

Phases 2 and 3 are out of scope for this spec and will each get their own design doc.

## Problem

The hub (index.html) currently has separate tiles linking to `po-water.html` and `caffeine.html`. The plan is to remove those tiles in phase 3 and instead surface hydration and stimulation tracking from within the Health page. Health.html (health.html:933-936) already embeds `po-water.html` via an iframe under a "Water Tracker" heading — so this merge is mostly already done for water; caffeine needs the same treatment.

## Design

No new mechanism is needed — extend the existing iframe-embed pattern that Water already uses, rather than inlining the ~250KB of combined HTML/CSS/JS from both standalone pages (which would risk ID/style collisions for no real benefit, since the iframe approach is already proven in production).

Changes to `health.html`:

1. Rename the existing `<div class="section-title">Water Tracker</div>` (health.html:934) to `<div class="section-title">Hydration</div>`. The iframe itself (`src="po-water.html"`, class `water-iframe`) is unchanged.
2. Add a new sibling `<section>` immediately after the hydration section:
   ```html
   <section id="stimulation" class="caffeine-embed">
     <div class="section-title">Stimulation</div>
     <iframe src="caffeine.html" class="caffeine-iframe" loading="lazy" title="Caffeine Tracker"></iframe>
   </section>
   ```
3. Add matching CSS, mirroring `.water-embed`/`.water-iframe` (health.html:124-137):
   ```css
   .caffeine-embed { margin-top: 56px; }
   .caffeine-iframe {
     display: block; width: 100%; height: 880px; border: 0;
     background: transparent; border-radius: 16px; overflow: hidden;
     color-scheme: dark;
   }
   @media (max-width: 480px) {
     .caffeine-embed { margin-top: 40px; }
     .caffeine-iframe { height: 780px; }
   }
   ```

`po-water.html` and `caffeine.html` remain as real, unmodified files — they continue to be the actual implementation, just reached via iframe instead of (eventually) a direct hub tile.

## Data flow

Unchanged. Each iframe is fully self-contained: `po-water.html` reads/writes `po_water_v1` in localStorage, `caffeine.html` manages its own keys, independent of the parent `health.html` page. No new shared state.

## Error handling

None needed beyond what already exists — `loading="lazy"` on the iframe is the only relevant behavior, identical to the current water embed.

## Testing

Manual verification: open health.html, confirm "Hydration" section renders the water tracker (existing behavior, just relabeled), confirm new "Stimulation" section renders the caffeine tracker with working logging, confirm responsive height behaves correctly at mobile width (≤480px).
