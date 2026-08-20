# Family communications — cadence and purpose

*Design principle: every message has exactly ONE job, and its content is engineered so the only conversational move it leaves open is the intended one. Every format survives a week on the operator's own family before any beta family receives it.*

## The week at a glance (canonical rhythm — Mon–Fri term weeks)
| When | Kid gets | Parent gets |
|---|---|---|
| Once, at onboarding | Access text: personal link + "Add to Home Screen" | — |
| Mon–Fri **4:00pm** | **"XP Daily is up"** nudge (🐉 boss flavour Fri) — sent only after the live set is verified as *today's* | — |
| Mon–Fri evening, **on completion** | — | **Soundbyte**: did it + XP + verdict, nothing else |
| **Wed** evening, **on completion or 8:25pm cutoff** | — | **Merged check-in**: Wednesday's soundbyte three beats + midweek body (replaces the plain Wed soundbyte) |
| **Fri** evening | **Weekly wrap** link + **kid portal** link | **Weekly report** link (the report carries the parent-portal link) |

Friday evening deliberately carries **two** parent texts — the soundbyte (fires on the kid's clock, whenever he completes) and the report (scheduled). Different jobs, different clocks; folding would delay reassurance or hostage the report to completion time. The week-1 family test calibrates whether that ever feels like spam.

**Onboarding captures per family:** parent mobile · kid mobile · parent email (collected but unused in v1 — SMS-first stays the law; the field future-proofs receipts and "email me the report").

## Kid-facing
- **Access text (once, at onboarding):** the key. Personal link + "Add to Home Screen."
- **Daily nudge (Mon–Fri 4:00pm):** "XP Daily is up" — after school, phones back in hands. Flavoured by the weekly skeleton (⚡ Wed, 🐉 Fri). Sent only after verifying the live set really is today's — a review HOLD or frozen day texts nobody. Celebration is NEVER in the text; it lives in the in-quiz end screen.
- **Weekly wrap (Fri evening):** game-flavoured arc of the week — score trend, streak, what got beaten, what's stalking them next week — as a link to the hosted wrap page, plus the kid-portal link. Tone: fellow player, not teacher.

## Parent-facing — three touchpoints, three jobs
| Touchpoint | Trigger | Job | Content |
|---|---|---|---|
| **Daily soundbyte** | run completion | **Reassure** | Did it + tonight's XP + a verdict closer. Nothing else. |
| **Midweek check-in** | Wed evening (on completion; 8:25pm cutoff) | **Activate + set expectations** | MERGED with Wednesday's soundbyte: the three beats on top, then honest momentum (the week-word, sampled midweek) + at most ONE ask or five-minute help action + always ends pointing at Friday's wrap |
| **Friday headlines** | Fri evening | **Judge** | Three headlines + link to the full report page |

**The no-ammunition law (daily layer):** the soundbyte never carries misses, gaps, or anything interrogable — a parent cannot turn it into an interrogation because there is nothing in it to interrogate with. The only move it leaves open is praise. Gaps surface only where they arrive dressed as *help* (midweek) or *perspective* (Friday).

**The daily soundbyte — final form (ratified 9 Aug 2026, day 1 of live).** Exactly three beats: **(a)** did it **(b)** tonight's +XP **(c)** a verdict closer. The verdict is what gives the score its meaning — a bare number means nothing to a parent. The verdict LADDER is effort/energy language, never grade-words, picked by code from score/max thresholds (85/70/50): *flew tonight* → *good night's work* → *put in a shift* → *the set bit back — hung in there*. **Banned from the daily layer:** percentages, ratios, running totals (a total belongs to the Friday report and the portal), misses, subjects, day-vs-day comparison. **Attribution law:** success belongs to the kid; difficulty belongs to the set — true, because the planner picks the difficulty — so even the floor verdict leaves only a praise-family move open. **The legend law:** the ladder's numeric definitions are published ONCE (the onboarding parent welcome; later the portal footer), so the words are precise claims to any parent who read the front door — without any specific night ever arriving as a grade. Tiny sets (warm-ups) carry no verdict. Silence remains the only "not done" signal.

**The Wednesday check-in — final form (ratified 9–10 Aug 2026): MERGED with Wednesday's soundbyte, evening delivery.** Wednesday is the **expectation-setter for Friday's wrap**: the arc is *daily reassures → Wednesday sets expectations and hands over one action → Friday resolves* — so the report always lands as the resolution of a story the parent is already inside, never a surprise verdict. **Delivery:** Wednesday evening, on completion (polls 6:25pm + 8:25pm, five minutes ahead of the soundbyte polls). When tonight's run is in, ONE merged SMS: the soundbyte's three beats on top (its own law, its own digits), the check-in body under it — and both cursors advance, so the plain Wednesday soundbyte never double-sends. Evening-on-completion is deliberate: the ask lands minutes after the kid practised the topic. **The cutoff law (8:25pm, run not in):** a *scheduled* weekly touchpoint cannot use silence — a missing expected message is louder and more alarming than a neutral line (the silence law stays where it belongs: the completion-triggered daily). The check-in goes out on the Mon–Tue read with the tonight-status law: **status plus open door, never judgment** — "tonight's run isn't in yet — if it lands later this evening, the usual text will follow" (the 9:30pm soundbyte poll keeps that promise). And ONLY when the set is verifiably published today: **our gaps are never reported as the kid's.** **One week-word engine, sampled twice, like for like:** Wednesday runs the same thresholds Friday uses — Mon–Wed vs LAST week's Mon–Wed when tonight's in, Mon–Tue vs Mon–Tue at the cutoff — so the two can never contradict. **Honest momentum, undramatic:** up is said, flat is said, down is said — "a bit behind last week", never bare "behind", never accusatory; quiet outranks slower, so thin evidence never gets a comprehension judgement stacked on it. At most **ONE ask** (a strength drawn out as a dinner-table question — the kid explaining is the pedagogy) and **ONE five-minute help action** (repair-flag first, then shaky), the gap dressed as help and **planted for Friday** ("it's the one Friday's wrap will centre on" — Wednesday plants, Friday harvests). No digits, no percentages, no ratios anywhere in the BODY (validator-enforced; the soundbyte line above carries XP under its own law); code picks every fact, the model dresses language only, and a deterministic fallback in the redlined voices sends when the model's text fails the law — the Wednesday never goes silent or off-law over an API blip. Every check-in ends pointing at Friday.

**Why the midweek matters most:** most parents don't lack interest, they lack a script. The check-in hands them one praise line and one 5-minute action — it productises the ledger's sit-down actions and channels parental energy into a single constructive touch instead of nightly questioning.

## Surfaces — SMS → weekly report → portal (what lives where)

Three surfaces, three time-frames. Only the SMS is *sent*; the other two are hosted pages (per-kid URLs, same model as the quiz).

1. **Friday SMS** — the only thing pushed (one-way SMS is the channel). Lead line + three headlines + a link. Can't carry rich content — it's the teaser.
2. **Weekly report** — a hosted HTML page the SMS link opens, self-contained so one tap gives the whole week. **A snapshot: this week, bounded.** Answers "how was *this* week?"
3. **Portal** — a second hosted, evergreen, bookmarkable page reached from the report ("see {name}'s full picture →"). **The cumulative shape — the film and the full atlas.** Answers "how's he doing *overall*?" Organised around subjects and time, not this week.

Flow: **SMS (teaser) → weekly report (this week, self-contained) → portal (cumulative, on tap).** The still frame is the report; the film and the atlas are the portal. Weekly reports are frames that drop into the portal's timeline.

**The kid side mirrors it:** daily SMS (nudge) → **weekly wrap** (hosted, Friday's game-flavoured arc) → **kid portal** (evergreen — level/XP, streak, achievements wall, mastery map in game vocabulary; this is the "kid dashboard" mocked earlier). Same per-kid-URL hosting model. Parent surfaces speak insight; kid surfaces speak game — same ledger underneath.

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

---

## Friday report — ratified 11 Aug 2026

Decisions taken when the Friday surfaces were built. These supersede any earlier
reading of this file where they conflict.

### The Friday law is NOT the Wednesday law

Wednesday forbids digits. **Friday permits numbers**, and the first build was
wrong to port Wednesday's rule across. "No-ammunition" on Friday means *every
flagged area arrives with its fix in the same breath* — not "no numbers". A
report can carry accuracy, counts and the XP total and still be safe, because
the resolution travels with the finding.

Still banned on Friday: `%` and score-slashes **in the SMS** (comprehension is a
word there, never a number), bare "behind" (only "a step behind"), paywall
framing on the link, and the banned words (miss, wrong, fail, dumb, lazy).
Accuracy figures ARE allowed on the hosted page, where there is room for the
caveat beside them.

### What leads, and what does not

* **Mastery movement leads.** The ledger is the product; the report must show it.
* **Points are demoted.** Difficulty varies between days, so points-per-day is
  the least trustworthy figure on file. It never leads, and **there is no points
  target** — a target on points rewards choosing easier questions. Targets belong
  on mastery and cadence. XP-by-day belongs on the KID wrap page as a game
  metric, not on the parent report.
* **Assessment readiness sits high** — the most actionable thing a parent can be
  told is what is coming and whether he is ready for it.

### Gaps: show them all, frame them as position

A paying parent wants to know about gaps — that IS the value, and hiding them to
seem kind removes the reason to subscribe. **The artistry is in the framing.**

* No binary tick/cross on the parent report. Every topic sits on a **red→amber→
  green scale** with a plain label ("Getting started" / "Building" / "Nearly
  there" / "Solid"), so a gap reads as a position on a journey.
* **Headlines derive from the band**, never from the week's events, so the title
  and the scale beneath it can never contradict each other.
* **Misconception-level diagnosis**: name the wrong option chosen and why it is
  wrong, from the archived set's own `why`. "He chose Parallelogram; a trapezium
  has only one pair of parallel sides" — not "got a maths question wrong". This
  is the difference between a parent being told to practise a topic and being
  told the one thing to fix.

### Week-over-week: OVERALL weekly, per-subject monthly

A week yields 2–6 questions per subject. A per-subject weekly trend would flip
direction on noise and destroy trust in the whole report. So:

* **Weekly comparisons are aggregate only** (40–60 questions): nights run,
  accuracy across all subjects together, topics that moved up a depth rung.
* **The accuracy row is suppressed unless BOTH weeks have 10+ answered.**
* **Per-subject POSITION** (a stock) is fine at any window — that is what the
  scale bars show. **Per-subject TRENDS** (a flow) wait for a monthly window.
* **Week 1 shows the empty state**, explaining what will appear next Friday. It
  explicitly ignores the pre-go-live beta week: partial, different pipeline,
  comparing against it would manufacture a trend out of nothing.

### Speed appears only when it moved

Fluency (median seconds on correct speed-phase answers) is one of the real
dimensions, but standing furniture that never changes is noise. It renders only
on a shift of 25% or more, and a slowdown is framed as the material getting
harder — the desirable-difficulties finding — never as decline.

### Praise is process-level, never person-level

Hattie & Timperley: feedback about the *person* is the weakest kind. The "say
one thing" script names the MOVE ("you explained why it works, not just what the
answer was"), never the child ("you're clever").

### Next week's plan is mandatory

The feed-forward half ("where to next?") is the part most reports omit. Every
report ends with a consolidated plan: what practice steps up, what comes back
for another look, what eases to maintenance. Closing line makes clear the child
does not have to be told any of it — the quiz just does it.

### Integrity gates the quote

A teach-back that fails the authenticity check (`integrity.py`) is never quoted
and never evidences depth. Its exclusion is disclosed in the reading notes
without accusation. See UNDERSTANDING.md.
