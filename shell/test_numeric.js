// XPDaily v3.1 — typed-numeric (speed) proof.
// Part A: NUMERIC-CORE extracted from the built shell and exercised directly — locks the
//   moderate-strictness contract (bare number OR number+correct unit; wrong unit ≠ credit;
//   unicode powers + spacing normalised).
// Part B: a full jsdom run over a numeric fixture — proves the shell RENDERS a keypad (not
//   options), SCORES typed answers, carries type/picked in the record, keeps the timing
//   invariant, and that the universal skip stamps the Q's fresh flag (soft-miss hook).
"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

// ── Part A: unit-test the matcher ─────────────────────────────────────────────
const m = src.match(/\/\*NUMERIC-CORE-START\*\/([\s\S]*?)\/\*NUMERIC-CORE-END\*\//);
if (!m) { console.error("FAIL: NUMERIC-CORE not found in built shell"); process.exit(1); }
const numericOK = new Function(m[1] + "; return numericOK;")();

console.log("numeric matcher (moderate strictness):");
check("exact bare number", numericOK("56", { answer: "56" }) === true);
check("bare number when answer carries a unit", numericOK("30", { answer: "30 cm²", accept: ["30 cm2"] }) === true);
check("number + correct unit (unicode ²)", numericOK("30 cm²", { answer: "30 cm²", accept: ["30 cm2"] }) === true);
check("number + correct unit (ascii, no space)", numericOK("30cm2", { answer: "30 cm²" }) === true);
check("wrong unit alone is NOT full credit", numericOK("30 m2", { answer: "30 cm²" }) === false);
check("thousands comma tolerated", numericOK("1,024", { answer: "1024" }) === true);
check("decimal exact", numericOK("3.14", { answer: "3.14" }) === true);
check("blank is wrong", numericOK("", { answer: "5" }) === false);
check("null is wrong", numericOK(null, { answer: "5" }) === false);
check("plain wrong number", numericOK("41", { answer: "42" }) === false);

// ── Part B: full run over a numeric fixture ───────────────────────────────────
const FIX = {
  student: "y9", date: "2026-08-02", day: "TEST", dateLabel: "SUN 2 AUG 2026",
  tag: "SYSTEM TEST", title: "numeric test",
  questions: [
    { id: "N1", phase: "speed", subject: "Maths", type: "numeric", prompt: "What is 7 × 8?",
      answer: "56", accept: ["56"], why: "56 — seven eights.", fresh: true },
    { id: "N2", phase: "speed", subject: "Maths", type: "numeric", prompt: "Area of a 6×5 rectangle?",
      answer: "30 cm²", accept: ["30", "30 cm2", "30cm²"], why: "30 cm² — six times five.", fresh: true },
    { id: "N3", phase: "speed", subject: "Maths", type: "numeric", prompt: "What is 12 × 12?",
      answer: "144", accept: ["144"], why: "144 — a dozen dozen.", fresh: true },
    { id: "N4", phase: "speed", subject: "Maths", type: "numeric", prompt: "A not-yet-taught one?",
      answer: "99", accept: ["99"], why: "99.", fresh: true },
    { id: "N5", phase: "speed", subject: "Maths", type: "numeric", prompt: "An established topic?",
      answer: "7", accept: ["7"], why: "7.", fresh: false },
    { id: "T1", phase: "steady", subject: "Gaming", prompt: "In games, what does XP stand for?",
      options: ["Extra Power", "Experience Points", "Expert Play", "Exit Portal"], answer: "Experience Points",
      why: "Experience Points.", fresh: true },
    { id: "SN1", phase: "steady", subject: "Maths", type: "numeric", prompt: "Area of a 5 × 6 rectangle?",
      answer: "30 cm²", accept: ["30", "30 cm2", "30cm²"], why: "30 cm² — five sixes.", fresh: true },
    { id: "TB", phase: "teach", subject: "Science", prompt: "SYSTEM TEST: type any 80+ character explanation." }
  ]
};

let webhookBody = null;
const dom = new JSDOM(src, {
  url: "https://xpdaily-test.netlify.test/", runScripts: "dangerously", pretendToBeVisual: true,
  beforeParse(window) {
    window.fetch = function (url, opts) {
      url = String(url);
      if (url.indexOf("raw.githubusercontent.com") !== -1) return Promise.resolve({ ok: true, json: () => Promise.resolve(FIX) });
      if (url.indexOf("script.google.com") !== -1) { webhookBody = opts && opts.body; return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }); }
      return Promise.reject(new Error("unexpected fetch: " + url));
    };
  },
});
const { window } = dom; const { document } = window;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const btns = () => Array.from(document.querySelectorAll("button"));
function clickText(t) { const b = btns().find((x) => x.textContent.indexOf(t) !== -1 && !x.disabled); if (!b) throw new Error("no button: " + t + " | have: " + btns().map((x) => x.textContent.trim().slice(0, 24)).join(" / ")); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); }
function typeAnswer(v) { const i = document.getElementById("nin"); if (!i) throw new Error("no numeric input on stage"); i.value = v; i.dispatchEvent(new window.Event("input", { bubbles: true })); }
function stage() { return document.getElementById("stage").textContent; }

