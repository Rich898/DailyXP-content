# Weekly Canvas content sweep — drill

*Runs once per week (Tue-ish; Monday quizzes are ledger-consolidation by design). Done via the Claude-in-Chrome extension panel riding the owner's logged-in browser. Retires when the scheduler's Canvas-API integration (student access tokens) lands.*

## Steps
1. **Panel on the right account.** Open Chrome → Claude side panel (icon near the address bar). It MUST be signed into the same account as the project chat — a different (e.g. work) account fails silently. Check before anything else.
2. **Log into the school's Canvas** as you normally access the students. Separate student logins = run the sweep once per session.
3. **Paste the sweep instruction** (below) into the panel with Canvas open in the tab.
4. **Sanity-check the output:** one section per student, dot points per subject, per-teacher pages covered where relevant, assessment dates captured.
5. **Bring it to the project chat** — paste the summary or upload it as a file. The panel and the project chat are separate contexts; the paste is the bridge.

## Sweep instruction (paste into the panel)
```
Sweep this week's Canvas content for the students. For every active course,
open the current week's modules/pages and summarise per subject as dot
points: topic names, key concepts/skills, and anything assessment-related
(dates, task types, notifications). For y9, ALSO check the per-teacher class
pages for Science and English — their content doesn't live on the shared
module pages — and note whether Science Term 3 content has been posted yet.

If page-walking is slow, use the Canvas API instead:
GET /api/v1/courses?enrollment_state=active&per_page=50 for course IDs, then
/courses/[ID]/modules — batch in groups of four with ~1.5s pauses.

Output: one section per student, one sub-section per subject, dot points
only. End with "NEW OR CHANGED vs last week" and any assessment dates found.
```

## Known quirks
- **y9:** Science and English live on per-teacher class pages (shared modules incomplete). **y8:** English is the per-teacher subject; Maths/Science/HSIE/Music use shared modules, with Maths and Science running week-by-week schedules on the course HOMEPAGE — sweep the homepage, not just modules, for those two.
- Shared-module subjects are consistent across a year level; **Science and English live on per-teacher class pages** — a sweep that skips them looks complete but isn't.
- The extension only works while the owner's Canvas session is open — it cannot log in itself and cannot be scheduled. Hence the token-based replacement on the roadmap.
