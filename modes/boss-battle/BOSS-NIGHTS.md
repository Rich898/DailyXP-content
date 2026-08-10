# Boss Nights — a future event mode (NOT Friday)

**Status:** preserved / not live. Working code frozen in this folder. Not wired into any
schedule. This is a *future season* mode, kept here as a documented starting point.

## What it is
A **win/lose** quiz night. Unlike Friday Battleground (continuous — you claim a % of ground,
never lose), a Boss Night has a real fail state: you either **beat the boss or you don't**.
You still earn XP for playing either way, but the outcome is binary, and that's the point —
it makes the stat sheet real.

The boss is built from the student's own ledger weaknesses (misses as attacks). The steady
slots are a challenge format (the frozen build uses **spot-the-lie**; a future Boss Night
could use any format, including the harder **spot-the-flaw** — see "Format" below). An HP bar
drains as you land hits; the teach-back is the finishing move.

## The governing principle (why this can't be Friday)
**In a game, losing is fun; in a study tool, losing is discouragement.**

A boss targets a kid's *weakest* topics. A losable boss on your worst subjects, as the
*single verdict on your week*, punishes exactly the kid who needs encouragement — at the
emotional high point of the week. That is why Friday is **Battleground** (a confidence builder,
no lose-state) and never a boss.

Win/lose only works **emotionally as a CAMPAIGN, not a single verdict.** "You lost tonight's
boss" is fine *if* tomorrow/next week is another shot and the thing that matters is the
**season record**. So Boss Nights are designed to run as a *streak of nights over a period*
(a few weeks, or a beta phase), where you win some and lose some, and the arc is:

> **Season Boss record: won 3 / lost 2 → new target next season.**

That record — not any single night — is the motivator. Losing a night is a plot beat, not a
grade on the child.

## When to use it (future)
- **Seasonal / occasional**, never the weekly Friday slot.
- A dedicated **Boss Season** (e.g. run Boss Nights weekly for a 4–6 week block), or
  occasional special nights inside a normal season.
- Good for a **beta cohort** that wants more stakes/competition once confidence is established.
- Explicitly *after* the confidence-building base rhythm is in place — bosses raise stakes on
  top of security, they don't replace it.

## What it unlocks (the reason to build it later)
Win/lose generates a richer stat/achievement surface than a no-lose mode can:
- **Boss record** (won/lost) per season → the season-wrap headline + next-season target.
- Boss-specific **badges/achievements**: first boss win, a win streak, a comeback win after
  losses, a flawless win, beating a boss on a subject you'd lost to before.
- **Stats**: win rate, longest win streak, nemesis subject (the one that keeps beating you),
  redemption (first win over a former nemesis).
- A season **narrative**: the record gives every season a scoreboard and a target to chase.

## Format (a call for whoever builds this)
The frozen build's boss uses **spot-the-lie** (four statements, one false) — chosen when the
boss was still the Friday event and needed to be gentle. A losable, higher-stakes Boss Night
is a natural home for a **harder** format:
- **spot-the-flaw** (find the wrong step in a worked solution) — more demanding, was cut from
  Friday for being too heavy, but well-suited to a stakes mode where difficulty is the point.
- or **any** of the Battleground formats (true/false, MC, sum-as-MC), mixed.

Decide format when the mode is revived; the shell mechanic (HP drain, win/lose) is
format-agnostic.

## What's frozen here
- `boss-shell.html` — the complete, working boss shell as it stood at commit `e4ba564`
  (HP-drain BOSS-CORE, boss banner + themed name, spot-the-lie fight, finishing-move
  teach-back, victory screen, Boss Slayer badge). Playable as-is.
- `test_boss.js` — the boss-core proof (HP is a pure function of records; exhaustive test that
  in *this* frozen build the boss can't be zeroed except by the finisher). **Note:** that
  no-lose property was the *Friday* design. A real Boss Night must ADD a genuine lose-state
  (e.g. boss wins if HP not brought below a threshold, or a hit/miss budget) — that's the
  main code change when reviving, and the test would be rewritten to prove the *win/lose*
  logic instead.

## To revive (rough sketch, not now)
1. Add a genuine **lose-condition** to BOSS-CORE (the frozen one is deliberately unloseable).
2. Add a **boss ledger** (per-season won/lost record) in the private repo.
3. Add Boss-specific badges/stats to `achievements.py`.
4. Add a **Boss Season** event type to `SEASONS.md` scheduling (distinct from Friday
   Battleground), and a directive + tag (e.g. `· BOSS NIGHT`).
5. Season-wrap surfaces the record + sets next season's target.

Keep it **off Friday**. Friday stays Battleground.
