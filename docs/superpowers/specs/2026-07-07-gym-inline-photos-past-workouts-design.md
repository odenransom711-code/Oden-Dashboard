# Fitness page: inline photo grid + always-visible Past Workouts

## Context

The daily weight log and physique photo check-in the user asked about already exist in full in `gym.html` — this isn't new functionality, it's a visibility change. Two things currently require an extra tap to see:
1. **Progress photos** — the photo grid, "Take Photo," and "From Library" buttons only appear after tapping a "PROGRESS PHOTOS" link, which slides in a full-screen overlay (`#wtOverlay`, `position: fixed; inset: 0`, gym.html:1092-1099).
2. **Past Workouts** — collapsed by default (`#poTwPastBody`, `style="display:none"`, gym.html:1613), expanded via a toggle button.

The user wants both inlined into the normal page flow, matching how every other section on this page (weight tracker, exercise logger, stats, today's workout) already works — no extra taps.

## Design

### Inline photo grid

Remove the "PROGRESS PHOTOS" button (`#wtProgressLink`, gym.html:1374-1380) and the full-screen slide-up shell around the photo grid (the back button, "Progress" title bar, and `.wt-overlay`'s fixed positioning, gym.html:1384-1402, 1092-1099). What's left — the "Take Photo"/"From Library" action buttons and the photo grid itself (`#wtPhotoGrid`) — becomes a new `po-sub-section` (matching the heading style already used for "History," "Today's workout," etc.) placed directly after the weight tracker's existing content, in normal document flow.

`photosRender()` (gym.html:3070+, already builds the grid's HTML from stored photos) currently only runs when the overlay is opened (`$('wtProgressLink').addEventListener('click', ...)`, gym.html:3154-3158) — it needs to run at page load instead (wired into the same render orchestrator that already calls `renderTodaysWorkout()`/`renderPastWorkouts()`/etc.), so the grid has real content immediately without requiring a click first. The `document.body.style.overflow = 'hidden'` scroll-lock (gym.html:3157, needed because the old overlay covered the whole viewport) is removed — it has no purpose once the grid is inline.

**Unchanged:** the camera capture screen (`#wtCam`) and the single/compare photo viewer (`#wtViewer`) stay exactly as full-screen overlays. Tapping "Take Photo" still opens the camera; tapping a photo in the grid still opens the full-screen viewer/compare tool. Only the *browsing grid* becomes inline — taking a photo or viewing one full-screen are legitimately focused actions, consistent with how modals work elsewhere in this dashboard (e.g. Calendar's day-detail expansion, the exercise/rotation/settings modals already in this same file).

### Past Workouts always visible

Remove the `#poTwPastToggle` button (gym.html:1609-1612) and its click handler (gym.html:2291+). `#poTwPastBody` (gym.html:1613) loses its `style="display:none"` and renders inline, always populated by the existing `renderPastWorkouts()` call already wired into the page's render cycle — no behavior change to how past workouts are computed or displayed, purely a visibility change.

### Testing

No automated test framework exists in this repo. Verification is manual: confirm the photo grid and its Take Photo/From Library buttons render immediately on page load (with existing photos, if any, already visible — no click needed); confirm tapping Take Photo/From Library and tapping an existing photo still work exactly as before (camera opens, viewer opens); confirm Past Workouts renders immediately below Today's Workout with no collapsed state or toggle button visible.
