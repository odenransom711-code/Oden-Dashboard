# School page (school.html)

## Context

This is phase 2 of a 3-phase dashboard redesign:
1. [Done] Fold Water and Caffeine into Health.html as "Hydration" and "Stimulation" sections (`docs/superpowers/specs/2026-06-30-health-hydration-stimulation-design.md`)
2. **This spec** — build a new School.html page (assignments/deadlines, classes/schedule, grades, exam countdown)
3. Redesign the hub (index.html): uniform-size nav tiles, a built-in Calendar block (month grid + agenda) featured prominently up top, snapshot/graph cards filling remaining grid space, removal of the standalone Water/Caffeine hub tiles, and addition of a School tile

Phase 3 is out of scope for this spec and will get its own design doc.

## Problem

The user wants a School section to track classes, assignments/deadlines, grades, and exam countdowns. There's no existing school-related page or data model in this dashboard.

The user also wants a single, visual calendar (showing classes alongside workouts, meetings, etc.) — that is the planned Phase 3 hub Calendar feature, not something this page should duplicate. This spec scopes Classes as a plain data list whose shape (days/times) is designed to later feed Phase 3's calendar as recurring events, without building any timetable/visual-schedule UI here.

## Design

### Conventions

Follow the established per-page pattern used by every other dashboard page (`gym.html`, `finance.html`, `health.html`), scaffolded from `template.html`:
- Same visual language: `dash-title`, `section-title`, `.gm-card`, `.stat-grid`, `.gm-input`/`.gm-add` form controls, `.goal-list`/`.gm-row` editable-list pattern.
- Data persists to localStorage and syncs across devices via `window.initCloudSync({ appKey, syncedKeys, onApplied })`, exactly like every other page. `appKey: 'school'` is unused by any existing page (confirmed: `caffeine`, `finance`, `health`, `goals`, `template` are taken).
- One root localStorage key, `school_v1`, holds the entire page's state as a single JSON object — keeps the sync surface to one key, same as how `finance.html`/`health.html` structure their primary state.

### Data model

```js
{
  activeSemesterId: "sem_1",
  semesters: [
    {
      id: "sem_1",
      name: "Fall 2026",
      classes: [
        {
          id: "cls_1",
          name: "Calculus II",
          instructor: "Dr. Lee",
          days: ["Mon", "Wed", "Fri"],
          startTime: "09:00",
          endTime: "09:50",
          room: "Building 4, Rm 210",
          grade: 91          // percentage, null if ungraded
        }
      ],
      tasks: [
        {
          id: "task_1",
          title: "Problem Set 4",
          type: "assignment",  // "assignment" | "exam"
          classId: "cls_1",    // nullable — task may not be tied to a class
          dueDate: "2026-07-10",
          done: false           // assignments only; ignored for exams
        }
      ]
    }
  ]
}
```

This shape is intentionally close to flat: `days`/`startTime`/`endTime` on each class are exactly what a future Phase 3 calendar integration needs to expand a class into recurring weekly events, without this page needing to know anything about Phase 3.

### Page layout (top to bottom)

1. **Header** — `<h1 class="dash-title">School</h1>` plus a semester switcher directly below it: a `<select>` populated from `semesters`, plus an "Add semester" control (text input + button, creates a new semester object with empty `classes`/`tasks` and switches `activeSemesterId` to it). All sections below operate only on the active semester's data.

2. **Overview** (`section-title` "Overview") — a `.gm-card` with:
   - Big number: average of all non-null `grade` values across the active semester's classes (`—` if no classes have a grade yet)
   - `.stat-grid` with two stats: class count, upcoming-task count (tasks with `dueDate >= today`, regardless of type)

3. **Classes** (`section-title` "Classes") — list of class cards in the active semester. Each card shows name, instructor, days (e.g. "Mon/Wed/Fri"), time range, room, and an editable grade field (percentage input, blank = ungraded). Cards are deletable (immediate, no confirmation, matching `template.html`'s existing delete-button pattern). An add-class form below the list (name, instructor, days checkboxes, start/end time, room) — name is required to submit.

4. **Upcoming** (`section-title` "Upcoming") — single list combining the active semester's assignments and exams, sorted by `dueDate` ascending. Each row shows:
   - A type badge ("Assignment" or "Exam")
   - Title, and the linked class name if `classId` is set
   - For assignments: a checkbox toggling `done`
   - For exams: a countdown chip computed live from `dueDate` vs. today — "in N days", "Today", or "Overdue" (reuse the same date-diff helper for the assignment rows' optional overdue styling, so there's one countdown engine, not two). "Today" means the user's local calendar date via plain `new Date()` — unlike Health's 6 AM daily-reset cutoff for habit logs, due dates are calendar days, not daily resets, so no special cutoff hour applies here.
   Rows are deletable. An add-task form below (title, type select, due date picker, optional class dropdown sourced from the active semester's `classes`) — title and due date are required to submit.

### Error handling

Lightweight, matching the rest of the codebase: required-field checks block submission of empty class names or task titles (no due date, no class — those are truly optional); no destructive-action confirmations on delete, consistent with `template.html`'s existing list-delete behavior.

### Testing

No automated test framework exists in this repo (confirmed during phase 1 — no test script in `package.json`, no test files anywhere). Verification is manual, in a browser:
- Add a semester, add classes with grades, confirm the Overview average updates correctly
- Add assignments and exams with various due dates, confirm the Upcoming list sorts correctly and countdown chips compute correctly relative to today
- Toggle an assignment done, reload, confirm it persisted
- Switch between two semesters, confirm each keeps its own classes/tasks/grades independent of the other
- Confirm deleting a class that's referenced by a task doesn't crash the page (task's `classId` becomes a dangling reference — the Upcoming row should fall back to showing no class name rather than erroring)
