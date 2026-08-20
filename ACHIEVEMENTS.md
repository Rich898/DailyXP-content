# Achievements — badging the ledger

Kids love badging themselves — XP, streaks, levels, achievements. The advantage this system
has over a straight game: the ledger already records mastery, streaks, confidence and speed, so
**an achievement is a read of the ledger, not a bolt-on.** Deterministic code, no AI, no new
state. A badge cannot be earned without the underlying learning — the reward is *load-bearing*:
the thing that feels good to unlock IS the thing we want them to do.

## Principles
- **Read-only over `state.json` + `runs.json`.** An achievement observes state; it never invents
  it. Same law as `LEDGER-RULES.md` — the ledger is the brain; badges are a view of it.
- **Compete with your past self, never each other.** No sibling comparison, no leaderboards
  between the boys. Every badge is mastery- or personal-best-based. (Protects both engagement —
  the "loser" never disengages — and the safeguarding wall.)
- **Honest by construction.** Because badges read real mastery/confidence/pace, the
  pedagogically-valuable behaviours and the rewarded behaviours are identical: fixing a weakness,
  slowing down, genuine (not illusory) confidence.
- **Kid-facing only.** Achievements surface in-quiz and on the kid dashboard. Parents get
  *insight*, never the badge count — a kid's achievements are never turned into pressure or
  ammunition (`REPORTING.md` no-ammunition rule).
- **Rarity = effort, not luck.** Tiers come from doing more of the real thing (longer streaks,
  full clears), never from a lucky run.

## The starter set (v1 — 12 badges, four families)
Trigger = the exact ledger/run condition. Type = one-time (first ever) / repeatable (per topic,
per run, or per week). ⭐ = directly rewards a core anti-fluency-illusion behaviour.

### Mastery — you learned something
| Badge | Unlocks when | Type |
|---|---|---|
| **First Blood** | first quiz ever completed | one-time |
| **Locked It** | a topic reaches `solid` | per topic |
| **Comeback** ⭐ | a topic exits REPAIR → `developing` | per topic |
| **Full Clear** | every live topic in a subject is `solid` | per subject |
| **Untouchable** | a `solid` topic holds across 3 spaced maintenance checks | per topic |

### Consistency — you showed up
| Badge | Unlocks when | Type |
|---|---|---|
| **Streak** (bronze/silver/gold) | 3 / 7 / 14 consecutive school-days completed | tiered |
| **Perfect Week** | all 5 school-days in one week | per week |

### Craft — you did it *well* (the clever ones)
| Badge | Unlocks when | Type |
|---|---|---|
| **Calm Hands** ⭐ | a calm, confident, correct answer on a topic you used to rush (prior `last_result` = fast-wrong / rush-profiled) | per topic |
| **Clean Run** | a whole quiz with zero lucky guesses and zero confident-wrongs | per run |
| **Sure Shot** ⭐ | a "Sure" that's actually right on a REPAIR topic (the confirm) | per topic |

### Event — you rose to the occasion
| Badge | Unlocks when | Type |
|---|---|---|
| **Full Claim** | claim the whole Friday Battleground — 100% of the territory (every zone) | per Friday |
| **Personal Best** | a night's XP above your own previous best, any night (baseline seeded from history at introduction — 20 Aug 2026 — so no backdated flood) | repeatable |

> **Changelog (20 Aug 2026):** *Boss Slayer* → **Full Claim** when Friday became Battleground
> (no win/lose — the badge rewards 100% claimed, matching the shell's own tier language).
> *Blitz Master* → **Personal Best** when the Blitz event was retired — same essence
> (beat your own XP record), no longer tied to a night type.

The payoff: **Comeback, Calm Hands and Sure Shot reward exactly the behaviours the whole system
is built to produce** — fixing weaknesses, slowing down, and real rather than illusory
confidence. A kid chasing badges is chasing the pedagogy.

## How it plugs in (to build)
- `achievements.py` — deterministic, idempotent, runs right after the state-writer. Reads
  `state.json` + `runs.json`, diffs against a private per-kid `achievements_earned.json`, emits
  any newly-unlocked badges for that run. No AI. Same shape as the state-writer.
- Newly-unlocked badges flow to two places: **(a)** the in-quiz end screen (the immediate
  dopamine moment) and **(b)** the kid's Friday dashboard.
- The private `achievements_earned.json` is the badge ledger (carries the kid's history →
  private repo). Public code stays name/score-free.

## Deliberately NOT in v1
- Sibling comparison / global leaderboards — never.
- Time-of-day or volume-farming badges — would reward grinding, not learning.
- Cosmetic-only badges with no ledger basis — would break the honesty principle. Cosmetics come
  through Seasons instead (`SEASONS.md`), earned by real progress.
