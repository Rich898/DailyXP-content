// XPDaily v3.1 — short-text + cloze (steady) proof.
// Part A: TEXT-CORE extracted and exercised directly — case/punctuation/spacing tolerance,
//   authored synonyms via `accept`, no fuzzy false-positives.
// Part B: a full jsdom run with a short-text and a cloze steady question — proves the shell
//   renders a WORD input (left-aligned, not options), scores it, and carries type/picked.
"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

// ── Part A ────────────────────────────────────────────────────────────────────
const m = src.match(/\/\*TEXT-CORE-START\*\/([\s\S]*?)\/\*TEXT-CORE-END\*\//);
if (!m) { console.error("FAIL: TEXT-CORE not found in built shell"); process.exit(1); }
const textOK = new Function(m[1] + "; return textOK;")();

console.log("text matcher (looser):");
check("exact", textOK("War Guilt Clause", { answer: "War Guilt Clause" }) === true);
check("case-insensitive", textOK("war guilt clause", { answer: "War Guilt Clause" }) === true);
check("authored synonym via accept", textOK("guilt clause", { answer: "War Guilt Clause", accept: ["war guilt", "guilt clause"] }) === true);
check("punctuation ignored", textOK("war-guilt, clause.", { answer: "war guilt clause" }) === true);
check("extra spacing ignored", textOK("  war   guilt  clause ", { answer: "war guilt clause" }) === true);
check("wrong answer rejected", textOK("versailles", { answer: "war guilt clause" }) === false);
check("no fuzzy false-positive (near miss rejected)", textOK("war guilt claus", { answer: "war guilt clause" }) === false);
check("blank rejected", textOK("", { answer: "x" }) === false);

// ── Part B ────────────────────────────────────────────────────────────────────
const FIX = {
  student: "y9", date: "2026-08-02", day: "TEST", dateLabel: "SUN 2 AUG 2026",
  tag: "SYSTEM TEST", title: "text test",
  questions: [
    { id: "S1", phase: "speed", subject: "Maths", prompt: "What is 2 + 2?",
      options: ["3", "4", "5", "6"], answer: "4", why: "It is four.", fresh: true },
    { id: "TX1", phase: "steady", subject: "History", type: "text", prompt: "Name the clause blaming Germany for WWI.",
      answer: "War Guilt Clause", accept: ["war guilt", "guilt clause"], why: "The War Guilt Clause (Article 231).", fresh: true },
    { id: "CZ1", phase: "steady", subject: "History", type: "cloze", prompt: "The Treaty of ______ was signed in 1919.",
      answer: "Versailles", accept: ["versaille"], why: "Versailles.", fresh: true },
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
function clickText(t) { const b = btns().find((x) => x.textContent.indexOf(t) !== -1 && !x.disabled); if (!b) throw new Error("no button: " + t); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); }
function clickOpt(v) { const b = btns().find((x) => x.classList.contains("opt") && x.getAttribute("data-v") === v); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); }
function typeAnswer(v) { const i = document.getElementById("nin"); if (!i) throw new Error("no word input on stage"); i.value = v; i.dispatchEvent(new window.Event("input", { bubbles: true })); }
function stage() { return document.getElementById("stage").textContent; }

(async () => {
  await sleep(80);
  console.log("full text/cloze run:");
  clickText("Drop in"); await sleep(30);
  clickOpt("4"); await sleep(950);            // speed MC done

  // TX1 — short-text
  const inp = document.getElementById("nin");
  check("TX1 renders a word input (not options)", !!inp && document.querySelectorAll(".opt").length === 0);
  check("TX1 input is left-aligned text style", !!inp && inp.className.indexOf("ninput-text") !== -1, inp && inp.className);
  typeAnswer("guilt clause"); await sleep(20); clickText("Sure"); await sleep(20); clickText("Lock it in"); await sleep(40);
  check("TX1 correct via accept synonym → reveal shows points, not 'Not quite'", stage().indexOf("250") !== -1 && stage().indexOf("Not quite") === -1, stage().replace(/\s+/g, " ").slice(0, 80));
  clickText("Next"); await sleep(30);

  // CZ1 — cloze (blank in the prompt), same engine
  check("CZ1 shows the blanked prompt", stage().indexOf("______") !== -1);
  typeAnswer("Versailles"); await sleep(20); clickText("Sure"); await sleep(20); clickText("Lock it in"); await sleep(40);
  clickText("Next"); await sleep(30);

  const tb = document.getElementById("tb"); tb.value = "Respiration releases energy from glucose in every living cell, not only in plants, which is why all organisms need it."; tb.dispatchEvent(new window.Event("input", { bubbles: true })); await sleep(60);
  clickText("Send it"); await sleep(180);

  check("run completed", stage().indexOf("FULL TIME") !== -1);
  const p = JSON.parse(webhookBody);
  const rec = {}; p.records.forEach((r) => { rec[r.id] = r; });
  check("TX1 record: text, picked, ok, confidence", rec.TX1.type === "text" && rec.TX1.picked === "guilt clause" && rec.TX1.ok === true && rec.TX1.confidence === "Sure", JSON.stringify(rec.TX1));
  check("CZ1 record: cloze, ok", rec.CZ1.type === "cloze" && rec.CZ1.ok === true, JSON.stringify(rec.CZ1));
  check("timing invariant: active ≤ elapsed", p.timing.activeSecs <= p.timing.elapsedSecs, p.timing.activeSecs + " vs " + p.timing.elapsedSecs);

  console.log("─".repeat(60));
  if (fails) { console.error(fails + " FAILURES"); process.exit(1); }
  console.log("SHORT-TEXT + CLOZE: ALL CHECKS PASS");
  process.exit(0);
})().catch((e) => { console.error("TEST CRASHED:", e.message); process.exit(1); });
