# Health Hydration/Stimulation Sections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Relabel Health.html's existing "Water Tracker" section to "Hydration" and add a matching new "Stimulation" section that embeds `caffeine.html` via iframe, using the same pattern already proven for water.

**Architecture:** Pure HTML/CSS addition to `health.html`. No build step, no test framework, no backend — this is a static, client-rendered dashboard where each page is a standalone `.html` file opened directly in the browser (see `index.html`, `health.html`, `po-water.html`, `caffeine.html` for the established pattern). Verification is manual: open the file in a browser and visually/functionally confirm behavior, mirroring how the existing water embed was presumably verified.

**Tech Stack:** Plain HTML, CSS, vanilla JS. No npm test runner, no Jest/pytest — `package.json` only lists `@supabase/supabase-js` as a runtime dependency, there is no test script.

## Global Constraints

- Do not modify `po-water.html` or `caffeine.html` — both stay as-is, untouched, continuing to own their own data (`po_water_v1` in localStorage for water; caffeine.html manages its own keys independently).
- No new shared state between `health.html` and the two embedded pages — iframes are fully self-contained, exactly like the existing water embed.
- Match existing code style in `health.html` exactly (2-space indent, no semicolons-only-where-already-used, existing class naming convention `.water-embed`/`.water-iframe` → mirror as `.caffeine-embed`/`.caffeine-iframe`).

---

### Task 1: Rename "Water Tracker" to "Hydration" and add the "Stimulation" section

**Files:**
- Modify: `health.html:124-138` (CSS block for `.water-embed`/`.water-iframe`)
- Modify: `health.html:933-936` (HTML for the water section)

**Interfaces:**
- Consumes: nothing (no dependency on other tasks — this is the only task in this plan)
- Produces: nothing consumed elsewhere in this plan; phase 3 (hub redesign, separate future plan) will stop linking to `po-water.html`/`caffeine.html` directly from `index.html`, relying on these sections existing inside `health.html` instead

- [ ] **Step 1: Add the `.caffeine-embed`/`.caffeine-iframe` CSS, mirroring the existing water CSS**

In `health.html`, find this block (currently at lines 124-138):

```css
.water-embed { margin-top: 56px; }
.water-iframe {
  display: block;
  width: 100%;
  height: 880px;
  border: 0;
  background: transparent;
  border-radius: 16px;
  overflow: hidden;
  color-scheme: dark;
}
@media (max-width: 480px) {
  .water-embed { margin-top: 40px; }
  .water-iframe { height: 780px; }
}
```

Replace it with (adds the new `.caffeine-embed`/`.caffeine-iframe` rules immediately after the existing water rules, keeping the same structure):

```css
.water-embed { margin-top: 56px; }
.water-iframe {
  display: block;
  width: 100%;
  height: 880px;
  border: 0;
  background: transparent;
  border-radius: 16px;
  overflow: hidden;
  color-scheme: dark;
}
@media (max-width: 480px) {
  .water-embed { margin-top: 40px; }
  .water-iframe { height: 780px; }
}

.caffeine-embed { margin-top: 56px; }
.caffeine-iframe {
  display: block;
  width: 100%;
  height: 880px;
  border: 0;
  background: transparent;
  border-radius: 16px;
  overflow: hidden;
  color-scheme: dark;
}
@media (max-width: 480px) {
  .caffeine-embed { margin-top: 40px; }
  .caffeine-iframe { height: 780px; }
}
```

- [ ] **Step 2: Relabel the water section to "Hydration" and add the new "Stimulation" section**

In `health.html`, find this block (currently at lines 933-936):

```html
  <section id="water" class="water-embed">
    <div class="section-title">Water Tracker</div>
    <iframe src="po-water.html" class="water-iframe" loading="lazy" title="Water Tracker"></iframe>
  </section>
```

Replace it with:

```html
  <section id="water" class="water-embed">
    <div class="section-title">Hydration</div>
    <iframe src="po-water.html" class="water-iframe" loading="lazy" title="Water Tracker"></iframe>
  </section>

  <section id="stimulation" class="caffeine-embed">
    <div class="section-title">Stimulation</div>
    <iframe src="caffeine.html" class="caffeine-iframe" loading="lazy" title="Caffeine Tracker"></iframe>
  </section>
```

- [ ] **Step 3: Verify the file is well-formed**

Run: `grep -c "<section" health.html && grep -c "</section>" health.html`
Expected: both counts equal, and at least one higher than before the edit (one new `<section>`/`</section>` pair added). Confirm by also running `python3 -c "import re,sys; s=open('health.html').read(); print(s.count('<section'), s.count('</section>'))"` if grep counts seem off due to multi-line tags.

- [ ] **Step 4: Manually verify in a browser**

Run: `python3 -m http.server 8000` from the repo root, then open `http://localhost:8000/health.html`.

Expected, in order down the page:
- A section titled **"Hydration"** renders where "Water Tracker" used to be, showing the water coach UI (date, bottle/glass logging) inside the iframe exactly as before.
- Immediately below it, a new section titled **"Stimulation"** renders, showing the Caffeine page's own UI (its own "Caffeine" heading, intake logging) inside the iframe.
- Resize the browser to ≤480px width (or use devtools device toolbar) and confirm both iframes shrink to 780px height and the top margin on each section reduces to 40px.
- Log a water entry and a caffeine entry through their respective embedded UIs, reload the page, and confirm both persisted (each iframe keeps its own state independently — this is just confirming the iframe embed didn't break the underlying pages' existing localStorage behavior).

- [ ] **Step 5: Commit**

```bash
git add health.html
git commit -m "$(cat <<'EOF'
Add Stimulation section to Health page, relabel Water Tracker to Hydration

Phase 1 of the dashboard redesign: surfaces caffeine tracking from
within Health via the same iframe-embed pattern already used for water.
EOF
)"
```
