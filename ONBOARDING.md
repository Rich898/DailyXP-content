# ONBOARDING — adding a new player (the front door)

Discovered the hard way on go-live eve (the t1 test seat was the first player to
ever *arrive* rather than be hand-carried): a new player receives the quiz via a
ONE-TIME ACCESS TEXT with their personal URL, then the home-screen icon is the
daily door. This is the complete sequence. Player = kid seat + parent seat.

## The sequence (operator + build-chat, ~20 min)
1. **Roster entry** (`roster.json`, public): `{"code": "<c>", "tag_initial": "<X>",
   "active": true}` — add `"targets_alias": "<other-code>"` only for test players
   riding another student's curriculum. Codes are anonymous by law.
2. **Seed the ledger** (private `work/state.json`): a `students.<c>` block — `ref`,
   `status: "ACTIVE"`, `status_reason`, `confidence_profile: ""`, `topics` (from the
   alias's topic list all-`untested`, or from a fresh Canvas sweep + school report
   for a real student). Commit private.
3. **Stamp the page**: `template_v3.html` with `__STUDENT__` → code and `__NAME__` →
   first name. NEVER commit the stamped page (name law) — hand it to the operator.
4. **Netlify**: new folder containing the page renamed `index.html` → app.netlify.com
   → Add new site → Deploy manually → drag folder → rename site (Site settings →
   Change site name) to something stable, e.g. `xpdaily-<c>`. URL is permanent;
   the pipeline republishes `<c>.json` daily to the same address.
5. **Comms seats**: repo secrets `MOBILE_MESSAGE_TO_<C>` (kid) and
   `MOBILE_MESSAGE_PARENTS_<C>` (comma-separated parents) + the two matching env
   lines in `test-sms.yml`, `kid-nudge.yml`, `evening-soundbyte.yml`. Record the
   seat holders (names, no numbers) in private `COMMS-SEATS.md`.
6. **Warm-up publish (recommended)**: a 3-Q `T-WARMUP`-style set via
   `tools/publish.py` so the page verifiably loads before day 1. Laws: `fresh: true`
   on every Q; subjects/topics OUTSIDE the ledger so playing it moves nothing;
   archive lands in PRIVATE `history/<c>/` (no-repeat memory).
7. **Access text** (the front door): fire `test-sms` at target `<c>` with:
   *"Welcome to XP Daily 👊 Your quiz lives here: <url> — open it, then add it to
   your Home Screen. That icon is your daily door."*
   NOTE: stamped pages carry the player's name baked in — there is NO name prompt.
   (SYSTEM TEST discard rows require a page stamped with that name — operator tool.)
   Desktop-only players (no smartphone): Chrome ⋮ → More tools → Create shortcut
   ("Open as window"), or just bookmark it — same door. Results submit identically.
8. **Verify the loop**: kid adds icon + plays warm-up → fire one evening-soundbyte
   dispatch → parent seat receives the first "done ✅" text. Onboarding complete.
9. **Parent welcome + the LEGEND** (fire once to `parents:<c>`, at onboarding):
   *"XP Daily here — each school night you'll get one line when <name>'s run is
   done: whether he did it, the XP he earned, and a verdict on the night. The
   verdict words are earned, not vibes — the system picks them from how the
   night's set went: 'flew tonight' is a standout, 'good night's work' is
   strong, 'put in a shift' means solid graft in the zone where it works
   hardest, and 'the set bit back' means the quiz played rough and finishing
   was the win. No text just means the run hasn't landed yet."*
   Per policy (REPORTING.md: the daily final form), NO percentages, ratios, or
   running totals appear anywhere — not in the nightly line, not in this
   legend. The verdict words stand on their own.

## Laws + open items
- **The URL is currently the identity.** Anyone holding it can play (and submit) as
  that kid. Acceptable obscurity for family/week-1; the moment a non-family child
  joins, kid codes/auth is a hard gate (with the rest of the privacy work).
- **Open design question (week-1 test decides):** should the daily 4pm nudge carry
  the link, or stay icon-only? Icon-only is cleaner; link-every-text is resilient.
