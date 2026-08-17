// XPDaily v3.1 — tap-to-order (steady) proof.
// A full jsdom run: tap shuffled items into sequence. Proves the tray/pool render, that Lock stays
// disabled until the sequence is complete, EXACT-sequence scoring (a correct order and a wrong one),
// per-slot correct/wrong feedback, and the record carrying type:"order" + the tapped sequence.
"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

const FIX = {
  student: "y9", date: "2026-08-02", day: "TEST", dateLabel: "SUN 2 AUG 2026", tag: "SYSTEM TEST", title: "order test",
  questions: [
    { id: "S1", phase: "speed", subject: "Maths", prompt: "What is 2 + 2?", options: ["3", "4"], answer: "4", why: "Four.", fresh: true },
    { id: "O1", phase: "steady", subject: "History", type: "order",
      prompt: "Put these in chronological order (earliest first).",
      sequence: ["WWI (1914)", "Versailles (1919)", "Depression (1929)", "Hitler (1933)"], why: "War, treaty, slump, Hitler.", fresh: true },
    { id: "O2", phase: "steady", subject: "Science", type: "order",
      prompt: "Order these steps.", sequence: ["One", "Two", "Three"], why: "One, two, three.", fresh: true },
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
function clickChip(text) {
  const b = Array.from(document.querySelectorAll("button.ochip")).find((x) => x.textContent.trim() === text);
  if (!b) throw new Error("no pool chip: " + text + " | pool: " + Array.from(document.querySelectorAll("button.ochip")).map((x) => x.textContent.trim()).join(" / "));
  b.dispatchEvent(new window.MouseEvent("click", { bubbles: true }));
}
const lockDisabled = () => document.getElementById("locksteady").disabled;

(async () => {
  await sleep(80);
  console.log("tap-to-order run:");
  clickText("Drop in"); await sleep(30);
  clickOpt("4"); await sleep(950);

  // O1 — tap into CORRECT chronological order
  check("O1 renders a tray (4 slots), no options", document.querySelectorAll(".oslot").length === 4 && document.querySelectorAll(".opt").length === 0);
  check("O1 pool has all 4 items", document.querySelectorAll("button.ochip").length === 4);
  clickChip("WWI (1914)"); await sleep(20);
  check("O1 Lock disabled while sequence incomplete", lockDisabled() === true);
  clickChip("Versailles (1919)"); await sleep(20);
  clickChip("Depression (1929)"); await sleep(20);
  clickChip("Hitler (1933)"); await sleep(20);
  check("O1 pool empties once all placed", document.querySelectorAll("button.ochip").length === 0);
  check("O1 Lock still disabled without confidence", lockDisabled() === true);
  clickText("Sure"); await sleep(20);
  check("O1 Lock enabled once complete + confident", lockDisabled() === false);
  clickText("Lock it in"); await sleep(40);
  check("O1 correct → points, not 'Not quite'", document.getElementById("stage").textContent.indexOf("250") !== -1 && document.getElementById("stage").textContent.indexOf("Not quite") === -1);
  check("O1 all slots flagged correct", document.querySelectorAll(".oslot.correct").length === 4 && document.querySelectorAll(".oslot.wrong").length === 0);
  clickText("Next"); await sleep(30);

  // O2 — tap into a WRONG order
  clickChip("Two"); await sleep(20); clickChip("One"); await sleep(20); clickChip("Three"); await sleep(20);
  clickText("Sure"); await sleep(20); clickText("Lock it in"); await sleep(40);
  check("O2 wrong → 'Not quite' + correct sequence shown", document.getElementById("stage").textContent.indexOf("Not quite") !== -1 && document.getElementById("stage").textContent.indexOf("One  \u2192  Two  \u2192  Three") !== -1);
  check("O2 at least one slot flagged wrong", document.querySelectorAll(".oslot.wrong").length >= 1);
  clickText("Next"); await sleep(30);

  const tb = document.getElementById("tb"); tb.value = "Respiration releases energy from glucose in every living cell, not only in plants, which is why all organisms need it."; tb.dispatchEvent(new window.Event("input", { bubbles: true })); await sleep(60);
  clickText("Send it"); await sleep(180);

  check("run completed", document.getElementById("stage").textContent.indexOf("FULL TIME") !== -1);
  const p = JSON.parse(webhookBody);
  const rec = {}; p.records.forEach((r) => { rec[r.id] = r; });
  check("O1 record: order, correct sequence, ok, confidence", rec.O1.type === "order" && JSON.stringify(rec.O1.picked) === JSON.stringify(FIX.questions[1].sequence) && rec.O1.ok === true && rec.O1.confidence === "Sure", JSON.stringify(rec.O1));
  check("O2 record: order, wrong sequence, ok=false", rec.O2.type === "order" && JSON.stringify(rec.O2.picked) === JSON.stringify(["Two", "One", "Three"]) && rec.O2.ok === false, JSON.stringify(rec.O2));
  check("timing invariant: active ≤ elapsed", p.timing.activeSecs <= p.timing.elapsedSecs, p.timing.activeSecs + " vs " + p.timing.elapsedSecs);

  console.log("─".repeat(60));
  if (fails) { console.error(fails + " FAILURES"); process.exit(1); }
  console.log("TAP-TO-ORDER: ALL CHECKS PASS");
  process.exit(0);
})().catch((e) => { console.error("TEST CRASHED:", e.message); process.exit(1); });
