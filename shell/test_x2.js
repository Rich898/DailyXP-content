// XPDaily v3.1 — hidden double-XP (x2) proof.
// A full jsdom run over a fixture with an x2 speed question and an x2 steady question. Proves: NO
// pre-answer tell (the question looks normal until answered), a correct x2 answer banks 2× points
// with a "DOUBLE XP" flourish, MAX_SCORE accounts for the doubling, and the record carries x2.
"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

const FIX = {
  student: "y9", date: "2026-08-02", day: "TEST", dateLabel: "SUN 2 AUG 2026", tag: "SYSTEM TEST", title: "x2 test",
  questions: [
    { id: "S1", phase: "speed", subject: "Maths", prompt: "What is 2 + 2?", options: ["3", "4"], answer: "4", why: "Four.", fresh: true },
    { id: "S2", phase: "speed", subject: "Maths", prompt: "What is 5 + 5? (secretly double)", options: ["9", "10"], answer: "10", why: "Ten.", fresh: true, x2: true },
    { id: "T1", phase: "steady", subject: "Gaming", prompt: "XP stands for? (secretly double)", options: ["Extra Power", "Experience Points"], answer: "Experience Points", why: "XP.", fresh: true, x2: true },
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
      if (url.indexOf("/functions/v1/grade-teachback") !== -1) return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) });
      if (url.indexOf("/rest/v1/runs_raw") !== -1) return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      if (url.indexOf("script.google.com") !== -1) { webhookBody = opts && opts.body; return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }); }
      return Promise.reject(new Error("unexpected fetch: " + url));
    };
  },
});
const { window } = dom; const { document } = window;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const btns = () => Array.from(document.querySelectorAll("button"));
const ct = (t) => { const b = btns().find((x) => x.textContent.indexOf(t) !== -1 && !x.disabled); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };
const opt = (v) => { const b = btns().find((x) => x.classList.contains("opt") && x.getAttribute("data-v") === v); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };
const stage = () => document.getElementById("stage").textContent;

(async () => {
  await sleep(80);
  console.log("hidden double-XP run:");
  ct("Drop in"); await sleep(30);
  opt("4"); await sleep(1000);                 // S1 normal

  // S2 — x2 speed: no tell before answering
  check("x2 question shows NO tell before answering", stage().indexOf("DOUBLE") === -1 && stage().indexOf("2\u00d7") === -1 && stage().indexOf("2x") === -1, stage().slice(0, 60));
  opt("10"); await sleep(60);
  check("x2 correct → DOUBLE XP flourish revealed", stage().indexOf("DOUBLE XP") !== -1);
  await sleep(1450);

  // T1 — x2 steady
  ct("Experience Points"); await sleep(30); ct("Sure"); await sleep(30); ct("Lock it in"); await sleep(40);
  check("x2 steady correct → DOUBLE XP flourish", stage().indexOf("DOUBLE XP") !== -1);
  ct("Next"); await sleep(30);

  const tb = document.getElementById("tb"); tb.value = "Respiration releases energy from glucose in every living cell, not only in plants, which is why all organisms need it."; tb.dispatchEvent(new window.Event("input", { bubbles: true })); await sleep(40);
  ct("Send it"); await sleep(120);

  const p = JSON.parse(webhookBody);
  const rec = {}; p.records.forEach((r) => { rec[r.id] = r; });
  check("S2 record carries x2 and doubled points", rec.S2.x2 === true && rec.S2.pts > 200, JSON.stringify(rec.S2));
  check("T1 record carries x2 and 500 (2×250)", rec.T1.x2 === true && rec.T1.pts === 500, JSON.stringify(rec.T1));
  check("normal S1 record has no x2 flag", !("x2" in rec.S1), JSON.stringify(rec.S1));
  // MAX_SCORE should include the doubling (one steady x2 adds +250, one speed x2 adds +speedmax)
  check("maxScore accounts for the doubling", p.maxScore > (2 * 250 + 150), String(p.maxScore));


  console.log("─".repeat(60));
  if (fails) { console.error(fails + " FAILURES"); process.exit(1); }
  console.log("HIDDEN DOUBLE-XP: ALL CHECKS PASS");
  process.exit(0);
})().catch((e) => { console.error("TEST CRASHED:", e.message); process.exit(1); });
