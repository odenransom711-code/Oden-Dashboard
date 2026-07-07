# Fitness page: quick split-tagging

## Context

`gym.html` ("Progressive Overload Coach") already has a sophisticated split-rotation system: `state.splitRotation` is a user-editable list of split names (Push/Pull/Legs/Rest/anything), `state.splitAnchor` pins a real date to a rotation index so `todaySplit()` can compute "what split is today," and a full rotation editor (rename/reorder/add/delete/set-today) already exists (gym.html:2404-2499). Detailed per-exercise logging (weight, reps, progressive-overload suggestions) also already exists and feeds the composition/body-fat estimate and volume totals — that stays exactly as-is.

The gap: `doneDays[dateKey]` (gym.html:2091-2098) currently just stores a timestamp marking a day "done," and the existing "Mark workout done" button (gym.html:1574, handler at 2214+) is disabled until at least one exercise set has been logged that day (`btn.disabled = sum.totalSets === 0 && !isDone`, gym.html:2177). There's no way to mark a day done — with which split — without first logging individual sets.

## Design

### Data model

Extend `doneDays[dateKey]` from a bare ISO-timestamp string to an object: `{ ts: ISOString, split: string }`. Both the new quick-tag chips AND the existing "Mark workout done" button write to this same structure — the button, when clicked, records `todaySplit().name` as the split (matching what it already implicitly represents, since it's only enabled when you've been logging exercises that day, which are themselves categorized by day/split).

### Quick-tag row

A new row of chip buttons, one per entry in `state.splitRotation` (including "Rest," since intentionally tagging a rest day is useful for consistency tracking), placed directly above the existing "Today's workout" sub-section (gym.html:1561). Today's computed split (`todaySplit().name`) gets a subtle pre-highlight so it's the obvious first tap, but any chip is tappable regardless — you're not locked into the rotation's prediction.

- Tapping an untagged chip sets `doneDays[todayKey] = { ts: now, split: chipName }` immediately — no confirmation, no exercise logging required.
- Tapping the currently-tagged chip again removes the tag (toggle off).
- Tapping a different chip while one is already tagged switches the tag to the new split (one tag per day, matching the existing one-`doneDays`-entry-per-day model).
- The existing "Today's workout" set list, set count, and "Mark workout done" button are untouched and still fully usable independently — quick-tagging and detailed logging can both happen on the same day if you want (e.g., quick-tag now, log a couple of sets later — the button's own state and the chip row both just reflect the same underlying `doneDays` entry).

### Past Workouts

`renderPastWorkouts()` (gym.html:2181-2212) currently summarizes a past day from its logged exercise sets, and separately shows a "DONE" badge if `doneDays[dk]` exists. For a day that was quick-tagged with zero logged exercises, `summarizeDay()` naturally returns `totalSets: 0, perEx: []`, which currently renders an empty exercise-name line. This gets a small update: when a day has `doneDays[dk]` set but no logged exercises, show the tagged split name in place of the (empty) exercise-name summary line, e.g. "Push · quick tag" instead of a blank string. Days with both logged exercises and a tag continue showing the exercise-name summary as before (the tag doesn't need separate display there, since the DONE badge already covers it and the split is inferable from which exercises were logged).

### Scope cut

Quick-tagging only ever applies to *today* — there's no UI to retroactively tag a past day you forgot. That's a reasonable future add if it turns out to matter, but wasn't asked for and isn't needed for the core "let me tag today's split without logging sets" request.

### Error handling

None needed beyond what's already lightweight elsewhere in this codebase — tapping a chip is a direct, reversible (toggle) action with no destructive confirmation needed, consistent with how the rest of this dashboard handles simple state toggles.

### Testing

No automated test framework exists in this repo. Verification is manual: tap a quick-tag chip with zero exercises logged today, confirm `doneDays` gets the right shape and the chip visually shows as tagged; tap it again and confirm it un-tags; log a couple of exercise sets and use the existing "Mark workout done" button, confirm it also now records a `split` field correctly (using `todaySplit().name`); check Past Workouts after reloading (or navigating to a prior day's data if testable) shows the quick-tagged split name for a done-but-unlogged day, and shows the normal exercise summary for a day with both logs and a tag.
