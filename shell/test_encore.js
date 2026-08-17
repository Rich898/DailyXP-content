// XPDaily v3.1 — optional encore (bonus round) proof.
// After the teach-back, an optional offer. Proves: the offer appears; ACCEPT plays 2 bonus questions
// through the reused steady machinery (including a typed one), tags their records encore:true, and
// counts toward the score; DECLINE goes straight to results with no encore records. One submit either way.
"use strict";
const fs = require("fs");
const { JSDOM } = require("jsdom");
const src = fs.readFileSync(__dirname + "/testbuild/index.html", "utf8");

let fails = 0;
function check(n, ok, d) { console.log((ok ? "  ok   " : "  FAIL ") + n + (d ? "  [" + d + "]" : "")); if (!ok) fails++; }

const FIX = {
  student: "y9", date: "2026-08-02", day: "TEST", dateLabel: "SUN 2 AUG 2026", tag: "SYSTEM TEST", title: "encore test",
  questions: [
    { id: "S1", phase: "speed", subject: "Maths", prompt: "2 + 2?", options: ["3", "4"], answer: "4", why: "Four.", fresh: true },
    { id: "T1", phase: "steady", subject: "Gaming", prompt: "XP stands for?", options: ["Extra Power", "Experience Points"], answer: "Experience Points", why: "XP.", fresh: true },
    { id: "TB", phase: "teach", subject: "Science", prompt: "SYSTEM TEST: type any 80+ character explanation." }
  ],
  encore: [
    { id: "E1", phase: "steady", subject: "History", prompt: "Capital of France?", options: ["Paris", "Lyon"], answer: "Paris", why: "Paris.", fresh: true },
    { id: "E2", phase: "steady", subject: "Maths", type: "numeric", prompt: "Bonus: 9 × 9?", answer: "81", accept: ["81"], why: "81.", fresh: true }
  ]
};

async function runFlow(takeEncore) {
  const dom = new JSDOM(src, {
    url: "https://xpdaily-test.netlify.test/", runScripts: "dangerously", pretendToBeVisual: true,
    beforeParse(window) {
      window.fetch = function (url, opts) {
        url = String(url);
        if (url.indexOf("raw.githubusercontent.com") !== -1) return Promise.resolve({ ok: true, json: () => Promise.resolve(FIX) });
        if (url.indexOf("/functions/v1/grade-teachback") !== -1) return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) });
        if (url.indexOf("/rest/v1/runs_raw") !== -1) return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
        if (url.indexOf("script.google.com") !== -1) { window.__wh = opts && opts.body; return Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: true }) }); }
        return Promise.reject(new Error("unexpected fetch: " + url));
      };
    },
  });
  const { window } = dom; const { document } = window;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const btns = () => Array.from(document.querySelectorAll("button"));
  const ct = (t) => { const b = btns().find((x) => x.textContent.indexOf(t) !== -1 && !x.disabled); if (!b) throw new Error("no btn: " + t); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };
  const opt = (v) => { const b = btns().find((x) => x.classList.contains("opt") && x.getAttribute("data-v") === v); b.dispatchEvent(new window.MouseEvent("click", { bubbles: true })); };
  const stage = () => document.getElementById("stage").textContent;

  await sleep(80);
  ct("Drop in"); await sleep(30);
  opt("4"); await sleep(1000);
  opt("Experience Points"); await sleep(30); ct("Sure"); await sleep(30); ct("Lock it in"); await sleep(30); ct("Next"); await sleep(30);
  const tb = document.getElementById("tb"); tb.value = "Respiration releases energy from glucose in every living cell, not only in plants, which is why all organisms need it."; tb.dispatchEvent(new window.Event("input", { bubbles: true })); await sleep(40);
  ct("Send it"); await sleep(60);

  const offered = stage().indexOf("BONUS ROUND") !== -1 || stage().indexOf("Want bonus XP") !== -1;

  if (takeEncore) {
    ct("Yes"); await sleep(40);
    // E1 (mc steady)
    opt("Paris"); await sleep(30); ct("Sure"); await sleep(30); ct("Lock it in"); await sleep(30); ct("Next"); await sleep(30);
    // E2 (numeric steady)
    const nin = document.getElementById("nin"); nin.value = "81"; nin.dispatchEvent(new window.Event("input", { bubbles: true })); await sleep(20);
    ct("Sure"); await sleep(20); ct("Lock it in"); await sleep(30); ct("Next"); await sleep(60);
  } else {
    ct("No thanks"); await sleep(60);
  }
  await sleep(60);
  const done = stage().indexOf("FULL TIME") !== -1;
  // submit fires on the done screen; read the captured payload
  const p = window.__wh ? JSON.parse(window.__wh) : null;
  return { offered, done, records: p ? p.records : [], score: p ? p.score : 0, maxScore: p ? p.maxScore : 0 };
}

(async () => {
  console.log("encore — DECLINE path:");
  const d = await runFlow(false);
  check("offer appears after teach-back", d.offered);
  check("decline → results reached", d.done);
  check("decline → no encore records", !d.records.some((r) => r.encore), JSON.stringify(d.records.map((r) => r.id)));

  console.log("encore — ACCEPT path:");
  const a = await runFlow(true);
  check("accept → results reached after bonus questions", a.done);
  const enc = a.records.filter((r) => r.encore);
  check("accept → 2 encore records, tagged encore:true", enc.length === 2 && enc.every((r) => r.encore === true), JSON.stringify(enc.map((r) => r.id)));
  check("encore E2 kept its numeric type", (a.records.find((r) => r.id === "E2") || {}).type === "numeric");
  check("encore questions counted toward score", a.score > d.score, a.score + " vs " + d.score);
  check("maxScore grew to include the taken encore", a.maxScore > d.maxScore, a.maxScore + " vs " + d.maxScore);

  console.log("─".repeat(60));
  if (fails) { console.error(fails + " FAILURES"); process.exit(1); }
  console.log("OPTIONAL ENCORE: ALL CHECKS PASS");
  process.exit(0);
})().catch((e) => { console.error("TEST CRASHED:", e.message); process.exit(1); });
