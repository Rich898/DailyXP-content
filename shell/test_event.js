// DailyXP — event-core proof.
// The event functions are extracted VERBATIM from the built shell (between the
// EVENT-CORE markers), then driven directly. Locks two things:
//   1. Detection is TAG-ONLY and strict — only a BATTLEGROUND tag lights an event.
//      (Blitz was retired 20 Aug 2026: REVERSED / BLITZ tags now light nothing.)
//   2. THE LAW: events never touch scoring — no *2 in the shell body outside the
//      audited cores. state.score is never multiplied anywhere.
"use strict";
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");
const m = src.match(/\/\*EVENT-CORE-START\*\/([\s\S]*?)\/\*EVENT-CORE-END\*\//);
if (!m) { console.error("FAIL: event core not found in built shell"); process.exit(1); }
const core = new Function(m[1] + "; return {eventModeFor};")();

let fails = 0;
function check(name, ok) {
  console.log((ok ? "  ok   " : "  FAIL ") + name);
  if (!ok) fails++;
}

console.log("detection (tag is the only carrier of truth)");
check("BATTLEGROUND tag -> battleground", core.eventModeFor("H3.5 \u00b7 BATTLEGROUND") === "battleground");
check("lowercase tolerated", core.eventModeFor("h3.5 \u00b7 battleground") === "battleground");
check("REVERSED BLITZ tag -> no event (Blitz retired)", core.eventModeFor("H3.3 \u00b7 REVERSED BLITZ") === "");
check("plain BLITZ tag -> no event (Blitz retired)", core.eventModeFor("H3.3 \u00b7 BLITZ") === "");
check("warm-up tag -> NO event", core.eventModeFor("T-WARMUP2") === "");
check("standard tag -> NO event", core.eventModeFor("H3.1") === "");
check("empty/undefined tag -> NO event", core.eventModeFor(undefined) === "" && core.eventModeFor("") === "");

console.log("THE LAW: no score mutation outside the display block");
const eventBlock = m[0];
// Strip the audited cores before the *2 scan: EVENT-CORE, FX-CORE (particle
// geometry, e.g. Math.PI*2), and X2-CORE (hidden double-XP) each legitimately
// contain *2 and have their own law tests. Any *2 in the REST of the shell
// would be an unaudited score-double.
let outside = src.replace(eventBlock, "");
const fxBlock = outside.match(/\/\*FX-CORE-START\*\/[\s\S]*?\/\*FX-CORE-END\*\//);
if (fxBlock) outside = outside.replace(fxBlock[0], "");
const x2Block = outside.match(/\/\*X2-CORE-START\*\/[\s\S]*?\/\*X2-CORE-END\*\//);
if (x2Block) outside = outside.replace(x2Block[0], "");   // hidden double-XP: audited by test_x2.js
// geometry is never a score-double: strip full-turn angle math (e.g. Math.PI*2 in confetti bursts)
outside = outside.replace(/Math\.PI\s*\*\s*\d+/g, "");
check("no *2 arithmetic in the main shell body (outside the audited cores)",
  !/\*\s*2\b/.test(outside.replace(/\/\*[\s\S]*?\*\//g, "")));
check("state.score is never multiplied", !/state\.score\s*\*/.test(src) && !/state\.score\s*\*=/.test(src));
check("MAX_SCORE formula untouched by events", !/MAX_SCORE[^\n]*EVENT|EVENT[^\n]*MAX_SCORE/.test(src));

console.log("");
if (fails) { console.error(fails + " FAILURE(S)"); process.exit(1); }
console.log("event-core: all green");
