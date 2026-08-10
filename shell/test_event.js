// DailyXP v3.0.5 — event-core proof.
// The event functions are extracted VERBATIM from the built shell (between the
// EVENT-CORE markers), then driven directly. Locks three things:
//   1. Detection is TAG-ONLY and strict — a warm-up played on a Wednesday can
//      never light the ×2 promise. REVERSED outranks BLITZ; BLITZ substring
//      still detects inside "REVERSED BLITZ" tags.
//   2. blitzTally is display arithmetic only.
//   3. THE LAW: events never touch scoring — the only *2 in the whole shell
//      lives inside the EVENT-CORE display block. state.score is never
//      multiplied anywhere.
"use strict";
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/roshan/index.html", "utf8");
const m = src.match(/\/\*EVENT-CORE-START\*\/([\s\S]*?)\/\*EVENT-CORE-END\*\//);
if (!m) { console.error("FAIL: event core not found in built shell"); process.exit(1); }
const core = new Function(m[1] + "; return {eventModeFor, isBlitz, blitzTally};")();

let fails = 0;
function check(name, ok) {
  console.log((ok ? "  ok   " : "  FAIL ") + name);
  if (!ok) fails++;
}

console.log("detection (tag is the only carrier of truth)");
check("REVERSED BLITZ tag -> reversed-blitz", core.eventModeFor("H3.3 \u00b7 REVERSED BLITZ") === "reversed-blitz");
check("plain BLITZ tag -> blitz", core.eventModeFor("H3.3 \u00b7 BLITZ") === "blitz");
check("lowercase tolerated", core.eventModeFor("h3.3 \u00b7 reversed blitz") === "reversed-blitz");
check("BOSS tag -> boss", core.eventModeFor("H3.5 \u00b7 BOSS") === "boss");
check("warm-up tag -> NO event (the false-promise guard)", core.eventModeFor("T-WARMUP2") === "");
check("standard tag -> NO event", core.eventModeFor("H3.1") === "");
check("empty/undefined tag -> NO event", core.eventModeFor(undefined) === "" && core.eventModeFor("") === "");

console.log("isBlitz mapping");
check("blitz is blitz", core.isBlitz("blitz") === true);
check("reversed-blitz is blitz", core.isBlitz("reversed-blitz") === true);
check("boss is not blitz", core.isBlitz("boss") === false);
check("no event is not blitz", core.isBlitz("") === false);

console.log("tally arithmetic (display only)");
check("2140 -> 4,280", core.blitzTally(2140) === (4280).toLocaleString());
check("0 -> 0", core.blitzTally(0) === "0");
check("null-safe", core.blitzTally(null) === "0");

console.log("THE LAW: no score mutation outside the display block");
const eventBlock = m[0];
const outside = src.replace(eventBlock, "");
check("no *2 arithmetic anywhere outside EVENT-CORE",
  !/\*\s*2\b/.test(outside.replace(/\/\*[\s\S]*?\*\//g, "")));
check("state.score is never multiplied", !/state\.score\s*\*/.test(src) && !/state\.score\s*\*=/.test(src));
check("MAX_SCORE formula untouched by events", !/MAX_SCORE[^\n]*EVENT|EVENT[^\n]*MAX_SCORE/.test(src));

console.log("");
if (fails) { console.error(fails + " FAILURE(S)"); process.exit(1); }
console.log("event-core: all green");
