# Family communications — cadence and purpose

*Design principle: every message has exactly ONE job, and its content is engineered so the only conversational move it leaves open is the intended one. Every format survives a week on the operator's own family before any beta family receives it.*

## Kid-facing
- **Access text (once, ever):** the key. Personal link + "Add to Home Screen." After this, the icon is the channel — no texts are ever needed to play.
- **Weekly recap (Fri):** game-flavoured arc of the week — score trend, streak, what got beaten, what's stalking them next week. Link for the detail. Tone: fellow player, not teacher.

## Parent-facing — three touchpoints, three jobs
| Touchpoint | Trigger | Job | Content |
|---|---|---|---|
| **Daily soundbyte** | run completion | **Reassure** | Done + points + streak. Nothing else. |
| **Midweek check-in** | Wed morning | **Activate** | Momentum read + ONE "something to say" (specific, data-grounded praise script) + ONE "area where you can help" (~5-minute action) |
| **Friday headlines** | Fri evening | **Judge** | Three headlines + link to the full report page |

**The no-ammunition law (daily layer):** the soundbyte never carries misses, gaps, or anything interrogable — a parent cannot turn it into an interrogation because there is nothing in it to interrogate with. The only move it leaves open is praise. Gaps surface only where they arrive dressed as *help* (midweek) or *perspective* (Friday).

**Open calibration (under live family test):** do ratios like "6/7" whisper *there was a miss*? If the test parent feels the pull to ask "which one?", the beta soundbyte drops to pure points-and-streak.

**Why the midweek matters most:** most parents don't lack interest, they lack a script. The check-in hands them one praise line and one 5-minute action — it productises the ledger's sit-down actions and channels parental energy into a single constructive touch instead of nightly questioning.

## Surfaces — SMS → weekly report → portal (what lives where)

Three surfaces, three time-frames. Only the SMS is *sent*; the other two are hosted pages (per-kid URLs, same model as the quiz).

1. **Friday SMS** — the only thing pushed (one-way SMS is the channel). Lead line + three headlines + a link. Can't carry rich content — it's the teaser.
2. **Weekly report** — a hosted HTML page the SMS link opens, self-contained so one tap gives the whole week. **A snapshot: this week, bounded.** Answers "how was *this* week?"
3. **Portal** — a second hosted, evergreen, bookmarkable page reached from the report ("see {name}'s full picture →"). **The cumulative shape — the film and the full atlas.** Answers "how's he doing *overall*?" Organised around subjects and time, not this week.

Flow: **SMS (teaser) → weekly report (this week, self-contained) → portal (cumulative, on tap).** The still frame is the report; the film and the atlas are the portal. Weekly reports are frames that drop into the portal's timeline.

### Which surface does a thing belong to? — does it have a time dimension?
A *number* is the report; a *trend* is the portal.
- "Maths is behind this week" → report. "Maths has been slipping three weeks" → portal.
- Where he stands *now* → report. Comprehension trend-lines *over the term* → portal.

### What lives where
- **Weekly report:** hero line · the three rows · the win · what's-next · assessment-readiness (when a test is near) · the action · a *compact* where-he-stands-now snapshot.
- **Portal:** the full per-subject/per-topic mastery map · comprehension *over the term* (trends) · overall strengths-and-growth shape · the archive of past weekly reports.

### Form + build order
- SMS is sent (branded one-way). Report + portal are hosted HTML (per-kid URL, like the quiz), self-contained. Email is a later option if parents ask — SMS-first keeps the channel single.
- **Build the weekly report first** (it's what the Friday touchpoint delivers); the portal is the depth behind it and can be lighter in week 1, filling in as history accumulates — trends need weeks to exist. (The parent dashboard mocked earlier is the *weekly report* view; the cumulative portal is a separate, not-yet-mocked screen.)

## The weekly parent report (surface 2 — the "this-week" page the Friday SMS links to)

Self-contained snapshot of the week. Detailed below; the cumulative view is the portal (above).

### The lead (hero) line — carries TWO things fused
Standing **and** trajectory in one sentence a parent can exhale on:
> "{name} — strong week. Keeping pace with his coursework and moved two topics forward since last week."

Standing = "keeping pace"; trajectory = "moved two forward"; activity is implied. This is the sentence that does the work if it's all they read.

### The week-word (the tone-setter) — CODE picks it, from thresholds
Four words, framed on effort/trajectory not outcome, so a hard week is never a rebuke of the kid:

| Word | Means | Parent action it implies |
|---|---|---|
| **Strong** | high activity + forward movement | celebrate |
| **Solid** | steady, on pace, undramatic (most weeks) | keep going |
| **Quiet** | low activity / missed days — factual, no judgement | nudge the habit |
| **Slower** | showed up, but things landed harder / a topic slid back | support the learning |

- **Quiet ≠ slower, deliberately:** quiet = an *engagement* dip (didn't show up); slower = a *comprehension* dip (showed up, tougher). Opposite parent actions, so they stay distinct.
- **Quiet outranks slower** when both are true: sparse activity means you can't honestly diagnose comprehension, so name the activity and don't stack a "slower" judgement on thin evidence.
- The word is chosen **deterministically from thresholds** (days completed, net topic movement). The AI writes the sentence; code picks the word — so the tone can't drift run to run.

### The three rows (one axis each, for the parent who wants the why)
- **This week** (activity — reassurance): days done · topics practised · events cleared. Safe facts only.
- **Where he stands** (standing — the insight): lead with the overall verdict, name only the exceptions ("on pace, except Maths — a step behind the current unit, pacing not a gap"). Full per-subject detail lives lower on the page, not in this row.
- **Since last week** (trajectory — the movement): net + notable — "moved 2 forward," name the biggest ↑ and any ↓ that needs action. Not every wobble.

### What "keeping pace" means (honest + computable)
The targets layer knows what class is *currently teaching*; the ledger knows what's *mastered*. **Keeping pace** = live topics reaching developing/solid roughly as fast as they go live. **"A step behind"** = a topic's been live a while but is still shaky/untested — taught, not landing yet.
- Never a bare "behind." Never against other children — there is no cohort, so "behind" can only ever mean behind *his own syllabus*. Always paired with the specific fixable thing.

### Laws (parent-side)
- **Code decides, language dresses:** the word, thresholds, standing verdict and movement list are computed; the AI only writes them into sentences.
- **The no-anxiety rule** (parent-side of no-ammunition): a flagged area always arrives *with its fix*, never as bare worry. Under-claim when data is thin.
- **Week 1 has no prior:** the first report drops trajectory, leans on standing + a "here's where he's starting" baseline; trajectory switches on from week 2.

### Still under design (candidate additions to the page)
A win/highlight to celebrate · a "what's coming next week" forward look · assessment-readiness when a test is near (the planner is already assessment-aware) · whether the warm narrative paragraph stays or the hero + rows replace it · whether the kid's achievements get a light, insight-framed mention.


## Config and delivery
- Per-family on/off per touchpoint, set at onboarding.
- Delivery: branded one-way SMS (sender = product name), with a "questions? text the operator" line since one-way can't receive replies.
- The message IS the tier-1 report. Links are the deep dive, never the paywall — a parent who never taps still got real value.
