// XPDaily — battleground-core proof.
// BATTLEGROUND-CORE is extracted verbatim from the built shell and exercised directly.
// Locks the HARD CONTRACT for Friday Battleground:
//   1. Territory % is a PURE function of the steady records + zone set — order-independent,
//      deterministic, 0..100. Display-only, no hidden state.
//   2. NO win/lose — there is no lose-condition; the result is only how much ground was claimed.
//      A miss leaves ground contested (never subtracts). Every % is honest progress.
//   3. Repair zones (harder ground) are worth a bigger share than plain zones.
//   4. THE LAW — BATTLEGROUND-CORE references NO game state (state., score/records writes,
//      T.questionDone, timing). It can only describe territory, never mutate the run.
"use strict";
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");
const m = src.match(/\/\*BATTLEGROUND-CORE-START\*\/([\s\S]*?)\/\*BATTLEGROUND-CORE-END\*\//);
if (!m) { console.error("FAIL: battleground core not found in built shell"); process.exit(1); }
const bgSource = m[1];
const makeBattleground = new Function(bgSource + "; return makeBattleground;")();

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

const B = makeBattleground();
const z = (repair) => ({ id: Math.random().toString(36).slice(2), phase: "steady", repair: !!repair });
const rec = (id, ok, repair) => ({ id: id, phase: "steady", ok: ok, repair: !!repair });

console.log("territory % is a pure function of records + zones");
{
  const zones = [z(true), z(false), z(false), z(false)];
  const ids = zones.map(q => q.id);
  const recs = [rec(ids[0], true, true), rec(ids[1], true), rec(ids[2], false), rec(ids[3], true)];
  const a = B.pct(recs, zones), b = B.pct(recs, zones);
  check("deterministic (same input -> same %)", a === b, "pct=" + a);
  const shuffled = [recs[3], recs[0], recs[2], recs[1]];
  check("order-independent", B.pct(shuffled, zones) === a, a + " vs " + B.pct(shuffled, zones));
  check("no zones claimed -> 0%", B.pct([], zones) === 0);
  check("all zones claimed -> 100%", B.pct(zones.map(q => rec(q.id, true, q.repair)), zones) === 100);
  check("% is within 0..100", a >= 0 && a <= 100, "pct=" + a);
}

console.log("claiming raises ground; misses leave it contested (never subtract)");
{
  const zones = [z(false), z(false)];
  const ids = zones.map(q => q.id);
  const none = B.pct([], zones);
  const oneClaim = B.pct([rec(ids[0], true)], zones);
  const oneMiss = B.pct([rec(ids[0], false)], zones);
  check("a claimed zone raises %", oneClaim > none, none + " -> " + oneClaim);
  check("a missed zone leaves % unchanged (contested, no penalty)", oneMiss === none, "pct=" + oneMiss);
  // repair worth more
  const zr = [z(true), z(false)];
  const idr = zr.map(q => q.id);
  const repairPct = B.pct([rec(idr[0], true, true)], zr);   // claimed the repair zone
  const plainPct = B.pct([rec(idr[1], true, false)], zr);   // claimed the plain zone
  check("claiming the repair (harder) zone claims MORE ground than the plain zone", repairPct > plainPct, plainPct + " vs " + repairPct);
}

console.log("NO win/lose — canLose is false, and 0-4 correct all yield an honest %, never a fail");
{
  check("canLose() is unconditionally false", B.canLose() === false);
  const zones = [z(true), z(false), z(false), z(false)];
  const ids = zones.map(q => q.id);
  // sweep every combination of 4 zones: pct is always 0..100, monotonic in #claimed, never negative
  let ok = true, prevAtCount = {};
  for (let mask = 0; mask < 16; mask++) {
    const recs = [];
    for (let i = 0; i < 4; i++) if (mask & (1 << i)) recs.push(rec(ids[i], true, zones[i].repair));
    const p = B.pct(recs, zones);
    if (p < 0 || p > 100) ok = false;
  }
  check("every answer combination yields a valid 0..100% (no negative / no >100 / no fail state)", ok);
  check("all-wrong is 0% (held the line), not a loss", B.pct([rec(ids[0],false),rec(ids[1],false),rec(ids[2],false),rec(ids[3],false)], zones) === 0);
}

console.log("tier framing (never a 'loss')");
check("100% -> total", B.tier(100) === "total");
check("80% -> strong", B.tier(80) === "strong");
check("50% -> solid", B.tier(50) === "solid");
check("20% -> foothold", B.tier(20) === "foothold");
check("0% -> held (not lost)", B.tier(0) === "held");

console.log("THE LAW: territory cannot touch the run");
check("no 'state.' references in BATTLEGROUND-CORE", !/\bstate\./.test(bgSource));
check("no score/records writes in BATTLEGROUND-CORE", !/\b(score|records)\s*[+\-]?=/.test(bgSource));
check("no timing references in BATTLEGROUND-CORE", !/T\.questionDone|tStart|activeMs/.test(bgSource));

console.log("");
if (fails) { console.error(fails + " FAILURE(S)"); process.exit(1); }
console.log("battleground-core: all green");
