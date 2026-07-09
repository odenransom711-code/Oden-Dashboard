# Fitness page: simplified Upper/Lower/Cardio logging

## Context

`gym.html` ("Progressive Overload Coach") currently logs workouts one **set** at a time: pick a gym + day filter, pick one exercise from a dropdown, enter a weight and a rep count via a pill picker, tap "Log set" — repeated for every individual set of every exercise. This is wired tightly into a progressive-overload coaching layer: each exercise carries a configured rep-range/weight-step (`repMin`/`repMax`/`step`), and "Next session" prescriptions, "Last time" comparisons, 1RM/best-set stats, a trend sparkline, and a body-composition estimate all read the resulting per-set log history (`state.logs[exerciseId] = [{weight, reps, date}, ...]`).

The user finds this confusing and wants a simpler flow: pick a day type (Upper/Lower/Cardio), add an exercise, and log **one entry per exercise per session** — sets, reps, and weight together — instead of tapping "Log set" repeatedly. There's no real exercise/log data in the dashboard yet (confirmed with the user), so this is a clean replacement, not a migration.

The user explicitly wants to **keep** the dependent coaching features (prescriptions, 1RM/best-set, sparkline, composition estimate) — adapted to compute from the new per-session data shape rather than removed.

## Design

### Data model

`state.logs[exerciseId]` changes from an array of per-set entries to an array of per-session entries:

```js
// Before: one entry per set
{ weight: 100, reps: 8, date: "2026-07-08T14:00:00.000Z" }

// After: one entry per exercise per logging action (sets + reps + weight together)
{ weight: 100, sets: 3, reps: 8, date: "2026-07-08T14:00:00.000Z" }
```

`state.exercises[i]` drops the progressive-overload configuration fields (`repMin`, `repMax`, `step`, `startWeight`) that existed only to drive the old per-set coaching rules. It keeps: `id`, `name`, `day` (now one of `upper`/`lower`/`cardio`), `bw` (bodyweight toggle — still useful to know whether to show/require a weight field).

`CONFIG.days` (and the fresh-state default `state.days`) changes from `[Push, Pull, Legs]` to `[Upper, Lower, Cardio]`. `CONFIG.splitRotation`/`state.splitRotation` (used by the already-shipped quick-tag feature and the day-pill's "what split is today" logic) updates to match: `["upper", "lower", "cardio", "rest"]`. The **gym filter/dimension is dropped entirely** from this page — the user's description of the desired flow never mentions it, and removing it is part of the simplification they asked for. `state.gyms`/`state.filterGym` and every exercise's `gym` field are removed; the gym segmented-button row disappears from the UI.

### New logging UI

Replaces the current Gym/Day filter row + Exercise dropdown + weight/reps-pill/"Log set" form with:

1. **Day type** — a segmented control (Upper / Lower / Cardio), same visual pattern as the existing day-pill/segmented-button styling already used elsewhere on this page. Selecting one filters the exercise dropdown below it, same filtering mechanism as today just on one dimension instead of two.
2. **Exercise** — a dropdown filtered to the selected day type, with the existing "+" button opening an add-exercise modal that's now much simpler: just a **name** field and a **bodyweight** toggle. The day type is inherited from whichever day-type is currently selected (no separate day picker inside the modal). No rep-range/step/start-weight fields — those are gone along with the old per-set coaching rules that used them.
3. **Log entry** — three inputs: **Sets** (number), **Reps** (number, reusing the existing pill-picker style already built for reps), **Weight** (number, reusing the existing +/− stepper) — hidden/replaced with just Sets + Reps when the exercise is marked bodyweight. One tap on "Log" records the whole entry as a single `state.logs[exerciseId]` push.

### Adapted dependent features

- **1RM / best-set stats**: identical Epley-formula math (`estimate1RM(weight, reps)`), now evaluated once per session entry instead of once per individual set — same function, same formula, just fed session-level `{weight, reps}` pairs instead of set-level ones. No change to the estimation logic itself.
- **Sparkline / trend chart**: plots the same estimated-1RM-over-time line, now with one point per logged session instead of one point per set — visually chunkier (fewer points for the same training history) but the same rendering code path.
- **"Last time" comparison**: shows the most recent session's `sets × reps @ weight` instead of a single set's `reps @ weight`.
- **"Next session" prescription** (`getRx()`): the old rule (stuck 3+ sessions at the same weight below `repMin` → deload 10%; hit `upgradeAtReps` → add `step` weight; otherwise add a rep) depended entirely on the now-removed `repMin`/`repMax`/`step` per-exercise configuration. New rule, using one fixed global step (2.5 for kg, 5 for lb — matching `CONFIG.upgradeAtReps`'s existing role as a single global tuning knob rather than per-exercise config): if the last 2+ sessions used the same weight, suggest adding the step for next time; otherwise suggest repeating the same sets/reps/weight. Bodyweight exercises: if the last 2+ sessions hit the same rep count, suggest one more rep; otherwise suggest repeating.
- **Composition/body-fat estimate**: **no changes needed** — it already aggregates `state.logs[ex.id]` by calendar day and sums `weight × reps` for volume, generically, regardless of whether there's one entry per set or one per session. Verified directly against its actual code before writing this spec.
- **History card**: lists sessions ("3×8 @ 100kg — Jul 8") instead of individual sets — same list-with-delete-button UI pattern, just one row per logged session instead of one row per set.
- **"Today's workout" / "Past workouts" summaries**: unaffected in structure (they already group by day and sum sets/volume across whatever's in `state.logs`) — they'll just show session-level entries instead of set-level ones, which if anything makes their per-exercise set-count display more directly meaningful (it already tried to show "N sets" per exercise per day; now that's a direct field read instead of an array length).
- **Quick-tag feature** (already shipped): fully independent of `state.logs`, reads only `state.splitRotation`/`doneDays` — needs its rotation labels updated to Upper/Lower/Cardio (a data change, `CONFIG.splitRotation`) but no logic changes.
- **Weight-tracking section**: fully independent (separate `po_coach_weights` localStorage key) — untouched by any of this.

### Error handling

Lightweight, matching the rest of this codebase: the Log button requires a selected exercise and non-empty sets/reps (weight too, unless bodyweight) before submitting; no confirmation dialog on deleting a logged session from History, consistent with how set-deletion already worked.

### Testing

No automated test framework exists in this repo. Verification is manual: add a new exercise under each day type, log a session for it (sets/reps/weight), confirm it appears in "Today's workout" and History; log a second session at the same weight and confirm the "Next session" prescription suggests adding weight; confirm 1RM/best-set stats and the sparkline populate correctly from session data; confirm quick-tag chips now show Upper/Lower/Cardio; confirm the composition estimate (if enough weight-tracking + exercise history exists) still computes without errors.
