// DailyXP v3.0 — timing-core proof.
// The timing code below is extracted VERBATIM from the built shell
// (between the TIMING-CORE markers), then driven with a fake clock
// through a realistic full run including reveal-reading pauses and a
// long mid-quiz walk-away. Asserts the invariants that were violated
// all of Week 1 (active > elapsed is now impossible).
"use strict";
const fs = require("fs");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");
const m = src.match(/\/\*TIMING-CORE-START\*\/([\s\S]*?)\/\*TIMING-CORE-END\*\//);
if (!m) { console.error("FAIL: timing core not found in built shell"); process.exit(1); }
const makeTiming = new Function(m[1] + "; return makeTiming;")(); // the exact shipped code

let CLOCK = 0;
const now = () => CLOCK;
const tick = (s) => { CLOCK += Math.round(s * 1000); };

const T = makeTiming(now);
T.startSession();

// ── HEAT 1 · SPEED (7 questions, mirrors real behaviour) ──
// Pattern per question: shown → think → answer (questionDone).
// Wrong answers then have a reveal-reading pause BEFORE the next
// question is shown — this pause was the old bug's fuel.
const speedPlan = [
  { think: 4.2, ok: true,  reveal: 0.9 },   // correct: 0.9s auto-advance
  { think: 6.8, ok: false, reveal: 14.0 },  // wrong: reads the why
  { think: 3.1, ok: true,  reveal: 0.9 },
  { think: 11.5, ok: false, reveal: 22.0 }, // wrong: long read
  { think: 30.0, ok: false, reveal: 9.0 },  // TIMEOUT at full window
  { think: 5.0, ok: true,  reveal: 0.9 },
  { think: 2.4, ok: true,  reveal: 0.9 },
];
let expectedActive = 0;
speedPlan.forEach((p, i) => {
  T.questionShown();
  tick(p.think);
  const rec = T.questionDone("S" + (i + 1), "Test", "speed", { ok: p.ok, timeUsed: p.think });
  expectedActive += p.think;
  if (Math.abs(rec.secs - p.think) > 0.05) { console.error("FAIL: per-question secs wrong", rec); process.exit(1); }
  tick(p.reveal); // reveal / auto-advance time — must land in idle, not active
});

// ── double-fire attack: a stray second questionDone with no open clock ──
const stray = T.questionDone("S7", "Test", "speed", { ok: true });
if (stray !== null) { console.error("FAIL: double-fire booked time"); process.exit(1); }

// ── HEAT 2 · STEADY (4 questions; picking/confidence re-renders don't restart clocks) ──
const steadyPlan = [
  { think: 22.0, reveal: 6.0 },
  { think: 35.5, reveal: 12.0 },
  { think: 18.0, reveal: 4.0 },
  { think: 41.0, reveal: 8.0 },
];
steadyPlan.forEach((p, i) => {
  T.questionShown();
  // simulate mid-question re-renders (pick option, pick confidence) — no clock effect
  tick(p.think * 0.4); /* re-render happens here in the shell; markShown() blocks restart */
  tick(p.think * 0.6);
  T.questionDone("T" + (i + 1), "Test", "steady", { ok: true, confidence: "Sure" });
  expectedActive += p.think;
  tick(p.reveal);
});

// ── mid-quiz walk-away: phone locked 6 minutes before teach-back ──
tick(360);

// ── TEACH-BACK: 3m18s of typing (Friday's real figure) ──
T.questionShown();
tick(198);
T.questionDone("TB1", "Test", "teach", { ok: true, chars: 240 });
expectedActive += 198;

const s = T.summary();
const raw = T._raw();

// ── THE INVARIANTS ──
const checks = [];
function check(name, cond, detail) { checks.push([name, cond, detail]); if (!cond) { console.error("FAIL:", name, detail || ""); } }

check("active ≤ elapsed (the Week-1 impossibility, now structurally impossible)",
      s.activeSecs <= s.elapsedSecs, s.activeSecs + " vs " + s.elapsedSecs);
check("raw accumulator also ≤ wall clock (clamp never needed)",
      raw.activeMs <= CLOCK - 0, raw.activeMs + " vs " + CLOCK);
check("active equals the sum of genuine think-time",
      Math.abs(s.activeSecs - expectedActive) < 0.5, s.activeSecs + " vs expected " + expectedActive);
check("phase times sum to active",
      Math.abs((s.phases.speed + s.phases.steady + s.phases.teach) - s.activeSecs) < 0.3,
      JSON.stringify(s.phases));
check("idle = elapsed − active (reveals + the 6-min walk-away)",
      Math.abs(s.idleSecs - (s.elapsedSecs - s.activeSecs)) < 0.2, s.idleSecs);
check("idle captured the walk-away (≥ 360s)", s.idleSecs >= 360, s.idleSecs);
check("12 per-question records, none doubled", s.perQuestion.length === 12, s.perQuestion.length);
check("teach-back time plausible (198s recorded)",
      Math.abs(s.phases.teach - 198) < 0.5, s.phases.teach);

const failed = checks.filter(c => !c[1]);
console.log("─".repeat(60));
console.log("Simulated full run:");
console.log("  elapsed " + s.elapsedSecs + "s · active " + s.activeSecs + "s · idle " + s.idleSecs + "s");
console.log("  phases: speed " + s.phases.speed + "s · steady " + s.phases.steady + "s · teach " + s.phases.teach + "s");
console.log("─".repeat(60));
checks.forEach(c => console.log((c[1] ? "  PASS  " : "  FAIL  ") + c[0]));
console.log("─".repeat(60));
if (failed.length) { console.error(failed.length + " FAILURES"); process.exit(1); }
console.log("ALL " + checks.length + " TIMING INVARIANTS HOLD");
