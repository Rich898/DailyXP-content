// XPDaily — boss-core proof.
// BOSS-CORE is extracted verbatim from the built shell and exercised directly.
// Locks the HARD CONTRACT for the Friday boss:
//   1. HP is a PURE function of the steady records — order-independent, deterministic,
//      and identical whether computed once or repeatedly (display-only, no hidden state).
//   2. The boss is ALWAYS defeatable — no sequence of answers, including all-wrong,
//      pushes HP to a lose-condition. A miss just leaves the boss standing; the finisher
//      (a separate drain-to-0 in the shell) always ends it. No fake jeopardy.
//   3. Repair-flagged hits chip harder than plain hits (the real weak spots hurt more).
//   4. THE LAW — BOSS-CORE source references NO game state (state., score/records writes,
//      T.questionDone, timing). It can only describe HP, never mutate the run.
"use strict";
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");
const m = src.match(/\/\*BOSS-CORE-START\*\/([\s\S]*?)\/\*BOSS-CORE-END\*\//);
if (!m) { console.error("FAIL: boss core not found in built shell"); process.exit(1); }
const bossSource = m[1];
const makeBoss = new Function(bossSource + "; return makeBoss;")();

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

const B = makeBoss();
const steady = (ok, repair) => ({ phase: "steady", ok: ok, repair: !!repair });

console.log("HP is a pure function of records");
{
  const recs = [steady(true), steady(true), steady(false), steady(true, true)];
  const a = B.hpFromRecords(recs), b = B.hpFromRecords(recs);
  check("deterministic (same input -> same HP)", a === b, "hp=" + a);
  const shuffled = [recs[3], recs[0], recs[2], recs[1]];
  check("order-independent", B.hpFromRecords(shuffled) === a, a + " vs " + B.hpFromRecords(shuffled));
  check("starts at full with no records", B.hpFromRecords([]) === B.MAX, "hp=" + B.hpFromRecords([]));
  check("pct is 0-100", B.pct(recs) >= 0 && B.pct(recs) <= 100, "pct=" + B.pct(recs));
}

console.log("landing hits chips the boss; misses do not");
{
  const none = B.hpFromRecords([]);
  const oneHit = B.hpFromRecords([steady(true)]);
  const oneMiss = B.hpFromRecords([steady(false)]);
  check("a landed hit lowers HP", oneHit < none, none + " -> " + oneHit);
  check("a miss leaves HP unchanged (boss survives, no self-damage)", oneMiss === none, "hp=" + oneMiss);
  const plain = B.hpFromRecords([steady(true)]);
  const repair = B.hpFromRecords([steady(true, true)]);
  check("repair-flagged hit chips HARDER than a plain hit", repair < plain, plain + " vs repair " + repair);
  check("a skipped steady does no damage", B.hpFromRecords([{ phase: "steady", ok: true, skipped: true }]) === none);
}

console.log("ALWAYS defeatable — no lose-condition");
{
  check("isDefeatable() is unconditionally true", B.isDefeatable() === true);
  // worst case: every attack missed -> boss at full, but the finisher still ends it.
  const allMiss = B.hpFromRecords([steady(false), steady(false), steady(false), steady(false)]);
  check("all-wrong leaves the boss standing (not a game-over), HP still finite", allMiss === B.MAX && allMiss > 0, "hp=" + allMiss);
  // best case: clean four -> floored above 0 so the teach-back finisher always has the kill shot.
  const cleanFour = B.hpFromRecords([steady(true, true), steady(true), steady(true), steady(true)]);
  check("clean four floors ABOVE zero (finisher does the last of it)", cleanFour >= B.FLOOR && cleanFour > 0, "hp=" + cleanFour + " floor=" + B.FLOOR);
  // exhaustive: no combination of up to 6 steady results can ever hit 0 via answers alone
  let everZero = false;
  for (let n = 0; n <= 6; n++) {
    for (let mask = 0; mask < (1 << n); mask++) {
      const recs = [];
      for (let i = 0; i < n; i++) recs.push(steady(!!(mask & (1 << i)), i % 2 === 0));
      if (B.hpFromRecords(recs) <= 0) everZero = true;
    }
  }
  check("no answer sequence (0-6 steady) ever drops HP to 0 — only the finisher can", !everZero);
}

console.log("themed name");
check("names from the dominant subject", B.nameFor(["Maths", "Maths", "Science"]).length > 0 && B.nameFor(["Maths", "Maths", "Science"]) !== "The Gatekeeper", B.nameFor(["Maths", "Maths", "Science"]));
check("falls back gracefully on unknown/empty", B.nameFor([]) === "The Gatekeeper");

console.log("THE LAW: boss HP cannot touch the run");
check("no 'state.' references in BOSS-CORE", !/\bstate\./.test(bossSource));
check("no score/records writes in BOSS-CORE", !/\b(score|records)\s*[+\-]?=/.test(bossSource));
check("no timing references in BOSS-CORE", !/T\.questionDone|tStart|activeMs/.test(bossSource));

console.log("");
if (fails) { console.error(fails + " FAILURE(S)"); process.exit(1); }
console.log("boss-core: all green");