(async () => {
  await sleep(80);
  console.log("full numeric run:");
  clickText("Drop in"); await sleep(30);

  // N1 — keypad rendered, NOT options; type correct.
  check("N1 renders a keypad, not options", !!document.getElementById("nin") && document.querySelectorAll(".opt").length === 0);
  check("N1 prompt shown", stage().indexOf("7 × 8") !== -1);
  check("N1 Submit disabled until typed", document.getElementById("ninsub").disabled === true);
  typeAnswer("56");
  check("N1 Submit enables once typed", document.getElementById("ninsub").disabled === false);
  clickText("Submit"); await sleep(60);
  check("N1 correct → banked", stage().indexOf("Got it") !== -1);
  await sleep(950);

  // N2 — bare/unit answer; type with unicode unit.
  check("N2 up", stage().indexOf("6×5") !== -1);
  typeAnswer("30 cm²"); clickText("Submit"); await sleep(1000);

  // N3 — type WRONG → reveal shows the answer.
  check("N3 up", stage().indexOf("12 × 12") !== -1);
  typeAnswer("99"); clickText("Submit"); await sleep(60);
  check("N3 wrong → reveal shows the answer", stage().indexOf("The answer: 144") !== -1);
  clickText("Got it"); await sleep(60);

  // N4 — fresh:true → benign skip ("haven't covered this yet").
  check("N4 up", stage().indexOf("not-yet-taught") !== -1);
  clickText("haven't covered this yet"); await sleep(760);

  // N5 — fresh:false → plain skip ("skip this one").
  check("N5 up", stage().indexOf("established topic") !== -1);
  clickText("skip this one"); await sleep(760);

  // steady MC (T1) → then steady NUMERIC (SN1) → teach → finish + submit.
  clickText("Experience Points"); await sleep(40); clickText("Sure"); await sleep(40); clickText("Lock it in"); await sleep(40); clickText("Next"); await sleep(30);

  // SN1 — numeric steady. Tap confidence BEFORE typing to prove the typed handler enables Lock.
  check("SN1 renders a keypad in steady", !!document.getElementById("nin") && document.querySelectorAll(".opt").length === 0);
  clickText("Sure"); await sleep(30);
  check("SN1 Lock disabled with confidence but no value", document.getElementById("locksteady").disabled === true);
  typeAnswer("30"); await sleep(20);
  check("SN1 Lock enables once typed (handler toggled it)", document.getElementById("locksteady").disabled === false);
  clickText("Lock it in"); await sleep(40);
  check("SN1 bare number vs unit answer → reveal shows points, not 'Not quite'", stage().indexOf("250") !== -1 && stage().indexOf("Not quite") === -1, stage().replace(/\s+/g, " ").slice(0, 80));
  clickText("Next"); await sleep(30);

  const tb = document.getElementById("tb"); tb.value = "Respiration releases energy from glucose in every living cell, not only in plants, which is why all organisms need it."; tb.dispatchEvent(new window.Event("input", { bubbles: true })); await sleep(60);
  clickText("Send it"); await sleep(180);

  check("run completed (done screen)", stage().indexOf("FULL TIME") !== -1);
  const p = JSON.parse(webhookBody);
  const rec = {}; p.records.forEach((r) => { rec[r.id] = r; });

  check("N1 record: numeric, picked 56, ok", rec.N1.type === "numeric" && rec.N1.picked === "56" && rec.N1.ok === true, JSON.stringify(rec.N1));
  check("N2 record: unicode unit typed → ok", rec.N2.type === "numeric" && rec.N2.ok === true, JSON.stringify(rec.N2));
  check("N3 record: wrong typed value, ok=false", rec.N3.type === "numeric" && rec.N3.picked === "99" && rec.N3.ok === false, JSON.stringify(rec.N3));
  check("N4 record: benign skip carries fresh:true", rec.N4.skipped === true && rec.N4.fresh === true, JSON.stringify(rec.N4));
  check("N5 record: soft-miss skip carries fresh:false", rec.N5.skipped === true && rec.N5.fresh === false, JSON.stringify(rec.N5));
  check("SN1 record: steady numeric, picked 30, ok, confidence Sure", rec.SN1.type === "numeric" && rec.SN1.picked === "30" && rec.SN1.ok === true && rec.SN1.confidence === "Sure", JSON.stringify(rec.SN1));
  check("timing invariant: active ≤ elapsed", p.timing.activeSecs <= p.timing.elapsedSecs, p.timing.activeSecs + " vs " + p.timing.elapsedSecs);
  check("per-question timing recorded for all 8", p.timing.perQuestion.length === 8, String(p.timing.perQuestion.length));

  console.log("─".repeat(60));
  if (fails) { console.error(fails + " FAILURES"); process.exit(1); }
  console.log("TYPED-NUMERIC: ALL CHECKS PASS");
  process.exit(0);
})().catch((e) => { console.error("TEST CRASHED:", e.message); process.exit(1); });
