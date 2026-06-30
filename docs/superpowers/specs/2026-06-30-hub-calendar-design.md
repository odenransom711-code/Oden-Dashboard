# Hub Calendar (index.html)

## Context

This is phase 3b of the dashboard redesign — the last sub-project in phase 3. Phase 3a (already done) cleaned up the hub's tile grid to 6 uniform tiles (Main, Fitness, Health, Finance, Nova, School). This spec adds the Calendar block the user asked for: "out on the front end of the dashboard," prominent, visible without clicking into any sub-page.

Earlier in this project's brainstorming, two scope decisions were made that bound this spec:
- **Manual entry only.** School's classes have day-of-week schedules and Fitness uses a rotating split tied to an anchor date — auto-expanding either into calendar events is real extra work (recurring-occurrence math, keeping events live-synced to edits in their source page). That's explicitly deferred; this phase is a generic event list you populate by hand.
- **No event categories.** Events are just title + date + optional time — no Workout/Class/Meeting type, no per-type coloring.

## Problem

There's no calendar anywhere on the dashboard. The user wants one glanceable at the top of the hub, showing a month view and an agenda of what's coming up, where they can jot down anything (workouts, meetings, deadlines) without navigating to a sub-page.

## Design

### Placement

A new `<div class="section">` titled "Calendar" inserted into `index.html` between the header row (`.hub-head`, currently ending at index.html:213) and the bento tile grid (currently starting at index.html:215). It renders above the nav tiles, full width within `.page`.

### Data model

One new localStorage key, `calendar_v1`:

```js
{ events: [ { id: "evt_xxx", date: "2026-07-04", title: "Dentist", time: "14:30" } ] }
```

`time` is optional — an empty string when not set. Synced via `window.initCloudSync({ appKey: 'calendar', syncedKeys: ['calendar_v1'], onApplied: render })`, registered inside a `document.addEventListener('DOMContentLoaded', ...)` wrapper — the School page build surfaced a real bug where registering `initCloudSync` in a non-deferred inline script (the established per-page pattern in `template.html`) runs before the deferred `sync.js` has loaded, so the call silently never fires. This spec avoids that bug from the start.

### Month grid

A 7-column grid, one row per week, for the currently-viewed month (in-memory `viewYear`/`viewMonth` state — not persisted; always opens to the real current month on page load). A header row above it shows day-of-week initials (Sun–Sat) and a "‹ July 2026 ›" label with prev/next buttons that shift `viewMonth`/`viewYear` and re-render.

Each day cell shows its date number. A day with one or more events gets a small dot below the number (a single dot regardless of how many events — no per-type coloring, since events carry no category). Today's cell gets a distinct border/background treatment so it's identifiable at a glance.

### Expand-in-place interaction

CSS Grid cells can't resize independently without distorting their entire row, so "the clicked day's area grows, pushing content below it down" is implemented as: each week is its own full-width 7-column sub-grid row, and clicking a day inserts an additional full-width strip immediately after *that week's row* — not by changing the height of the individual day cell. This strip shows:
- The selected date as a heading
- That day's existing events as a list (title, time if set, delete button)
- A small add-event form scoped to that date (title input, optional time input, add button)

Clicking a different day moves the strip to sit below the new day's week row (collapsing the old one). Clicking the already-selected day again collapses the strip with no day selected.

### Agenda list

A separate `.gm-card` below the month grid, titled "Upcoming," listing the next 5 events with `date >= today` across any month (not scoped to whichever month the grid happens to be showing), sorted by date then time ascending. Each row shows a short date label (e.g. "Wed Jul 1"), the title, and the time if set. If fewer than 5 events exist, it just shows what's there; if zero, an empty state ("Nothing on the calendar yet").

### Error handling

Lightweight, matching the rest of the codebase: adding an event requires a non-empty title (date comes from whichever day is selected, so it's never missing); no confirmation dialog on delete.

### Testing

No automated test framework exists in this repo. Verification is manual: add events across a few different days and months, confirm the month grid's event dots and expand-in-place behavior work, confirm the agenda always shows the next 5 regardless of which month is currently displayed in the grid, confirm month navigation works and doesn't persist across reload, confirm deleting an event removes it from both the expanded-day view and the agenda, and confirm cloud sync actually fires this time (verify `initCloudSync` is called after `DOMContentLoaded`, not before).
